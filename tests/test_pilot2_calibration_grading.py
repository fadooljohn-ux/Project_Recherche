from pathlib import Path

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot2_calibration_grading import (
    grade_gaussian_calibration,
    grade_injections,
    grade_promotion,
    grade_sealed_gaussian,
    grade_structured_tail,
)


def _config() -> dict:
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / "config/pilot2_calibration_v0.2.yaml")


def test_gaussian_threshold_is_proposed_but_not_locked() -> None:
    records = [
        {
            "global_maximum_delta_chi2": float(index),
        }
        for index in range(1000)
    ]
    result = grade_gaussian_calibration(
        records,
        {"whitened_variance": 1.0, "maximum_absolute_pooled_lag_correlation": 0.01},
        _config(),
    )
    assert result["status"] == "pass"
    assert result["threshold"] == {
        "status": "proposed_not_locked",
        "value_delta_chi2": 989.0,
        "estimator": "conservative_nearest_rank",
        "rank": 990,
    }


def test_sealed_and_structured_graders_use_strict_threshold() -> None:
    config = _config()
    sealed = [{"global_maximum_delta_chi2": 10.0} for _ in range(500)]
    assert grade_sealed_gaussian(sealed, 10.0, config)["status"] == "pass"
    structured = [
        {"variant": variant["id"], "global_maximum_delta_chi2": 10.0}
        for variant in config["structured_tail_evaluation"]["variants"]
        for _ in range(1000)
    ]
    result = grade_structured_tail(structured, 10.0, config)
    assert result["status"] == "pass"
    assert result["threshold_unchanged"] is True


def _injection_record(family: str, triggered: bool, audit: bool = False) -> dict:
    return {
        "family": family,
        "triggered": triggered,
        "frequency_recovered": triggered,
        "amplitude_bias_fraction": 0.01,
        "phase_error_radians": 0.01,
        "toa_adjustment_error_microseconds": 0.0001,
        "ordinary_fit_converged": True,
        "joint_fit_converged": True,
        "solver_audit_required": audit,
        "solver_audit_pass": True,
        "candidate_eligible": False,
        "signal_astrometry_correlation": 0.9 if family == "annual" else 0.0,
        "ordinary_absorption_fraction": 0.0,
        "period_days": 365.25 if family == "annual" else 0.0,
    }


def test_injection_and_promotion_graders_pass_complete_synthetic_fixture() -> None:
    config = _config()
    records = []
    audit_remaining = 29
    for ladder in config["injections"]["main_period_ladders"]:
        for amplitude_index, amplitude in enumerate(ladder["amplitudes_microseconds"]):
            triggered_count = (3, 6, 9, 12)[amplitude_index]
            for index in range(12):
                item = _injection_record("main", index < triggered_count, audit_remaining > 0)
                audit_remaining -= item["solver_audit_required"]
                item.update(period_days=ladder["period_days"], amplitude_microseconds=amplitude)
                records.append(item)
    for _ in range(28):
        records.append(_injection_record("annual", True, audit_remaining > 0))
        audit_remaining -= records[-1]["solver_audit_required"]
    for _ in range(16):
        records.append(_injection_record("boundary", True, audit_remaining > 0))
        audit_remaining -= records[-1]["solver_audit_required"]
    result = grade_injections(records, config)
    assert result["status"] == "pass"
    assert len(records) == 284
    assert audit_remaining == 0
    stages = {
        name: {"status": "pass"}
        for name in (
            "gaussian_threshold_calibration",
            "sealed_gaussian_evaluation",
            "structured_tail_evaluation",
            "injection_recovery_and_annual_map",
        )
    }
    promotion = grade_promotion(stages)
    assert promotion["status"] == "pass"
    assert promotion["observed_search_authorized"] is False


def test_graders_fail_closed_on_missing_records() -> None:
    config = _config()
    assert grade_gaussian_calibration([], {}, config)["status"] == "fail"
    assert grade_sealed_gaussian([], 1.0, config)["status"] == "fail"
    assert grade_structured_tail([], 1.0, config)["status"] == "fail"
    assert grade_injections([], config)["status"] == "fail"
    assert grade_promotion({})["status"] == "fail"
