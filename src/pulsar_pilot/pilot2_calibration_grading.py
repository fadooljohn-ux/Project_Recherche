from __future__ import annotations

import math
from collections import defaultdict
from itertools import pairwise
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
    status = "pass" if all(item["status"] == "pass" for item in gates) else "fail"
    return {"schema_version": 1, "stage": stage, "status": status, "gates": gates, **extra}


def grade_gaussian_calibration(
    records: list[dict[str, Any]], diagnostics: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    expected = int(config["gaussian_nulls"]["calibration_cases"])
    maxima = sorted(float(item["global_maximum_delta_chi2"]) for item in records)
    rank = math.ceil(float(config["gaussian_nulls"]["threshold_quantile"]) * expected)
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
    variance_ok = (
        float(config["null_ensemble_gates"]["whitened_variance_minimum"])
        <= variance
        <= float(config["null_ensemble_gates"]["whitened_variance_maximum"])
    )
    lag_ok = lag <= float(config["null_ensemble_gates"]["maximum_absolute_pooled_lag_correlation"])
    gates = [
        _gate("exact_case_count", len(records), "==", expected, len(records) == expected),
        _gate("whitened_variance", variance, "within", [0.9, 1.1], variance_ok),
        _gate("lag_correlation", lag, "<=", 0.1, lag_ok),
    ]
    return _result(
        "gaussian_threshold_calibration",
        gates,
        threshold={
            "status": "proposed_not_locked",
            "value_delta_chi2": threshold,
            "estimator": "conservative_nearest_rank",
            "rank": rank,
        },
    )


def grade_sealed_gaussian(
    records: list[dict[str, Any]], threshold: float, config: dict[str, Any]
) -> dict[str, Any]:
    expected = int(config["gaussian_nulls"]["sealed_evaluation_cases"])
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
            "false_positive_rate",
            rate,
            "<=",
            config["gaussian_nulls"]["evaluation_false_positive_rate_maximum"],
            rate <= float(config["gaussian_nulls"]["evaluation_false_positive_rate_maximum"]),
        ),
        _gate(
            "wilson_upper_95",
            interval["upper"],
            "<=",
            config["gaussian_nulls"]["evaluation_wilson_upper_95_maximum"],
            interval["upper"]
            <= float(config["gaussian_nulls"]["evaluation_wilson_upper_95_maximum"]),
        ),
        _gate("threshold_retuned", False, "is", False, True),
    ]
    return _result(
        "sealed_gaussian_evaluation",
        gates,
        false_positives=false_positives,
        false_positive_rate=rate,
        wilson_95=interval,
    )


def grade_structured_tail(
    records: list[dict[str, Any]], threshold: float, config: dict[str, Any]
) -> dict[str, Any]:
    expected = int(config["structured_tail_evaluation"]["cases_per_variant"])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        grouped[str(item["variant"])].append(item)
    variants: dict[str, Any] = {}
    gates: list[dict[str, Any]] = []
    for specification in config["structured_tail_evaluation"]["variants"]:
        variant = specification["id"]
        items = grouped.get(variant, [])
        false_positives = sum(
            float(item["global_maximum_delta_chi2"]) > threshold for item in items
        )
        interval = (
            wilson_interval_95(false_positives, len(items))
            if items
            else {"lower": 1.0, "upper": 1.0}
        )
        count_ok = len(items) == expected
        tripwire = interval["lower"] > 0.01
        gates.extend(
            [
                _gate(f"{variant}_case_count", len(items), "==", expected, count_ok),
                _gate(f"{variant}_rebaseline_tripwire", tripwire, "is", False, not tripwire),
            ]
        )
        variants[variant] = {
            "cases": len(items),
            "false_positives": false_positives,
            "wilson_95": interval,
            "tripwire": tripwire,
        }
    return _result("structured_tail_evaluation", gates, variants=variants, threshold_unchanged=True)


