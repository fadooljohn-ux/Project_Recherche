import json
from pathlib import Path

import pytest

from pulsar_pilot.config import load_yaml
from pulsar_pilot.paths import initialize_data_root
from pulsar_pilot.pilot2_calibration_design import build_inventory
from pulsar_pilot.pilot2_calibration_runtime import (
    CalibrationLedger,
    HeartbeatService,
    implementation_sha256,
    run_stage,
    verify_execution_gate,
    verify_implementation_freeze,
    zero_case_dry_run,
)


def _ledger(tmp_path: Path) -> CalibrationLedger:
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    root = Path(__file__).resolve().parents[1]
    inventory = build_inventory(load_yaml(root / "config/pilot2_calibration_v0.2.yaml"))
    return CalibrationLedger(data_root, inventory["inventory_sha256"], implementation_sha256())


def test_execution_gate_remains_locked_and_runner_never_calls_executor(tmp_path: Path) -> None:
    gate = verify_execution_gate()
    if gate["status"] == "pass":
        assert gate["failures"] == []
        return
    assert gate["status"] == "locked"
    ledger = _ledger(tmp_path)
    called = False

    def executor(_: dict) -> Path:
        nonlocal called
        called = True
        raise AssertionError("executor must remain unreachable")

    with pytest.raises(RuntimeError, match="execution is locked"):
        run_stage(ledger, "gaussian_threshold_calibration", [{"case_id": "x"}], executor, dict)
    assert called is False


def test_implementation_freeze_verifies_without_authorizing_execution() -> None:
    assert verify_implementation_freeze()["status"] == "pass"
    assert verify_execution_gate()["status"] in {"locked", "pass"}


def test_ledger_checkpoints_resume_and_detect_corruption(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage("gaussian_threshold_calibration")
    artifact_dir = ledger.data_root / "derived/pilot2/test-artifacts"
    artifact_dir.mkdir(parents=True)
    for index in range(25):
        artifact = artifact_dir / f"case-{index:02d}.json"
        artifact.write_text(json.dumps({"synthetic_integrity_test": index}) + "\n")
        ledger.record_case("gaussian_threshold_calibration", f"case-{index:02d}", artifact)
    resumed = _ledger(tmp_path)
    state = resumed.load()
    assert len(state["completed_cases"]) == 25
    assert state["checkpoints"][-1]["completed_stage_cases"] == 25
    assert resumed.verify_artifacts()["status"] == "pass"
    artifact.write_text("corrupted\n")
    assert resumed.verify_artifacts()["status"] == "fail"


def test_threshold_is_locked_before_sealed_evaluation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.begin_stage("gaussian_threshold_calibration")
    result = ledger.data_root / "derived/pilot2/calibration-result.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(
        json.dumps({"threshold": {"status": "proposed_not_locked", "value_delta_chi2": 42.0}})
    )
    ledger.complete_stage("gaussian_threshold_calibration", result, True)
    with pytest.raises(RuntimeError, match="predecessor"):
        ledger.begin_stage("sealed_gaussian_evaluation")
    lock = ledger.commit_threshold_lock(result)
    assert lock["status"] == "locked_before_sealed_evaluation"
    state = ledger.begin_stage("sealed_gaussian_evaluation")
    assert state["stage_status"]["sealed_gaussian_evaluation"] == "running"


def test_health_record_is_outcome_free_and_heartbeat_refreshes(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    before = json.loads(ledger.health_path.read_text())
    with HeartbeatService(ledger, interval_seconds=0.01):
        pass
    after = json.loads(ledger.health_path.read_text())
    assert after["scientific_outcomes_sealed"] is True
    assert set(after) == set(before)
    forbidden = {"threshold", "trigger", "candidate", "delta_chi2", "false_positive"}
    assert forbidden.isdisjoint(after)
    assert 'http-equiv="refresh" content="30"' in ledger.dashboard_path.read_text()


def test_zero_case_dry_run_executes_no_science(tmp_path: Path) -> None:
    if verify_execution_gate()["status"] == "pass":
        return
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    result = zero_case_dry_run(data_root)
    assert result["status"] == "pass"
    assert result["science_cases_executed"] == 0
    assert result["random_draws_generated"] == 0
    assert result["model_fits_executed"] == 0
    assert result["periodic_scans_executed"] == 0
    assert all(result["criteria"].values())


def test_resume_rejects_changed_implementation_hash(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    changed = CalibrationLedger(ledger.data_root, ledger.inventory_sha256, "0" * 64)
    with pytest.raises(RuntimeError, match="implementation hash mismatch"):
        changed.load()
