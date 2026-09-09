import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pulsar_pilot import pilot2_injection_executor as injection_executor
from pulsar_pilot.config import load_yaml
from pulsar_pilot.paths import initialize_data_root
from pulsar_pilot.pilot2_calibration_revision_design import build_revision_inventory
from pulsar_pilot.pilot2_calibration_revision_runtime import (
    RevisionLedger,
)
from pulsar_pilot.pilot2_calibration_revision_runtime import (
    implementation_sha256 as gaussian_implementation_sha256,
)
from pulsar_pilot.pilot2_injection_executor import (
    HEARTBEAT_INTERVAL_SECONDS,
    PASSIVE_REVIEW_INTERVAL_SECONDS,
    STALE_HEARTBEAT_SECONDS,
    _solver_audit_pass,
    supervision_snapshot,
)


def _config() -> dict:
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / "config/pilot2_calibration_v0.2.1.yaml")


def _ledger(tmp_path: Path) -> RevisionLedger:
    inventory = build_revision_inventory(_config())
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    return RevisionLedger(
        data_root, inventory["inventory_sha256"], gaussian_implementation_sha256()
    )


def test_injection_inventory_has_exact_frozen_counts() -> None:
    inventory = build_revision_inventory(_config())
    cases = inventory["injection_cases"]
    assert sum(item["family"] == "main" for item in cases) == 240
    assert sum(item["family"] == "annual" for item in cases) == 28
    assert sum(item["family"] == "boundary" for item in cases) == 16
    assert [item["family"] for item in cases] == ["main"] * 240 + ["annual"] * 28 + [
        "boundary"
    ] * 16
    assert len(inventory["solver_audit_case_ids"]) == 29
    assert set(inventory["solver_audit_case_ids"]) <= {item["case_id"] for item in cases}


def test_solver_audit_uses_all_frozen_tolerances() -> None:
    primary = {
        "returned_converged": True,
        "fitter_converged": True,
        "release_red_noise_preserved": True,
        "wavex_absent": True,
    }
    audit = {
        "completed": True,
        "release_red_noise_preserved": True,
        "wavex_absent": True,
    }
    passing = {
        "amplitude_difference_microseconds": 0.01,
        "phase_difference_radians": 0.001,
        "chi2_difference": 0.1,
    }
    assert _solver_audit_pass(primary, audit, passing, _config())
    failing = {**passing, "chi2_difference": 0.1000001}
    assert not _solver_audit_pass(primary, audit, failing, _config())


def test_fresh_injection_heartbeat_suppresses_codex_polling(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.empty()
    state["stage_status"].update(
        {
            "gaussian_threshold_calibration": "pass",
            "commit_threshold_lock": "pass",
            "sealed_gaussian_evaluation": "pass",
            "structured_tail_evaluation": "pass",
            "injection_recovery_and_annual_map": "running",
        }
    )
    state["active_stage"] = "injection_recovery_and_annual_map"
    state["runtime_active"] = True
    ledger.save(state)
    snapshot = supervision_snapshot(ledger.data_root)
    assert snapshot["event"] == "healthy_no_action"
    assert snapshot["codex_check_required"] is False
    assert snapshot["heartbeat_interval_seconds"] == HEARTBEAT_INTERVAL_SECONDS
    assert snapshot["stale_after_seconds"] == STALE_HEARTBEAT_SECONDS
    assert snapshot["passive_review_interval_seconds"] == PASSIVE_REVIEW_INTERVAL_SECONDS


def test_stale_injection_heartbeat_requests_attention(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.empty()
    state["stage_status"].update(
        {
            "gaussian_threshold_calibration": "pass",
            "commit_threshold_lock": "pass",
            "sealed_gaussian_evaluation": "pass",
            "structured_tail_evaluation": "pass",
            "injection_recovery_and_annual_map": "running",
        }
    )
    state["active_stage"] = "injection_recovery_and_annual_map"
    state["runtime_active"] = True
    ledger.save(state)
    health = json.loads(ledger.health_path.read_text())
    now = datetime.now(UTC)
    health["last_heartbeat_utc"] = (now - timedelta(seconds=91)).isoformat().replace(
        "+00:00", "Z"
    )
    ledger.health_path.write_text(json.dumps(health))
    snapshot = supervision_snapshot(ledger.data_root, now=now)
    assert snapshot["event"] == "stale_attention_required"
    assert snapshot["codex_check_required"] is True


def test_injection_ledger_recovers_existing_artifact(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.empty()
    state["stage_status"].update(
        {
            "gaussian_threshold_calibration": "pass",
            "commit_threshold_lock": "pass",
            "sealed_gaussian_evaluation": "pass",
            "structured_tail_evaluation": "pass",
        }
    )
    ledger.save(state)
    ledger.begin_stage("injection_recovery_and_annual_map")
    artifact = ledger.data_root / "derived/pilot2/test-injection-case.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('{"simulated_test_artifact": true}\n')
    ledger.record_case("injection_recovery_and_annual_map", "simulated-test-case", artifact)
    recovered = RevisionLedger(
        ledger.data_root, ledger.inventory_sha256, gaussian_implementation_sha256()
    )
    assert "simulated-test-case" in recovered.load()["completed_cases"]
    assert recovered.verify_artifacts()["status"] == "pass"


def test_execution_cannot_reach_setup_without_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    monkeypatch.setattr(
        injection_executor,
        "prepare_injection_context",
        lambda *_: pytest.fail("setup reached before authorization"),
    )
    with pytest.raises(RuntimeError, match="execution is locked"):
        injection_executor.execute_injections(ledger.data_root)


def test_injection_executor_preserves_observed_search_boundary() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/pilot2_injection_executor.py").read_text()
    assert '"observed_residual_vector_used": False' in source
    assert '"observed_periodic_scan_executed": False' in source
    assert '"signed_wrapped_phase_error_radians"' in source
    assert '"toa_adjustment_maximum_absolute_error_microseconds"' in source
