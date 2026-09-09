"""Current case grading and record contract; historical runners remain archival.

Numerical rules extracted unchanged from v0.2.2 grading and v0.2.7 schemas.
"""

from __future__ import annotations

import math
from collections import defaultdict
from itertools import pairwise
from typing import Any

import numpy as np

from .injection_integrity import (
    DM_ERROR_KEY,
    TOA_ADJUSTMENT_KEY,
    UNCENTERED_TARGET_KEY,
    toa_adjustment_gate_value,
)

STAGE = "injection_remediation_evaluation"


def _gate(name: str, observed: Any, comparator: str, limit: Any, passed: bool) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "comparator": comparator,
        "limit": limit,
        "status": "pass" if passed else "fail",
    }


def _nearest_rank(values: list[float], quantile: float) -> float:
    if not values:
        return math.inf
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def grade_records(
    records: list[dict[str, Any]],
    base_config: dict[str, Any],
    remediation: dict[str, Any],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["family"])].append(record)
    expected = {"main": 240, "phase_reference": 60, "annual": 28, "boundary": 16}
    gates = [
        _gate(
            f"{family}_case_count",
            len(grouped[family]),
            "==",
            count,
            len(grouped[family]) == count,
        )
        for family, count in expected.items()
    ]
    canonical_failures = 0
    adjustment_values: list[float] = []
    for record in records:
        try:
            adjustment_values.append(toa_adjustment_gate_value(record))
        except (TypeError, ValueError):
            canonical_failures += 1
    maximum_adjustment = max(adjustment_values, default=math.inf)
    adjustment_limit = float(
        remediation["application_integrity"]["toa_adjustment_maximum_microseconds"]
    )
    gates.extend(
        [
            _gate(
                "canonical_toa_metrics",
                canonical_failures,
                "==",
                0,
                canonical_failures == 0 and len(adjustment_values) == len(records),
            ),
            _gate(
                "toa_application_error",
                maximum_adjustment,
                "<=",
                adjustment_limit,
                maximum_adjustment <= adjustment_limit,
            ),
        ]
    )
    all_converged = bool(records) and all(
        bool(item["ordinary_fit_converged"]) and bool(item["joint_fit_converged"])
        for item in records
    )
    audited = [item for item in records if bool(item.get("solver_audit_required"))]
    audit_failures = sum(not bool(item.get("solver_audit_pass")) for item in audited)
    gates.extend(
        [
            _gate("fit_convergence", all_converged, "is", True, all_converged),
            _gate("solver_audit_count", len(audited), "==", 35, len(audited) == 35),
            _gate(
                "solver_audit_failures",
                audit_failures,
                "==",
                0,
                audit_failures == 0,
            ),
        ]
    )
    main = grouped["main"]
    periods: dict[float, dict[float, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for item in main:
        periods[float(item["period_days"])][float(item["amplitude_microseconds"])].append(item)
    monotonic = 0
    bracketed = 0
    strong_rates: list[float] = []
    for cells in periods.values():
        rates = [
            sum(bool(item["triggered"]) for item in cells[amplitude]) / len(cells[amplitude])
            for amplitude in sorted(cells)
        ]
        monotonic += all(left <= right for left, right in pairwise(rates))
        bracketed += min(rates) <= 0.5 <= max(rates) and min(rates) <= 0.9 <= max(rates)
        strong_rates.append(rates[-1])
    triggered = [item for item in main if bool(item["triggered"])]
    frequency_rate = (
        sum(bool(item["frequency_recovered"]) for item in triggered) / len(triggered)
        if triggered
        else 0.0
    )
    median_bias = (
        float(np.median([abs(float(item["amplitude_bias_fraction"])) for item in triggered]))
        if triggered
        else math.inf
    )
    main_phase_p90 = _nearest_rank(
        [abs(float(item["phase_error_radians"])) for item in triggered], 0.9
    )
    limits = base_config["injection_gates"]
    gates.extend(
        [
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
                bracketed
                >= int(limits["minimum_main_periods_bracketing_50_and_90_percent_recovery"]),
            ),
        ]
    )
    phase_reference = grouped["phase_reference"]
    reference_p90 = _nearest_rank(
        [abs(float(item["phase_error_radians"])) for item in phase_reference], 0.9
    )
    reference_limit = float(
        remediation["phase_reference_controls"]["phase_error_p90_maximum_radians"]
    )
    all_reference_triggered = len(phase_reference) == 60 and all(
        bool(item["triggered"]) for item in phase_reference
    )
    gates.extend(
        [
            _gate(
                "phase_reference_trigger_recovery",
                sum(bool(item["triggered"]) for item in phase_reference),
                "==",
                60,
                all_reference_triggered,
            ),
            _gate(
                "phase_reference_error_p90",
                reference_p90,
                "<=",
                reference_limit,
                reference_p90 <= reference_limit,
            ),
        ]
    )
    correlation_limit = float(
        base_config["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
    )
    absorption_limit = float(
        base_config["candidate_eligibility"]["maximum_ordinary_model_absorption_fraction"]
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
    gates.append(
        _gate(
            "annual_eligibility_violations",
            annual_violations,
            "==",
            0,
            annual_violations == 0,
        )
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "status": "pass" if all(gate["status"] == "pass" for gate in gates) else "fail",
        "gates": gates,
        "diagnostics": {
            "all_triggered_main_phase_error_role": "diagnostic_not_hard_gate",
            "all_triggered_main_phase_error_p90_radians": main_phase_p90,
            "phase_reference_error_p90_radians": reference_p90,
            "strong_control_minimum_recovery": min(strong_rates, default=0.0),
            "frequency_recovery_rate": frequency_rate,
            "median_amplitude_bias_fraction": median_bias,
            "monotonic_periods": monotonic,
            "bracketed_periods": bracketed,
        },
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
    }


PHASE_TELEMETRY_KEYS = (
    "recovered_sine_microseconds",
    "recovered_cosine_microseconds",
    "sine_uncertainty_microseconds",
    "cosine_uncertainty_microseconds",
    "sine_cosine_correlation",
    "sine_cosine_covariance_microseconds_squared",
    "recovered_phase_radians",
    "phase_standard_error_radians",
    "signed_wrapped_phase_error_radians",
)

RECORD_NUMERIC_KEYS = (
    "period_days",
    "amplitude_microseconds",
    "phase_radians",
    "locked_threshold_delta_chi2",
    "global_maximum_delta_chi2",
    "frequency_recovery_tolerance_per_day",
    "amplitude_bias_fraction",
    "phase_error_radians",
    *PHASE_TELEMETRY_KEYS,
    "toa_adjustment_error_microseconds",
    TOA_ADJUSTMENT_KEY,
    UNCENTERED_TARGET_KEY,
    DM_ERROR_KEY,
    "ordinary_absorption_fraction",
    "signal_astrometry_correlation",
)

RECORD_BOOLEAN_KEYS = (
    "triggered",
    "frequency_recovered",
    "ordinary_fit_converged",
    "joint_fit_converged",
    "solver_audit_required",
    "solver_audit_pass",
    "observed_residual_vector_used",
    "observed_periodic_scan_executed",
)

BASE_RECORD_KEYS = {
    "schema_version",
    "run_id",
    "execution_binding_sha256",
    "case",
    "family",
    *RECORD_NUMERIC_KEYS,
    *RECORD_BOOLEAN_KEYS,
    "solver_comparison",
    "full_covariance_solver",
    "input_binding",
}

FULL_SOLVER_KEYS = {
    "solver",
    "completed",
    "returned_chi2",
    "sine_us",
    "cosine_us",
    "amplitude_us",
    "phase_radians",
    "sine_uncertainty_us",
    "cosine_uncertainty_us",
    "chi2",
    "reduced_chi2",
    "weighted_rms_us",
    "free_parameter_count",
    "release_red_noise_preserved",
    "wavex_absent",
}


def _finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _validate_solver_payload(record: dict[str, Any], audit_required: bool) -> list[str]:
    comparison = record.get("solver_comparison")
    solver = record.get("full_covariance_solver")
    if not audit_required:
        return [] if comparison is None and solver is None else ["unexpected solver-audit payload"]
    failures: list[str] = []
    comparison_keys = {
        "amplitude_difference_microseconds",
        "phase_difference_radians",
        "chi2_difference",
    }
    if not isinstance(comparison, dict) or set(comparison) != comparison_keys:
        failures.append("solver comparison schema differs")
    elif not all(_finite_number(value) and value >= 0 for value in comparison.values()):
        failures.append("solver comparison contains an invalid value")
    if not isinstance(solver, dict) or set(solver) != FULL_SOLVER_KEYS:
        failures.append("full-covariance solver schema differs")
        return failures
    if solver.get("solver") != "WidebandTOAFitter_explicit_full_covariance":
        failures.append("full-covariance solver identity differs")
    for key in ("completed", "release_red_noise_preserved", "wavex_absent"):
        if type(solver.get(key)) is not bool:
            failures.append(f"full-covariance solver boolean is invalid: {key}")
    if type(solver.get("free_parameter_count")) is not int or solver["free_parameter_count"] < 0:
        failures.append("full-covariance solver parameter count is invalid")
    numeric = FULL_SOLVER_KEYS - {
        "solver",
        "completed",
        "free_parameter_count",
        "release_red_noise_preserved",
        "wavex_absent",
    }
    for key in numeric:
        if not _finite_number(solver.get(key)):
            failures.append(f"full-covariance solver value is invalid: {key}")
    return failures
