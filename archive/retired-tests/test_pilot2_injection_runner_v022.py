import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pulsar_pilot import pilot2_injection_runner_v022 as runner
from pulsar_pilot.config import load_yaml
from pulsar_pilot.injection_integrity import (
    DM_ERROR_KEY,
    TOA_ADJUSTMENT_KEY,
    UNCENTERED_TARGET_KEY,
)
from pulsar_pilot.paths import initialize_data_root
from pulsar_pilot.pilot2_calibration_runtime import HeartbeatService
from pulsar_pilot.pilot2_case_contract import grade_records
from pulsar_pilot.pilot2_injection_remediation import build_remediation_inventory
from pulsar_pilot.pilot2_injection_runner_v022 import (
    RUN_ID,
    STAGE,
    V022Ledger,
    implementation_sha256,
    supervision_snapshot,
    verify_execution_gate,
    verify_implementation_freeze,
    verify_readiness_freeze,
    zero_case_dry_run,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _configs() -> tuple[dict, dict, dict]:
    root = _root()
    return (
        load_yaml(root / "config/pilot2_calibration_v0.2.1.yaml"),
        load_yaml(root / "config/pilot2_injection_remediation_v0.2.2.yaml"),
        load_yaml(root / "config/pilot2_injection_runner_v0.2.2.yaml"),
    )


def _inventory() -> dict:
    base, remediation, _ = _configs()
    return build_remediation_inventory(base, remediation)


def _ledger(tmp_path: Path) -> V022Ledger:
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    return V022Ledger(
        data_root, _inventory()["inventory_sha256"], implementation_sha256()
    )


def _passing_records() -> list[dict]:
    base, remediation, _ = _configs()
    inventory = build_remediation_inventory(base, remediation)
    audit_ids = set(inventory["solver_audit_case_ids"])
    amplitudes = {
        float(ladder["period_days"]): sorted(
            float(value) for value in ladder["amplitudes_microseconds"]
        )
        for ladder in base["injections"]["main_period_ladders"]
    }
    cell_index: dict[tuple[float, float], int] = {
        (period, amplitude): index
        for period, values in amplitudes.items()
        for index, amplitude in enumerate(values)
    }
    records = []
    for case in inventory["cases"]:
        triggered = True
        if case["family"] == "main":
            index = cell_index[
                (float(case["period_days"]), float(case["amplitude_microseconds"]))
            ]
            position = int(case["noise_realization_index"]) + 3 * int(
                case["case_id"].split("-h")[1].split("-")[0]
            )
            triggered = position < (3, 6, 9, 12)[index]
        records.append(
            {
                "case": case,
                "family": case["family"],
                "period_days": case["period_days"],
                "amplitude_microseconds": case["amplitude_microseconds"],
                "triggered": triggered,
                "frequency_recovered": triggered,
                "amplitude_bias_fraction": 0.01,
                "phase_error_radians": 0.01,
                TOA_ADJUSTMENT_KEY: 0.00001,
                UNCENTERED_TARGET_KEY: 0.0018,
                DM_ERROR_KEY: 0.0,
                "ordinary_fit_converged": True,
                "joint_fit_converged": True,
                "solver_audit_required": case["case_id"] in audit_ids,
                "solver_audit_pass": True,
                "candidate_eligible": True,
                "signal_astrometry_correlation": 0.0,
                "ordinary_absorption_fraction": 0.0,
            }
        )
    return records


def test_runner_inventory_and_paths_are_versioned() -> None:
    inventory = _inventory()
    assert len(inventory["cases"]) == 344
    assert len(inventory["solver_audit_case_ids"]) == 35
    ledger = V022Ledger(Path("/tmp/example"), inventory["inventory_sha256"], "a" * 64)
    assert ledger.path.name == "calibration-v0.2.2-ledger.json"
    assert ledger.health_path.name == "calibration-v0.2.2-health.json"
    assert "calibration-v0.2.2-dashboard" in str(ledger.dashboard_path)
    assert ledger.empty()["run_id"] == RUN_ID


def test_v022_grader_passes_complete_prospective_fixture() -> None:
    base, remediation, _ = _configs()
    result = grade_records(_passing_records(), base, remediation)
    assert result["status"] == "pass"
    assert result["diagnostics"]["all_triggered_main_phase_error_role"] == (
        "diagnostic_not_hard_gate"
    )
    assert result["diagnostics"]["phase_reference_error_p90_radians"] == 0.01


def test_v022_grader_fails_phase_reference_p90() -> None:
    base, remediation, _ = _configs()
    records = _passing_records()
    phase_reference = [item for item in records if item["family"] == "phase_reference"]
    for item in phase_reference[:7]:
        item["phase_error_radians"] = 0.2
    result = grade_records(records, base, remediation)
    assert result["status"] == "fail"
    gate = next(item for item in result["gates"] if item["name"] == "phase_reference_error_p90")
    assert gate["status"] == "fail"


def test_v022_grader_rejects_legacy_only_toa_metric() -> None:
    base, remediation, _ = _configs()
    records = _passing_records()
    records[0].pop(TOA_ADJUSTMENT_KEY)
    records[0]["toa_adjustment_error_microseconds"] = 0.0018
    result = grade_records(records, base, remediation)
    assert result["status"] == "fail"
    gate = next(item for item in result["gates"] if item["name"] == "canonical_toa_metrics")
    assert gate["status"] == "fail"


def test_ledger_checkpoints_resume_and_detect_corruption(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    artifact_dir = ledger.data_root / "derived/pilot2/v022-test-artifacts"
    artifact_dir.mkdir(parents=True)
    for index in range(25):
        artifact = artifact_dir / f"case-{index:02d}.json"
        artifact.write_text(json.dumps({"zero_case_test_artifact": index}) + "\n")
        ledger.record_case(STAGE, f"case-{index:02d}", artifact)
    resumed = _ledger(tmp_path)
    state = resumed.load()
    assert len(state["completed_cases"]) == 25
    assert state["checkpoints"][-1]["completed_stage_cases"] == 25
    assert resumed.verify_artifacts()["status"] == "pass"
    artifact.write_text("corrupted\n")
    assert resumed.verify_artifacts()["status"] == "fail"


def test_resume_rejects_changed_implementation_hash(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    changed = V022Ledger(ledger.data_root, ledger.inventory_sha256, "0" * 64)
    with pytest.raises(RuntimeError, match="implementation hash mismatch"):
        changed.load()


def test_terminal_failure_creates_hard_stop_and_blocks_resume(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage(STAGE)
    result = ledger.data_root / "run_records/pilot2/simulated-v022-failure.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text('{"simulated_zero_case_failure": true}\n')
    ledger.complete_stage(STAGE, result, False)
    assert ledger.load()["hard_stop"]["reason"] == "stage_gate_failure"
    with pytest.raises(RuntimeError, match="hard stop"):
        ledger.begin_stage(STAGE)


def test_health_and_heartbeat_are_outcome_free(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    before = json.loads(ledger.health_path.read_text())
    with HeartbeatService(ledger, interval_seconds=0.01):
        pass
    after = json.loads(ledger.health_path.read_text())
    assert after["scientific_outcomes_sealed"] is True
    assert after["total_injection_cases"] == 344
    assert set(after) == set(before)
    forbidden = {"threshold", "trigger", "candidate", "delta_chi2", "phase_error"}
    assert forbidden.isdisjoint(after)
    assert 'http-equiv="refresh" content="30"' in ledger.dashboard_path.read_text()


def test_stale_heartbeat_requests_attention(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.begin_stage(STAGE)
    state["runtime_active"] = True
    ledger.save(state)
    health = json.loads(ledger.health_path.read_text())
    now = datetime.now(UTC)
    health["last_heartbeat_utc"] = (now - timedelta(seconds=91)).isoformat().replace(
        "+00:00", "Z"
    )
    ledger.health_path.write_text(json.dumps(health))
    snapshot = supervision_snapshot(ledger.data_root, now.isoformat())
    assert snapshot["event"] == "stale_attention_required"
    assert snapshot["codex_check_required"] is True


def test_execution_lock_precedes_predecessor_and_context_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    monkeypatch.setattr(
        runner,
        "verify_predecessor_bindings",
        lambda *_: pytest.fail("predecessors loaded before authorization"),
    )
    monkeypatch.setattr(
        runner,
        "prepare_context",
        lambda *_: pytest.fail("timing-model context loaded before authorization"),
    )
    gate = verify_execution_gate()
    assert gate["status"] == "locked"
    assert gate["predecessors_loaded"] is False
    with pytest.raises(RuntimeError, match="execution is locked"):
        runner.execute(ledger.data_root)


def test_zero_case_dry_run_executes_no_science(tmp_path: Path) -> None:
    if verify_implementation_freeze()["status"] != "pass":
        return
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    result = zero_case_dry_run(data_root)
    assert result["status"] == "pass"
    assert result["science_cases_executed"] == 0
    assert result["random_draws_generated"] == 0
    assert result["model_fits_executed"] == 0
    assert result["periodic_scans_executed"] == 0
    assert result["predecessor_artifacts_loaded"] == 0


def test_implementation_freeze_is_hash_bound_and_execution_locked() -> None:
    result = verify_implementation_freeze()
    assert result["status"] == "pass"
    assert result["execution_authorized"] is False
    assert verify_readiness_freeze()["status"] == "pass"
    assert verify_execution_gate()["status"] == "locked"


def test_runner_source_preserves_observed_search_boundary() -> None:
    source = (_root() / "src/pulsar_pilot/pilot2_injection_runner_v022.py").read_text()
    assert '"observed_residual_vector_used": False' in source
    assert '"observed_periodic_scan_executed": False' in source
    assert '"promotion_grade_executed": False' in source
