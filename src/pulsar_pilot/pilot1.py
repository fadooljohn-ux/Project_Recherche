from __future__ import annotations

import math
from collections.abc import Callable
from itertools import pairwise
from typing import Any


def _strictly_increasing(values: list[float]) -> bool:
    return all(left < right for left, right in pairwise(values))


def _matrix_case_count(matrix: dict[str, Any]) -> int:
    return (
        len(matrix["periods_days"])
        * len(matrix["amplitudes_microseconds"])
        * len(matrix["phases_radians"])
        * int(matrix["covariance_noise_realizations_per_phase"])
    )


def validate_pilot1_plan(plan: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "plan_id",
        "status",
        "execution_authorized",
        "target",
        "dataset",
        "detector",
        "nulls",
        "injections",
        "candidate_eligibility",
        "independent_audit",
        "promotion_benchmarks",
        "resource_caps",
        "promotion",
    }
    missing = required.difference(plan)
    if missing:
        raise ValueError(f"Pilot 1 plan is missing keys: {sorted(missing)}")
    if plan["schema_version"] != 1:
        raise ValueError("Pilot 1 plan schema_version must be 1")
    if plan["plan_id"] != "pilot1-calibration-v0.1":
        raise ValueError("Unexpected Pilot 1 plan identifier")
    if plan["execution_authorized"] is not False:
        raise ValueError("The design record must not authorize Pilot 1 execution")
    if plan["target"] != "J1744-1134":
        raise ValueError("Pilot 1 remains limited to J1744-1134")

    detector = plan["detector"]
    if detector["trigger"] != "covariance_whitened_gls_circular_scan":
        raise ValueError("Pilot 1 requires the covariance-whitened GLS trigger")
    if detector["preserve_release_red_noise"] is not True:
        raise ValueError("Pilot 1 must preserve the released red-noise covariance")
    if detector["wavex_allowed"] is not False:
        raise ValueError("WaveX is not compatible with the Pilot 1 release model")

    nulls = plan["nulls"]
    if int(nulls["calibration_count"]) < 1000:
        raise ValueError("At least 1000 calibration nulls are required")
    if int(nulls["sealed_evaluation_count"]) < 500:
        raise ValueError("At least 500 sealed evaluation nulls are required")
    if nulls["calibration_and_evaluation_sets_disjoint"] is not True:
        raise ValueError("Calibration and evaluation nulls must be disjoint")
    if nulls["calibration_seed"] == nulls["sealed_evaluation_seed"]:
        raise ValueError("Calibration and sealed-evaluation seeds must differ")
    if nulls["threshold_estimator"] != "conservative_nearest_rank":
        raise ValueError("Pilot 1 requires a conservative nearest-rank threshold")
    if nulls["trigger_comparison"] != "strictly_greater_than_threshold":
        raise ValueError("Pilot 1 trigger comparison must be strict")
    if nulls["evaluation_binomial_interval"] != "wilson_95_percent":
        raise ValueError("Pilot 1 requires the frozen Wilson interval")

    injections = plan["injections"]
    for name in (
        "main_matrix",
        "annual_identifiability_matrix",
        "search_boundary_matrix",
    ):
        matrix = injections[name]
        periods = [float(value) for value in matrix["periods_days"]]
        amplitudes = [float(value) for value in matrix["amplitudes_microseconds"]]
        phases = [float(value) for value in matrix["phases_radians"]]
        if not periods or not amplitudes or len(phases) < 4:
            raise ValueError(f"{name} must contain periods, amplitudes, and four phases")
        if not _strictly_increasing(periods) or not _strictly_increasing(amplitudes):
            raise ValueError(f"{name} periods and amplitudes must be strictly increasing")
        if any(value <= 0 for value in periods + amplitudes):
            raise ValueError(f"{name} periods and amplitudes must be positive")
        if len(set(phases)) != len(phases):
            raise ValueError(f"{name} phases must be unique")
        if int(matrix["covariance_noise_realizations_per_phase"]) < 1:
            raise ValueError(f"{name} must have at least one noise realization per phase")

    eligibility = plan["candidate_eligibility"]
    if float(eligibility["maximum_signal_astrometry_correlation"]) > 0.8:
        raise ValueError("The annual-coupling eligibility threshold may not exceed 0.8")
    if float(eligibility["maximum_ordinary_model_absorption_fraction"]) > 0.8:
        raise ValueError("The absorption eligibility threshold may not exceed 0.8")

    if plan["independent_audit"]["selection_method"] != (
        "sha256_case_id_rank_lowest_fraction"
    ):
        raise ValueError("Pilot 1 audit selection must be deterministic")

    promotion = plan["promotion"]
    if promotion["milestone"] != "initial-v0.1":
        raise ValueError("Pilot 1 must target the initial-v0.1 milestone")
    if promotion["post_promotion_search_requires_separate_freeze"] is not True:
        raise ValueError("Initial v0.1 search execution must require a separate freeze")
    if promotion["discovery_claim_authorized"] is not False:
        raise ValueError("The Pilot 1 design cannot authorize a discovery claim")


