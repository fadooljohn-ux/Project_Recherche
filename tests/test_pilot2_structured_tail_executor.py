import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from pulsar_pilot import pilot2_structured_tail_executor as structured_executor
from pulsar_pilot.config import load_yaml
from pulsar_pilot.paths import initialize_data_root
from pulsar_pilot.pilot2_calibration_revision_design import build_revision_inventory
from pulsar_pilot.pilot2_calibration_revision_runtime import (
    RevisionLedger,
)
from pulsar_pilot.pilot2_calibration_revision_runtime import (
    implementation_sha256 as gaussian_implementation_sha256,
)
from pulsar_pilot.pilot2_structured_tail_executor import (
    HEARTBEAT_INTERVAL_SECONDS,
    PASSIVE_REVIEW_INTERVAL_SECONDS,
    STALE_HEARTBEAT_SECONDS,
    _mixture_scale,
    generate_structured_null,
    supervision_snapshot,
)


def _ledger(tmp_path: Path) -> RevisionLedger:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / "config/pilot2_calibration_v0.2.1.yaml")
    inventory = build_revision_inventory(config)
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    return RevisionLedger(
        data_root, inventory["inventory_sha256"], gaussian_implementation_sha256()
    )


def test_structured_null_is_reproducible_and_unit_variance_normalized() -> None:
    factor = np.eye(8)
    variant = {"selected_native_innovation_block": "timing"}
    first = generate_structured_null(
        factor, np.random.default_rng(42), variant, 4, np.arange(4), 0.01, 3.0
    )
    second = generate_structured_null(
        factor, np.random.default_rng(42), variant, 4, np.arange(4), 0.01, 3.0
    )
    assert np.array_equal(first[0], second[0])
    assert first[1] == second[1]
    assert abs(_mixture_scale(0.01, 3.0) ** 2 - 1.08) < 1e-12


def test_clustered_variant_contaminates_paired_coordinates() -> None:
    factor = np.eye(8)
    noise, contaminated = generate_structured_null(
        factor, np.random.default_rng(7), {}, 4, np.asarray([1, 1, 2, 3]), 1.0, 3.0
    )
    assert noise.shape == (8,)
    assert contaminated == 8


def test_fresh_heartbeat_suppresses_codex_polling(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.empty()
    state["stage_status"].update(
        {
            "gaussian_threshold_calibration": "pass",
            "commit_threshold_lock": "pass",
            "sealed_gaussian_evaluation": "pass",
            "structured_tail_evaluation": "running",
        }
    )
    state["active_stage"] = "structured_tail_evaluation"
    state["runtime_active"] = True
    ledger.save(state)
    snapshot = supervision_snapshot(ledger.data_root)
    assert snapshot["event"] == "healthy_no_action"
    assert snapshot["codex_check_required"] is False
    assert snapshot["heartbeat_interval_seconds"] == HEARTBEAT_INTERVAL_SECONDS
    assert snapshot["stale_after_seconds"] == STALE_HEARTBEAT_SECONDS
    assert snapshot["passive_review_interval_seconds"] == PASSIVE_REVIEW_INTERVAL_SECONDS


def test_stale_heartbeat_requests_attention(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.empty()
    state["stage_status"].update(
        {
            "gaussian_threshold_calibration": "pass",
            "commit_threshold_lock": "pass",
            "sealed_gaussian_evaluation": "pass",
            "structured_tail_evaluation": "running",
        }
    )
    state["active_stage"] = "structured_tail_evaluation"
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


def test_structured_ledger_recovers_existing_artifact(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    state = ledger.empty()
    state["stage_status"].update(
        {
            "gaussian_threshold_calibration": "pass",
            "commit_threshold_lock": "pass",
            "sealed_gaussian_evaluation": "pass",
        }
    )
    ledger.save(state)
    ledger.begin_stage("structured_tail_evaluation")
    artifact = ledger.data_root / "derived/pilot2/test-structured-case.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('{"simulated_test_artifact": true}\n')
    ledger.record_case("structured_tail_evaluation", "simulated-test-case", artifact)
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
        structured_executor,
        "prepare_structured_context",
        lambda *_: pytest.fail("setup reached before authorization"),
    )
    with pytest.raises(RuntimeError, match="execution is locked"):
        structured_executor.execute_structured_tail(ledger.data_root)


def test_structured_executor_preserves_observed_search_boundary() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/pilot2_structured_tail_executor.py").read_text()
    assert '"observed_residual_vector_used": False' in source
    assert '"observed_periodic_scan_executed": False' in source