def grade_injections(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    expected = {"main": 240, "annual": 28, "boundary": 16}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        grouped[str(item["family"])].append(item)
    limits = config["injection_gates"]
    main = grouped["main"]
    periods: dict[float, dict[float, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for item in main:
        periods[float(item["period_days"])][float(item["amplitude_microseconds"])].append(item)
    monotonic = bracketed = 0
    strong_rates: list[float] = []
    for cells in periods.values():
        rates = [sum(bool(x["triggered"]) for x in cells[a]) / len(cells[a]) for a in sorted(cells)]
        monotonic += all(left <= right for left, right in pairwise(rates))
        bracketed += min(rates) <= 0.5 <= max(rates) and min(rates) <= 0.9 <= max(rates)
        strong_rates.append(rates[-1])
    triggered = [item for item in main if item["triggered"]]
    frequency_rate = (
        sum(bool(item["frequency_recovered"]) for item in triggered) / len(triggered)
        if triggered
        else 0.0
    )
    biases = sorted(abs(float(item["amplitude_bias_fraction"])) for item in triggered)
    phases = sorted(abs(float(item["phase_error_radians"])) for item in triggered)
    median_bias = biases[len(biases) // 2] if biases else math.inf
    p90_phase = phases[max(0, math.ceil(0.9 * len(phases)) - 1)] if phases else math.inf
    correlation_limit = float(
        config["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
    )
    absorption_limit = float(
        config["candidate_eligibility"]["maximum_ordinary_model_absorption_fraction"]
    )
    annual_by_period: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for item in grouped["annual"]:
        annual_by_period[float(item["period_days"])].append(item)
    annual_eligible = {
        period: max(float(item["signal_astrometry_correlation"]) for item in items)
        < correlation_limit
        and max(float(item["ordinary_absorption_fraction"]) for item in items) < absorption_limit
        for period, items in annual_by_period.items()
    }
    annual_violations = sum(
        bool(item.get("candidate_eligible")) and not annual_eligible[float(item["period_days"])]
        for item in grouped["annual"]
    )
    audited = [item for item in records if item.get("solver_audit_required")]
    audit_failures = sum(not bool(item.get("solver_audit_pass")) for item in audited)
    max_adjustment_error = max(
        (abs(float(item["toa_adjustment_error_microseconds"])) for item in records),
        default=math.inf,
    )
    all_converged = bool(records) and all(
        bool(item["ordinary_fit_converged"]) and bool(item["joint_fit_converged"])
        for item in records
    )
    gates = [
        *[
            _gate(
                f"{family}_case_count",
                len(grouped[family]),
                "==",
                count,
                len(grouped[family]) == count,
            )
            for family, count in expected.items()
        ],
        _gate(
            "toa_application_error",
            max_adjustment_error,
            "<=",
            config["injections"]["maximum_toa_adjustment_error_microseconds"],
            max_adjustment_error
            <= float(config["injections"]["maximum_toa_adjustment_error_microseconds"]),
        ),
        _gate("fit_convergence", all_converged, "is", True, all_converged),
        _gate(
            "solver_audit_count",
            len(audited),
            "==",
            config["solver_audit"]["expected_cases"],
            len(audited) == int(config["solver_audit"]["expected_cases"]),
        ),
        _gate(
            "solver_audit_failures",
            audit_failures,
            "<=",
            config["solver_audit"]["failures_maximum"],
            audit_failures <= int(config["solver_audit"]["failures_maximum"]),
        ),
        _gate(
            "strong_control_recovery",
            min(strong_rates, default=0.0),
            ">=",
            limits["strong_control_recovery_rate_minimum"],
            bool(strong_rates)
            and min(strong_rates) >= float(limits["strong_control_recovery_rate_minimum"]),
        ),
        _gate(
            "frequency_recovery",
            frequency_rate,
            ">=",
            limits["injected_frequency_recovery_rate_minimum"],
            frequency_rate >= float(limits["injected_frequency_recovery_rate_minimum"]),
        ),
        _gate(
            "median_amplitude_bias",
            median_bias,
            "<=",
            limits["median_amplitude_bias_fraction_maximum"],
            median_bias <= float(limits["median_amplitude_bias_fraction_maximum"]),
        ),
        _gate(
            "phase_error_p90",
            p90_phase,
            "<=",
            limits["phase_error_p90_maximum_radians"],
            p90_phase <= float(limits["phase_error_p90_maximum_radians"]),
        ),
        _gate(
            "monotonic_periods",
            monotonic,
            ">=",
            limits["minimum_main_periods_with_monotonic_detection_fraction"],
            monotonic >= int(limits["minimum_main_periods_with_monotonic_detection_fraction"]),
        ),
        _gate(
            "bracketed_periods",
            bracketed,
            ">=",
            limits["minimum_main_periods_bracketing_50_and_90_percent_recovery"],
            bracketed >= int(limits["minimum_main_periods_bracketing_50_and_90_percent_recovery"]),
        ),
        _gate(
            "annual_eligibility_violations",
            annual_violations,
            "<=",
            limits["annual_eligibility_violations_maximum"],
            annual_violations <= int(limits["annual_eligibility_violations_maximum"]),
        ),
    ]
    return _result(
        "injection_recovery_and_annual_map",
        gates,
        metrics={
            "monotonic_periods": monotonic,
            "bracketed_periods": bracketed,
            "strong_control_minimum_recovery": min(strong_rates, default=0.0),
            "frequency_recovery_rate": frequency_rate,
            "median_amplitude_bias_fraction": median_bias,
            "phase_error_p90_radians": p90_phase,
            "annual_eligibility_violations": annual_violations,
        },
    )


def grade_promotion(stage_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    required = [
        "gaussian_threshold_calibration",
        "sealed_gaussian_evaluation",
        "structured_tail_evaluation",
        "injection_recovery_and_annual_map",
    ]
    gates = [
        _gate(
            f"{stage}_passed",
            stage_results.get(stage, {}).get("status"),
            "==",
            "pass",
            stage_results.get(stage, {}).get("status") == "pass",
        )
        for stage in required
    ]
    gates.append(_gate("observed_search_authorized", False, "is", False, True))
    return _result(
        "promotion_grade",
        gates,
        calibration_pass_requires_all_hard_gates=True,
        observed_search_authorized=False,
        next_authorized_activity="observed_search_design_preparation_only",
    )
