from pathlib import Path

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot2_calibration_revision_design import (
    build_revision_inventory,
    revision_summary,
    validate_revision,
    verify_revision_freeze,
)


def _config() -> dict:
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / "config/pilot2_calibration_v0.2.1.yaml")


def test_revision_inventory_is_exact_unique_and_deterministic() -> None:
    config = _config()
    first = build_revision_inventory(config)
    assert first == build_revision_inventory(config)
    assert len(first["gaussian_null_cases"]) == 7000
    assert len(first["structured_tail_cases"]) == 3000
    assert len(first["injection_cases"]) == 284
    assert len(first["solver_audit_case_ids"]) == 29
    assert all(item["case_id"].startswith("p2r1-") for item in first["gaussian_null_cases"])


def test_revision_statistical_and_resource_design_passes() -> None:
    config = _config()
    validation = validate_revision(config, build_revision_inventory(config))
    assert validation["status"] == "pass"
    assert validation["total_unique_cases"] == 10284
    assert validation["case_ids_disjoint_from_v0.2"] is True
    assert validation["seeds_disjoint_from_v0.2"] is True
    assert validation["sealed_maximum_false_positives"] == 36
    assert validation["projected_wall_hours_with_contingency"] < 6.0


def test_revision_keeps_every_execution_authority_locked() -> None:
    summary = revision_summary(_config())
    assert summary["status"] == "pass"
    assert summary["execution_authorized"] is False
    assert summary["observed_periodic_search_authorized"] is False


def test_revision_design_contains_no_science_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/pilot2_calibration_revision_design.py").read_text()
    assert "np.random" not in source
    assert "fit_toas" not in source
    assert ".scan(" not in source


def test_revision_freeze_verifies_when_present() -> None:
    root = Path(__file__).resolve().parents[1]
    if not (root / "protocol/PILOT2_CALIBRATION_DESIGN_FREEZE_v0.2.1.json").exists():
        return
    assert verify_revision_freeze()["status"] == "pass"
