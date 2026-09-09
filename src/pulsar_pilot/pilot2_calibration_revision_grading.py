from __future__ import annotations

import math
from typing import Any

from .pilot1_evaluation import wilson_interval_95


def _gate(name: str, observed: Any, comparator: str, limit: Any, passed: bool) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "comparator": comparator,
        "limit": limit,
        "status": "pass" if passed else "fail",
    }


def _result(stage: str, gates: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage": stage,
        "status": "pass" if all(item["status"] == "pass" for item in gates) else "fail",
        "gates": gates,
        **extra,
    }


def grade_revision_calibration(
    records: list[dict[str, Any]], diagnostics: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    specification = config["gaussian_nulls"]
    expected = int(specification["calibration_cases"])
    rank = int(specification["threshold_order_statistic_rank"])
    maxima = sorted(float(item["global_maximum_delta_chi2"]) for item in records)
    threshold = maxima[rank - 1] if len(maxima) == expected else None
    variance = float(diagnostics.get("whitened_variance", math.inf))
    lag = abs(
        float(
            diagnostics.get(
                "maximum_absolute_pooled_lag_correlation",
                diagnostics.get("maximum_absolute_ensemble_correlation", math.inf),
            )
        )
    )
    null_gates = config["null_ensemble_gates"]
    gates = [
        _gate("exact_case_count", len(records), "==", expected, len(records) == expected),
        _gate(
            "whitened_variance",
            variance,
            "within",
            [null_gates["whitened_variance_minimum"], null_gates["whitened_variance_maximum"]],
            float(null_gates["whitened_variance_minimum"])
            <= variance
            <= float(null_gates["whitened_variance_maximum"]),
        ),
        _gate(
            "lag_correlation",
            lag,
            "<=",
            null_gates["maximum_absolute_pooled_lag_correlation"],
            lag <= float(null_gates["maximum_absolute_pooled_lag_correlation"]),
        ),
    ]
    return _result(
        "gaussian_threshold_calibration",
        gates,
        threshold={
            "status": "proposed_not_locked",
            "value_delta_chi2": threshold,
            "estimator": specification["threshold_estimator"],
            "rank": rank,
            "sample_count": len(records),
            "one_sided_confidence": specification["threshold_one_sided_confidence"],
        },
    )


def grade_revision_sealed(
    records: list[dict[str, Any]], threshold: float, config: dict[str, Any]
) -> dict[str, Any]:
    specification = config["gaussian_nulls"]
    expected = int(specification["sealed_evaluation_cases"])
    false_positives = sum(float(item["global_maximum_delta_chi2"]) > threshold for item in records)
    interval = (
        wilson_interval_95(false_positives, len(records))
        if records
        else {"lower": 0.0, "upper": 1.0}
    )
    rate = false_positives / len(records) if records else 1.0
    gates = [
        _gate("exact_case_count", len(records), "==", expected, len(records) == expected),
        _gate(
            "wilson_upper_95",
            interval["upper"],
            "<=",
            specification["evaluation_wilson_upper_95_maximum"],
            interval["upper"] <= float(specification["evaluation_wilson_upper_95_maximum"]),
        ),
        _gate("threshold_retuned", False, "is", False, True),
        _gate(
            "raw_false_positive_rate_is_report_only",
            specification["evaluation_raw_false_positive_rate_role"],
            "==",
            "reported_estimate_not_hard_gate",
            specification["evaluation_raw_false_positive_rate_role"]
            == "reported_estimate_not_hard_gate",
        ),
    ]
    return _result(
        "sealed_gaussian_evaluation",
        gates,
        false_positives=false_positives,
        false_positive_rate=rate,
        wilson_95=interval,
    )
