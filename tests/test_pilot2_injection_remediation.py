import copy
from pathlib import Path

from pulsar_pilot.config import load_yaml
from pulsar_pilot.injection_integrity import (
    DM_ERROR_KEY,
    TOA_ADJUSTMENT_KEY,
    UNCENTERED_TARGET_KEY,
)
from pulsar_pilot.pilot2_calibration_revision_design import build_revision_inventory
from pulsar_pilot.pilot2_injection_remediation import (
    analyze_v021_phase_failure,
    build_remediation_inventory,
    grade_remediation_integrity,
    validate_remediation_design,
    verify_remediation_freeze,
)


def _configs() -> tuple[dict, dict]:
    root = Path(__file__).resolve().parents[1]
    return (
        load_yaml(root / "config/pilot2_calibration_v0.2.1.yaml"),
        load_yaml(root / "config/pilot2_injection_remediation_v0.2.2.yaml"),
    )


def test_remediation_inventory_is_locked_and_disjoint() -> None:
    base, remediation = _configs()
    inventory = build_remediation_inventory(base, remediation)
    validation = validate_remediation_design(base, remediation, inventory)
    assert validation["status"] == "pass"
    assert validation["total_cases"] == 344
    assert validation["case_counts"] == {
        "main": 240,
        "phase_reference": 60,
        "annual": 28,
        "boundary": 16,
    }
    assert validation["solver_audit_cases"] == 35
    assert validation["case_ids_disjoint_from_v0.2.1"] is True
    assert validation["seeds_disjoint_from_v0.2.1"] is True
    assert validation["phase_limit_unchanged"] is True
    assert validation["toa_limit_unchanged"] is True
    assert validation["execution_authorized"] is False


def test_remediation_inventory_does_not_reuse_historical_injections() -> None:
    base, remediation = _configs()
    historical = build_revision_inventory(base)
    prospective = build_remediation_inventory(base, remediation)
    assert {item["case_id"] for item in historical["injection_cases"]}.isdisjoint(
        {item["case_id"] for item in prospective["cases"]}
    )
    assert {item["seed"] for item in historical["injection_cases"]}.isdisjoint(
        {item["seed"] for item in prospective["cases"]}
    )


def _remediation_record(family: str, phase_error: float = 0.01) -> dict:
    return {
        "family": family,
        "triggered": True,
        "phase_error_radians": phase_error,
        TOA_ADJUSTMENT_KEY: 0.00001,
        UNCENTERED_TARGET_KEY: 0.0018,
        DM_ERROR_KEY: 0.0,
    }


def test_remediation_integrity_uses_canonical_toa_metric() -> None:
    _, remediation = _configs()
    records = [_remediation_record("phase_reference") for _ in range(60)]
    result = grade_remediation_integrity(records, remediation)
    assert result["status"] == "pass"
    assert result["maximum_toa_adjustment_error_microseconds"] == 0.00001
    assert result["phase_reference_p90_radians"] == 0.01


def test_remediation_integrity_rejects_legacy_conflated_metric() -> None:
    _, remediation = _configs()
    records = [_remediation_record("phase_reference") for _ in range(60)]
    records[0].pop(TOA_ADJUSTMENT_KEY)
    records[0]["toa_adjustment_error_microseconds"] = 0.0018
    result = grade_remediation_integrity(records, remediation)
    assert result["status"] == "fail"
    assert result["canonical_toa_metrics_present"] is False


def test_phase_analysis_identifies_detection_strength_pattern() -> None:
    records = []
    trigger = 23.0
    for period_index, period in enumerate((50.0, 100.0, 200.0, 500.0, 1000.0)):
        for amplitude_index, amplitude in enumerate((0.1, 0.2, 0.3, 0.4)):
            for phase_index, phase in enumerate((0.0, 1.0, 2.0, 3.0)):
                for noise_index in range(3):
                    trigger += 1.0
                    error = 0.25 if trigger < 80.0 else 0.02
                    records.append(
                        {
                            "family": "main",
                            "period_days": period,
                            "amplitude_microseconds": amplitude,
                            "phase_radians": phase,
                            "triggered": True,
                            "global_maximum_delta_chi2": trigger,
                            "phase_error_radians": error,
                            "amplitude_bias_fraction": 0.01,
                            "ordinary_absorption_fraction": 0.0,
                            "noise_realization_index": noise_index,
                            "period_index": period_index,
                            "amplitude_index": amplitude_index,
                            "phase_index": phase_index,
                        }
                    )
    result = analyze_v021_phase_failure(records)
    assert result["science_cases_executed"] == 0
    assert result["spearman_correlations_with_absolute_phase_error"][
        "trigger_statistic"
    ] < 0.0
    assert result["causal_assessment"]["primary"] == (
        "phase_precision_degrades_as_detection_strength_decreases"
    )


def test_design_fails_if_numerical_phase_limit_is_relaxed() -> None:
    base, remediation = _configs()
    changed = copy.deepcopy(remediation)
    changed["phase_reference_controls"]["phase_error_p90_maximum_radians"] = 0.15
    inventory = build_remediation_inventory(base, changed)
    result = validate_remediation_design(base, changed, inventory)
    assert result["status"] == "fail"
    assert "The numerical phase-accuracy limit changed" in result["failures"]


def test_remediation_freeze_is_hash_bound_and_execution_locked() -> None:
    result = verify_remediation_freeze()
    assert result["status"] == "pass"
    assert result["execution_authorized"] is False
