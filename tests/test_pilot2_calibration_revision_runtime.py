import json
from pathlib import Path

import pytest

from pulsar_pilot.config import load_yaml
from pulsar_pilot.paths import initialize_data_root
from pulsar_pilot.pilot2_calibration_revision_design import build_revision_inventory
from pulsar_pilot.pilot2_calibration_revision_grading import (
    grade_revision_calibration,
    grade_revision_sealed,
)
from pulsar_pilot.pilot2_calibration_revision_runtime import (
    RevisionLedger,
    implementation_sha256,
    verify_execution_gate,
    verify_implementation_freeze,
    zero_case_dry_run,
)


def _config() -> dict:
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / "config/pilot2_calibration_v0.2.1.yaml")


def _ledger(tmp_path: Path) -> RevisionLedger:
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    inventory = build_revision_inventory(_config())
    return RevisionLedger(data_root, inventory["inventory_sha256"], implementation_sha256())


def test_revision_calibration_uses_frozen_rank_4962() -> None:
    records = [{"global_maximum_delta_chi2": float(index)} for index in range(5000)]
    diagnostics = {
        "whitened_variance": 1.0,
        "maximum_absolute_pooled_lag_correlation": 0.01,
    }
    result = grade_revision_calibration(records, diagnostics, _config())
    assert result["status"] == "pass"
    assert result["threshold"]["rank"] == 4962
    assert result["threshold"]["value_delta_chi2"] == 4961.0


def test_revision_sealed_has_one_statistical_hard_gate() -> None:
    config = _config()
    passing = [{"global_maximum_delta_chi2": 2.0 if index < 36 else 0.0} for index in range(2000)]
    failing = [{"global_maximum_delta_chi2": 2.0 if index < 37 else 0.0} for index in range(2000)]
    assert grade_revision_sealed(passing, 1.0, config)["status"] == "pass"
    assert grade_revision_sealed(failing, 1.0, config)["status"] == "fail"


def test_revision_ledger_is_separate_and_threshold_lock_is_ordered(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    assert ledger.path.name == "calibration-v0.2.1-ledger.json"
    state = ledger.begin_stage("gaussian_threshold_calibration")
    assert state["run_id"] == "pilot2-b1937-calibration-v0.2.1"
    result = ledger.data_root / "derived/pilot2/revision-result.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(
        json.dumps(
            {
                "threshold": {
                    "status": "proposed_not_locked",
                    "value_delta_chi2": 42.0,
                    "rank": 4962,
                    "sample_count": 5000,
                }
            }
        )
    )
    ledger.complete_stage("gaussian_threshold_calibration", result, True)
    lock = ledger.commit_threshold_lock(result)
    assert lock["rank"] == 4962
    assert lock["sample_count"] == 5000
    assert ledger.verify_threshold_lock() == lock


def test_revision_resume_rejects_changed_implementation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.save(ledger.empty())
    changed = RevisionLedger(ledger.data_root, ledger.inventory_sha256, "0" * 64)
    with pytest.raises(RuntimeError, match="implementation hash mismatch"):
        changed.load()


def test_revision_zero_case_validation_when_execution_is_locked(tmp_path: Path) -> None:
    if verify_implementation_freeze()["status"] != "pass":
        return
    if verify_execution_gate()["status"] == "pass":
        return
    data_root = tmp_path / "data-root"
    initialize_data_root(data_root)
    result = zero_case_dry_run(data_root)
    assert result["status"] == "pass"
    assert result["science_cases_executed"] == 0
    assert result["random_draws_generated"] == 0


def test_revision_executor_preserves_observed_search_boundary() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/pilot2_calibration_revision_executor.py").read_text()
    assert '"observed_residual_vector_used": False' in source
    assert '"observed_periodic_scan_executed": False' in source
