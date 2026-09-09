from pathlib import Path

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot2_calibration_design import (
    build_inventory,
    plan_summary,
    validate_design,
    verify_design_freeze,
)


def _config() -> dict:
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / "config/pilot2_calibration_v0.2.yaml")


def test_calibration_inventory_is_exact_and_deterministic() -> None:
    config = _config()
    first = build_inventory(config)
    second = build_inventory(config)
    assert first == second
    assert first["inventory_sha256"] == (
        "28bcd10edcf719c1d44cdef17dd8b200b332b127f13c8a1558b7b4b8acd69dc7"
    )
    assert len(first["gaussian_null_cases"]) == 1500
    assert len(first["structured_tail_cases"]) == 3000
    assert len(first["injection_cases"]) == 284
    assert len(first["solver_audit_case_ids"]) == 29


def test_calibration_design_validation_passes() -> None:
    config = _config()
    inventory = build_inventory(config)
    validation = validate_design(config, inventory)
    assert validation["status"] == "pass"
    assert validation["failures"] == []
    assert validation["unique_case_ids"] == 4784
    assert validation["unique_seeds"] == 4784
    assert validation["projected_wall_hours_with_contingency"] < 6.0


def test_target_specific_amplitude_ladders_are_increasing() -> None:
    config = _config()
    ladders = config["injections"]["main_period_ladders"]
    assert [item["period_days"] for item in ladders] == [50, 100, 200, 500, 1000]
    for ladder in ladders:
        amplitudes = ladder["amplitudes_microseconds"]
        assert len(amplitudes) == 4
        assert amplitudes == sorted(amplitudes)
        assert len(set(amplitudes)) == 4
    assert ladders[0]["amplitudes_microseconds"] != ladders[-1][
        "amplitudes_microseconds"
    ]


def test_design_package_keeps_execution_and_observed_search_locked() -> None:
    config = _config()
    summary = plan_summary(config)
    assert summary["status"] == "pass"
    assert summary["execution_authorized"] is False
    assert summary["observed_periodic_search_authorized"] is False
    assert config["authority"]["observed_residual_access_authorized"] is False
    assert config["promotion"]["pass_authorizes_observed_search"] is False


def test_design_module_contains_no_science_execution_path() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/pulsar_pilot/pilot2_calibration_design.py").read_text(
        encoding="utf-8"
    )
    assert "pint." not in source
    assert "fit_toas" not in source
    assert ".scan(" not in source
    assert "numpy" not in source


def test_calibration_design_freeze_verifies_if_present() -> None:
    root = Path(__file__).resolve().parents[1]
    if not (root / "protocol/PILOT2_CALIBRATION_DESIGN_FREEZE_v0.2.json").exists():
        return
    assert verify_design_freeze()["status"] == "pass"