def build_pilot1_plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    validate_pilot1_plan(plan)
    matrices = plan["injections"]
    main_count = _matrix_case_count(matrices["main_matrix"])
    annual_count = _matrix_case_count(matrices["annual_identifiability_matrix"])
    boundary_count = _matrix_case_count(matrices["search_boundary_matrix"])
    injection_count = main_count + annual_count + boundary_count
    audit_count = math.ceil(
        injection_count * float(plan["independent_audit"]["deterministic_fraction"])
    )
    null_count = int(plan["nulls"]["calibration_count"]) + int(
        plan["nulls"]["sealed_evaluation_count"]
    )
    trigger_count = null_count + injection_count

    resources = plan["resource_caps"]
    primary_fit_count = 2 * injection_count
    estimated_seconds = (
        primary_fit_count * float(resources["pilot0_average_fit_wall_seconds_for_planning"])
        + audit_count * float(resources["pilot0_full_covariance_fit_wall_seconds_for_planning"])
        + trigger_count * float(resources["trigger_scan_seconds_per_case_allowance"])
    )

    return {
        "schema_version": 1,
        "plan_id": plan["plan_id"],
        "status": plan["status"],
        "execution_authorized": plan["execution_authorized"],
        "target": plan["target"],
        "case_counts": {
            "calibration_nulls": int(plan["nulls"]["calibration_count"]),
            "sealed_evaluation_nulls": int(plan["nulls"]["sealed_evaluation_count"]),
            "main_injections": main_count,
            "annual_identifiability_injections": annual_count,
            "search_boundary_injections": boundary_count,
            "total_injections": injection_count,
            "total_trigger_scans": trigger_count,
            "primary_timing_fits": primary_fit_count,
            "explicit_full_covariance_audits": audit_count,
        },
        "planning_estimate": {
            "wall_seconds": estimated_seconds,
            "wall_hours": estimated_seconds / 3600.0,
            "macbook_cap_hours": float(resources["macbook_total_wall_hours"]),
            "within_macbook_cap": estimated_seconds
            <= 3600.0 * float(resources["macbook_total_wall_hours"]),
            "basis": "Pilot 0 measured per-fit costs plus a conservative trigger allowance",
        },
        "promotion_milestone": plan["promotion"]["milestone"],
        "promotion_ready": False,
        "block_reason": "Pilot 1 design is review-only; no calibration metrics exist yet.",
    }


def _metric_status(
    metrics: dict[str, Any], key: str, predicate: Callable[[Any], bool]
) -> str:
    if key not in metrics:
        return "BLOCKED"
    return "PASS" if predicate(metrics[key]) else "FAIL"


