import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot1 import (
    build_pilot1_plan_summary,
    evaluate_v01_promotion,
    validate_pilot1_plan,
)


def _plan() -> dict:
    root = Path(__file__).resolve().parents[1]
    return load_yaml(root / "config" / "pilot1.yaml")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _passing_metrics() -> dict:
    return {
        "calibration_nulls_completed": 1000,
        "sealed_evaluation_nulls_completed": 500,
        "calibration_evaluation_split_preserved": True,
        "covariance_aware_statistic_used": True,
        "evaluation_false_positive_rate": 0.008,
        "evaluation_false_positive_rate_upper_95": 0.022,
        "strong_control_recovery_rate": 0.95,
        "injected_frequency_recovery_rate": 0.97,
        "median_amplitude_bias_fraction": 0.08,
        "phase_error_p90_radians": 0.08,
        "periods_with_monotonic_detection_fraction": 4,
        "periods_with_bracketed_50_and_90_percent_sensitivity": 3,
        "annual_eligibility_violations": 0,
        "independent_audit_failures": 0,
        "unexpected_material_warnings": 0,
        "null_whitened_variance": 1.01,
        "null_maximum_absolute_ensemble_correlation": 0.06,
        "published_100_day_sensitivity_ratio": 0.8,
        "all_artifact_hashes_verified": True,
        "total_wall_hours": 2.2,
        "peak_memory_gib": 1.5,
        "complete_data_root_gib": 1.8,
        "blind_real_data_search_executed": False,
    }


def test_validate_and_summarize_pilot1_plan() -> None:
    plan = _plan()
    validate_pilot1_plan(plan)
    summary = build_pilot1_plan_summary(plan)
    assert summary["execution_authorized"] is False
    assert summary["case_counts"]["main_injections"] == 240
    assert summary["case_counts"]["annual_identifiability_injections"] == 28
    assert summary["case_counts"]["search_boundary_injections"] == 16
    assert summary["case_counts"]["total_injections"] == 284
    assert summary["case_counts"]["total_trigger_scans"] == 1784
    assert summary["case_counts"]["primary_timing_fits"] == 568
    assert summary["case_counts"]["explicit_full_covariance_audits"] == 29
    assert summary["planning_estimate"]["within_macbook_cap"] is True


def test_plan_rejects_execution_authorization() -> None:
    plan = deepcopy(_plan())
    plan["execution_authorized"] = True
    with pytest.raises(ValueError, match="must not authorize"):
        validate_pilot1_plan(plan)


def test_plan_rejects_weak_null_count() -> None:
    plan = deepcopy(_plan())
    plan["nulls"]["calibration_count"] = 999
    with pytest.raises(ValueError, match="1000 calibration nulls"):
        validate_pilot1_plan(plan)


def test_plan_rejects_permissive_annual_threshold() -> None:
    plan = deepcopy(_plan())
    plan["candidate_eligibility"]["maximum_signal_astrometry_correlation"] = 0.81
    with pytest.raises(ValueError, match="may not exceed 0.8"):
        validate_pilot1_plan(plan)


def test_promotion_passes_only_when_every_benchmark_passes() -> None:
    result = evaluate_v01_promotion(_plan(), _passing_metrics())
    assert result["overall"] == "PASS"
    assert result["promotion_ready"] is True
    assert set(result["rows"].values()) == {"PASS"}


def test_promotion_blocks_when_metrics_are_missing() -> None:
    result = evaluate_v01_promotion(_plan(), {})
    assert result["overall"] == "BLOCKED"
    assert result["promotion_ready"] is False


def test_one_failed_benchmark_fails_promotion() -> None:
    metrics = _passing_metrics()
    metrics["evaluation_false_positive_rate"] = 0.012
    result = evaluate_v01_promotion(_plan(), metrics)
    assert result["overall"] == "FAIL"
    assert result["rows"]["false_positive_rate"] == "FAIL"
    assert result["promotion_ready"] is False


def test_pilot1_design_record_hashes() -> None:
    root = Path(__file__).resolve().parents[1]
    record_path = root / "protocol" / "PILOT1_DESIGN_RECORD_v0.1.json"
    manifest_line = (root / "protocol" / "design_records.sha256").read_text().strip()
    expected, relative = manifest_line.split("  ", 1)
    assert relative == "protocol/PILOT1_DESIGN_RECORD_v0.1.json"
    assert _sha256(record_path) == expected

    record = json.loads(record_path.read_text())
    assert record["execution_authorized"] is False
    for section in ("design_sha256", "research_sha256"):
        for relative, expected in record[section].items():
            assert _sha256(root / relative) == expected
    assert _sha256(root / "pixi.lock") == record["pixi_lock_sha256"]
