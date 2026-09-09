from __future__ import annotations

import copy
import json
from collections.abc import Callable
from typing import Any

import numpy as np

from .c1 import generate_circular_delay_us
from .c1r1 import _joint_downhill_fit, _joint_full_covariance_fit, wrapped_phase_difference
from .c3 import extract_annual_correlation_diagnostic
from .injection_integrity import phase_measurement_diagnostics, separate_application_diagnostics
from .pilot1_benchmark import _synthetic_toas
from .pilot1_runtime import generate_covariance_null
from .pilot2_injection_executor import (
    ASTROMETRIC_PARAMETERS,
    InjectionContext,
    _solver_audit_pass,
)
from .pilot2_preflight import MAX_FIT_ITERATIONS


def _correlation_parameter_block(fitter: Any) -> Any:
    correlation = getattr(fitter, "parameter_correlation_matrix", None)
    if correlation is None or not hasattr(correlation, "get_label_matrix"):
        raise RuntimeError("Fitted PINT correlation-matrix object is unavailable")
    block = correlation.get_label_matrix(["CSSIN", "CSCOS"])
    matrix = np.asarray(block.matrix, dtype=float)
    if matrix.shape != (2, 2) or not np.all(np.isfinite(matrix)):
        raise RuntimeError("Fitted PINT CSSIN/CSCOS correlation block is invalid")
    return block


def phase_telemetry(primary: dict[str, Any], injected_phase: float) -> dict[str, float]:
    block = _correlation_parameter_block(primary["fitter"])
    diagnostics = phase_measurement_diagnostics(
        float(primary["sine_us"]),
        float(primary["cosine_us"]),
        float(primary["sine_uncertainty_us"]),
        float(primary["cosine_uncertainty_us"]),
        float(block.matrix[0, 1]),
    )
    diagnostics["signed_wrapped_phase_error_radians"] = wrapped_phase_difference(
        diagnostics["recovered_phase_radians"], injected_phase
    )
    return diagnostics


def execute_injection_case(
    context: InjectionContext,
    case: dict[str, Any],
    threshold: float,
    audit_required: bool,
    config: dict[str, Any],
    execution_binding: str,
    on_operation: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    from pint.fitter import WidebandDownhillFitter
    from pint.residuals import WidebandTOAResiduals

    def completed(name: str) -> None:
        if on_operation is not None:
            on_operation(name)

    count = len(context.toas)
    noise = generate_covariance_null(
        context.scanner.covariance_cholesky, np.random.default_rng(int(case["seed"]))
    )
    completed("random_draws")
    signal_us = np.asarray(
        generate_circular_delay_us(
            context.times.astype(np.longdouble),
            float(case["period_days"]),
            float(case["amplitude_microseconds"]),
            float(case["phase_radians"]),
            context.reference_epoch,
        ),
        dtype=float,
    )
    requested = noise.copy()
    requested[:count] += signal_us * 1e-6
    scan = context.scanner.scan(requested)
    completed("scans")
    synthetic, application = _synthetic_toas(context.toas, context.model, requested)
    ordinary = WidebandDownhillFitter(synthetic, copy.deepcopy(context.model))
    ordinary_returned = bool(ordinary.fit_toas(maxiter=MAX_FIT_ITERATIONS))
    completed("primary_fits")
    ordinary_residuals = WidebandTOAResiduals(synthetic, ordinary.model)
    exact = context.exact_scanners[float(case["period_days"])].scan(
        ordinary_residuals.calc_wideband_resids()
    )
    postfit_amplitude = float(exact["amplitude_us"])
    absorption = float(
        np.clip(
            1.0 - postfit_amplitude / float(case["amplitude_microseconds"]), 0.0, 1.0
        )
    )
    injected_frequency = 1.0 / float(case["period_days"])
    primary = _joint_downhill_fit(
        synthetic,
        context.model,
        injected_frequency,
        context.reference_epoch,
        MAX_FIT_ITERATIONS,
    )
    completed("primary_fits")
    telemetry = phase_telemetry(primary, float(case["phase_radians"]))
    application_diagnostics = separate_application_diagnostics(application)
    comparison: dict[str, float] | None = None
    audit_payload: dict[str, Any] | None = None
    audit_pass = True
    if audit_required:
        audit = _joint_full_covariance_fit(
            synthetic,
            context.model,
            injected_frequency,
            context.reference_epoch,
            MAX_FIT_ITERATIONS,
        )
        completed("solver_audits")
        comparison = {
            "amplitude_difference_microseconds": abs(
                float(primary["amplitude_us"]) - float(audit["amplitude_us"])
            ),
            "phase_difference_radians": abs(
                wrapped_phase_difference(
                    float(primary["phase_radians"]), float(audit["phase_radians"])
                )
            ),
            "chi2_difference": abs(float(primary["chi2"]) - float(audit["chi2"])),
        }
        audit_pass = _solver_audit_pass(primary, audit, comparison, config)
        audit_payload = {
            key: value
            for key, value in audit.items()
            if key not in {"fitter", "model", "residuals"}
        }
    astrometric_correlation = 0.0
    if case["family"] == "annual":
        diagnostic = extract_annual_correlation_diagnostic(
            primary["fitter"], list(ASTROMETRIC_PARAMETERS)
        )
        astrometric_correlation = float(diagnostic["maximum_absolute_correlation"])
    independent_bin = 1.0 / float(np.ptp(context.times))
    amplitude_bias = abs(
        float(primary["amplitude_us"]) - float(case["amplitude_microseconds"])
    ) / float(case["amplitude_microseconds"])
    record = {
        "schema_version": 3,
        "run_id": "pilot2-b1937-injection-remediation-v0.2.3",
        "execution_binding_sha256": execution_binding,
        "case": case,
        "family": case["family"],
        "period_days": float(case["period_days"]),
        "amplitude_microseconds": float(case["amplitude_microseconds"]),
        "phase_radians": float(case["phase_radians"]),
        "locked_threshold_delta_chi2": threshold,
        "global_maximum_delta_chi2": float(scan["trigger_statistic"]),
        "triggered": float(scan["trigger_statistic"]) > threshold,
        "frequency_recovered": abs(
            float(scan["peak_frequency_per_day"]) - injected_frequency
        )
        <= independent_bin,
        "frequency_recovery_tolerance_per_day": independent_bin,
        "amplitude_bias_fraction": amplitude_bias,
        "phase_error_radians": abs(telemetry["signed_wrapped_phase_error_radians"]),
        **telemetry,
        "toa_adjustment_error_microseconds": application_diagnostics[
            "toa_adjustment_maximum_absolute_error_microseconds"
        ],
        **application_diagnostics,
        "ordinary_fit_converged": ordinary_returned and bool(ordinary.converged),
        "joint_fit_converged": bool(primary["returned_converged"])
        and bool(primary["fitter_converged"]),
        "ordinary_absorption_fraction": absorption,
        "signal_astrometry_correlation": astrometric_correlation,
        "solver_audit_required": audit_required,
        "solver_audit_pass": audit_pass,
        "solver_comparison": comparison,
        "full_covariance_solver": audit_payload,
        "input_binding": context.input_binding,
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
    }
    return json.loads(json.dumps(record, sort_keys=True))