def evaluate_v01_promotion(plan: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    validate_pilot1_plan(plan)
    thresholds = plan["promotion_benchmarks"]
    resources = plan["resource_caps"]
    nulls = plan["nulls"]

    rows = {
        "calibration_null_count": _metric_status(
            metrics,
            "calibration_nulls_completed",
            lambda value: int(value) >= int(nulls["calibration_count"]),
        ),
        "sealed_evaluation_null_count": _metric_status(
            metrics,
            "sealed_evaluation_nulls_completed",
            lambda value: int(value) >= int(nulls["sealed_evaluation_count"]),
        ),
        "calibration_evaluation_split": _metric_status(
            metrics, "calibration_evaluation_split_preserved", bool
        ),
        "covariance_aware_statistic": _metric_status(
            metrics, "covariance_aware_statistic_used", bool
        ),
        "false_positive_rate": _metric_status(
            metrics,
            "evaluation_false_positive_rate",
            lambda value: float(value)
            <= float(thresholds["evaluation_false_positive_rate_maximum"]),
        ),
        "false_positive_upper_bound": _metric_status(
            metrics,
            "evaluation_false_positive_rate_upper_95",
            lambda value: float(value)
            <= float(thresholds["evaluation_false_positive_rate_upper_95_maximum"]),
        ),
        "strong_control_recovery": _metric_status(
            metrics,
            "strong_control_recovery_rate",
            lambda value: float(value)
            >= float(thresholds["strong_control_recovery_rate_minimum"]),
        ),
        "frequency_recovery": _metric_status(
            metrics,
            "injected_frequency_recovery_rate",
            lambda value: float(value)
            >= float(thresholds["injected_frequency_recovery_rate_minimum"]),
        ),
        "amplitude_bias": _metric_status(
            metrics,
            "median_amplitude_bias_fraction",
            lambda value: float(value)
            <= float(thresholds["median_amplitude_bias_fraction_maximum"]),
        ),
        "phase_error": _metric_status(
            metrics,
            "phase_error_p90_radians",
            lambda value: float(value) <= float(thresholds["phase_error_p90_maximum_radians"]),
        ),
        "monotonic_detection_fraction": _metric_status(
            metrics,
            "periods_with_monotonic_detection_fraction",
            lambda value: int(value)
            >= int(thresholds["minimum_periods_with_monotonic_detection_fraction"]),
        ),
        "sensitivity_bracketing": _metric_status(
            metrics,
            "periods_with_bracketed_50_and_90_percent_sensitivity",
            lambda value: int(value)
            >= int(thresholds["minimum_periods_with_bracketed_50_and_90_percent_sensitivity"]),
        ),
        "annual_eligibility_mask": _metric_status(
            metrics,
            "annual_eligibility_violations",
            lambda value: int(value) <= int(thresholds["annual_eligibility_violations_maximum"]),
        ),
        "independent_covariance_audit": _metric_status(
            metrics,
            "independent_audit_failures",
            lambda value: int(value) <= int(thresholds["independent_audit_failures_maximum"]),
        ),
        "warning_hygiene": _metric_status(
            metrics,
            "unexpected_material_warnings",
            lambda value: int(value)
            <= int(thresholds["unexpected_material_warnings_maximum"]),
        ),
        "null_whitened_variance": _metric_status(
            metrics,
            "null_whitened_variance",
            lambda value: float(thresholds["null_whitened_variance_minimum"])
            <= float(value)
            <= float(thresholds["null_whitened_variance_maximum"]),
        ),
        "null_ensemble_correlation": _metric_status(
            metrics,
            "null_maximum_absolute_ensemble_correlation",
            lambda value: float(value)
            <= float(thresholds["null_maximum_absolute_ensemble_correlation"]),
        ),
        "published_reference_reconciliation": _metric_status(
            metrics,
            "published_100_day_sensitivity_ratio",
            lambda value: float(thresholds["published_100_day_sensitivity_ratio_minimum"])
            <= float(value)
            <= float(thresholds["published_100_day_sensitivity_ratio_maximum"]),
        ),
        "artifact_hashes": _metric_status(metrics, "all_artifact_hashes_verified", bool),
        "runtime": _metric_status(
            metrics,
            "total_wall_hours",
            lambda value: float(value) <= float(resources["macbook_total_wall_hours"]),
        ),
        "memory": _metric_status(
            metrics,
            "peak_memory_gib",
            lambda value: float(value) <= float(resources["peak_memory_gib"]),
        ),
        "storage": _metric_status(
            metrics,
            "complete_data_root_gib",
            lambda value: float(value) <= float(resources["complete_data_root_gib"]),
        ),
        "blind_search_boundary": _metric_status(
            metrics, "blind_real_data_search_executed", lambda value: value is False
        ),
    }
    if any(status == "FAIL" for status in rows.values()):
        overall = "FAIL"
    elif any(status == "BLOCKED" for status in rows.values()):
        overall = "BLOCKED"
    else:
        overall = "PASS"
    return {
        "overall": overall,
        "rows": rows,
        "promotion_milestone": plan["promotion"]["milestone"],
        "promotion_ready": overall == "PASS",
        "post_promotion_search_requires_separate_freeze": True,
        "discovery_claim_authorized": False,
    }
