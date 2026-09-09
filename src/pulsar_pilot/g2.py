from __future__ import annotations

import copy
import json
import os
import platform
import resource
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .config import PilotConfig
from .provenance import logical_path

EXPECTED_WARNING_DISPOSITIONS = {
    "tai2tt_bipm2019.clk overrides global clock file tai2tt_bipm2019.clk": (
        "expected controlled release-clock override"
    ),
    "time_gbt.dat overrides global clock file time_gbt.dat": (
        "expected controlled release-clock override"
    ),
    "Unexpected parameter toa_noise_params": (
        "PINT 1.1.5 covariance-axis bookkeeping label; not a timing-model parameter"
    ),
}


def compare_parameter_values(
    release_value: float,
    postfit_value: float,
    release_uncertainty: float,
    sigma_multiplier: float,
    numerical_tolerance_ulps: int,
) -> dict[str, float | bool]:
    release_ld = np.longdouble(release_value)
    postfit_ld = np.longdouble(postfit_value)
    uncertainty_ld = np.longdouble(release_uncertainty)
    numerical_floor = abs(np.spacing(release_ld)) * numerical_tolerance_ulps
    sigma_limit = sigma_multiplier * abs(uncertainty_ld)
    threshold = max(numerical_floor, sigma_limit)
    delta = postfit_ld - release_ld
    return {
        "release_value": float(release_ld),
        "postfit_value": float(postfit_ld),
        "delta": float(delta),
        "release_uncertainty": float(uncertainty_ld),
        "delta_sigma": float(abs(delta) / uncertainty_ld) if uncertainty_ld else float("inf"),
        "numerical_floor": float(numerical_floor),
        "acceptance_threshold": float(threshold),
        "pass": bool(abs(delta) <= threshold and uncertainty_ld > 0),
    }


def validate_free_parameters(observed: list[str], expected_base: list[str]) -> dict[str, Any]:
    observed_base = [name for name in observed if not name.startswith("DMX_")]
    dmx = [name for name in observed if name.startswith("DMX_")]
    missing = sorted(set(expected_base) - set(observed_base))
    unexpected = sorted(set(observed_base) - set(expected_base))
    return {
        "status": "pass" if not missing and not unexpected and dmx else "fail",
        "free_parameter_count": len(observed),
        "free_dmx_count": len(dmx),
        "missing_base_parameters": missing,
        "unexpected_base_parameters": unexpected,
    }


def classify_warning_lines(lines: list[str]) -> dict[str, Any]:
    warning_lines = [line for line in lines if "WARNING" in line or "ERROR" in line]
    expected: list[dict[str, str]] = []
    unexpected: list[str] = []
    for line in warning_lines:
        matches = [
            (pattern, disposition)
            for pattern, disposition in EXPECTED_WARNING_DISPOSITIONS.items()
            if pattern in line
        ]
        if matches:
            expected.append({"warning": line, "disposition": matches[0][1]})
        else:
            unexpected.append(line)
    return {
        "status": "pass" if not unexpected else "fail",
        "expected_warning_count": len(expected),
        "expected_warnings": expected,
        "unexpected_warning_count": len(unexpected),
        "unexpected_warnings": unexpected,
    }


def _peak_rss_mib() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**2 if platform.system() == "Darwin" else 1024
    return peak / divisor


def _normality_diagnostics(values: np.ndarray) -> dict[str, float | int]:
    from pint.utils import anderson_darling
    from scipy.stats import kstest

    values = values.astype(float)
    ks_result = kstest(values, "norm")
    ad_statistic, ad_pvalue_raw = anderson_darling(values)
    return {
        "count": len(values),
        "mean": float(np.mean(values)),
        "standard_deviation": float(np.std(values, ddof=1)),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "ks_statistic": float(ks_result.statistic),
        "ks_pvalue": float(ks_result.pvalue),
        "anderson_darling_statistic": float(ad_statistic),
        "anderson_darling_pvalue": float(np.asarray(ad_pvalue_raw).reshape(-1)[0]),
    }


def run_g2(config: PilotConfig, data_root: Path) -> dict[str, Any]:
    controlled = data_root / "controlled" / "nanograv15yr-v2.1.0"
    clock_dir = controlled / "clock"
    par_path = controlled / "wideband" / "par" / "J1744-1134_PINT_20230131.wb.par"
    tim_path = controlled / "wideband" / "tim" / "J1744-1134_PINT_20230131.wb.tim"
    for required in (clock_dir, par_path, tim_path):
        if not required.exists():
            raise FileNotFoundError(f"Required controlled input is missing: {required}")

    recorded = datetime.now(UTC)
    run_id = recorded.strftime("%Y%m%dT%H%M%SZ")
    run_dir = data_root / "run_records"
    derived_dir = data_root / "derived" / "g2"
    cache_root = data_root / "derived" / "cache"
    for directory in (run_dir, derived_dir, cache_root):
        directory.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"g2_refit_{run_id}.log"
    record_path = run_dir / f"g2_refit_{run_id}.json"
    postfit_path = derived_dir / f"J1744-1134_{run_id}.postfit.par"

    os.environ["PINT_CLOCK_OVERRIDE"] = str(clock_dir)
    os.environ["XDG_CACHE_HOME"] = str(cache_root)

    import astropy.units as u
    import pint
    import pint.logging
    from pint.fitter import WidebandDownhillFitter
    from pint.models import get_model_and_toas
    from pint.residuals import WidebandTOAResiduals

    pint.logging.setup(
        level="INFO",
        sink=log_path,
        usecolors=False,
        capturewarnings=True,
        removeprior=True,
    )

    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    release_model, toas = get_model_and_toas(
        par_path,
        tim_path,
        ephem="DE440",
        include_bipm=True,
        bipm_version="BIPM2019",
        planets=True,
        usepickle=False,
        limits="warn",
    )
    configuration = validate_free_parameters(release_model.free_params, config.free_base_parameters)
    if configuration["status"] != "pass":
        raise RuntimeError(f"Released free-parameter set violates the frozen configuration: {configuration}")

    reference_residuals = WidebandTOAResiduals(toas, release_model)
    reference_rms_us = float(reference_residuals.toa.rms_weighted().to_value(u.us))
    reference_chi2 = float(reference_residuals.chi2)

    fit_start = time.perf_counter()
    fitter = WidebandDownhillFitter(toas, copy.deepcopy(release_model))
    fit_returned_converged = bool(fitter.fit_toas(maxiter=config.max_fit_iterations))
    fit_wall_seconds = time.perf_counter() - fit_start
    postfit_model = fitter.model
    postfit_residuals = WidebandTOAResiduals(toas, postfit_model)
    postfit_rms_us = float(postfit_residuals.toa.rms_weighted().to_value(u.us))
    postfit_chi2 = float(postfit_residuals.chi2)
    whitened = postfit_residuals.calc_wideband_whitened_resids()
    whitened_toa = postfit_residuals.calc_whitened_resids()
    whitened_dm = postfit_residuals.calc_whitened_dm_resids()

    comparisons: list[dict[str, Any]] = []
    for name in release_model.free_params:
        release_parameter = getattr(release_model, name)
        postfit_parameter = getattr(postfit_model, name)
        if release_parameter.uncertainty is None:
            comparison: dict[str, Any] = {
                "name": name,
                "unit": str(release_parameter.units),
                "pass": False,
                "reason": "released uncertainty is missing",
            }
        else:
            unit = release_parameter.units
            comparison = {
                "name": name,
                "unit": str(unit),
                **compare_parameter_values(
                    release_parameter.quantity.to_value(unit),
                    postfit_parameter.quantity.to_value(unit),
                    release_parameter.uncertainty.to_value(unit),
                    config.parameter_sigma_tolerance,
                    config.numerical_tolerance_ulps,
                ),
                "postfit_uncertainty": (
                    float(postfit_parameter.uncertainty.to_value(unit))
                    if postfit_parameter.uncertainty is not None
                    else None
                ),
            }
        comparisons.append(comparison)

    parameter_failures = [item["name"] for item in comparisons if not item["pass"]]
    worst_delta_sigma = max(float(item.get("delta_sigma", float("inf"))) for item in comparisons)
    uncertainty_changes = [
        (
            abs(float(item["postfit_uncertainty"]) / float(item["release_uncertainty"]) - 1),
            item["name"],
        )
        for item in comparisons
        if item.get("postfit_uncertainty") is not None and item.get("release_uncertainty")
    ]
    worst_uncertainty_change, worst_uncertainty_parameter = max(uncertainty_changes)
    rms_relative_difference = abs(postfit_rms_us - reference_rms_us) / reference_rms_us

    postfit_path.write_text(
        postfit_model.as_parfile(comment="Project Recherche Gate G2 controlled refit"),
        encoding="utf-8",
    )
    postfit_path.chmod(0o444)

    sanitized_lines = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    warnings = classify_warning_lines(sanitized_lines)
    total_wall_seconds = time.perf_counter() - wall_start
    peak_rss_mib = _peak_rss_mib()
    criteria = {
        "configuration": configuration["status"] == "pass",
        "fit_converged": fit_returned_converged and bool(fitter.converged),
        "parameters_within_tolerance": not parameter_failures,
        "weighted_rms_within_5_percent": (
            rms_relative_difference <= config.weighted_rms_tolerance_fraction
        ),
        "material_warnings_dispositioned": warnings["status"] == "pass",
        "runtime_under_60_minutes": total_wall_seconds <= 3600,
        "peak_memory_under_16_gib": peak_rss_mib <= 16 * 1024,
    }
    status = "pass" if all(criteria.values()) else "fail"

    record: dict[str, Any] = {
        "schema_version": 1,
        "recorded_utc": recorded.isoformat(),
        "run_id": run_id,
        "gate": "G2_published_solution_reproduction",
        "status": status,
        "dataset": "nanograv15yr-v2.1.0",
        "target": "J1744-1134",
        "mode": "wideband",
        "inputs": {
            "par": logical_path(par_path, data_root),
            "tim": logical_path(tim_path, data_root),
            "clock_override": logical_path(clock_dir, data_root),
            "ephemeris": "DE440",
            "timescale": "TT(BIPM2019)",
            "fitter": "WidebandDownhillFitter",
            "max_iterations": config.max_fit_iterations,
            "full_covariance": False,
        },
        "software": {
            "python": platform.python_version(),
            "pint_pulsar": pint.__version__,
            "numpy": np.__version__,
            "process_machine": platform.machine(),
            "longdouble_mantissa_bits": int(np.finfo(np.longdouble).nmant),
        },
        "observations": {
            "ntoas": len(toas),
            "mjd_min": float(toas.get_mjds().min().value),
            "mjd_max": float(toas.get_mjds().max().value),
        },
        "fit": {
            "returned_converged": fit_returned_converged,
            "fitter_converged": bool(fitter.converged),
            "reference_weighted_rms_us": reference_rms_us,
            "postfit_weighted_rms_us": postfit_rms_us,
            "weighted_rms_relative_difference": rms_relative_difference,
            "reference_wideband_chi2": reference_chi2,
            "chi2_recorded_in_release_model": float(release_model.CHI2.value),
            "postfit_wideband_chi2": postfit_chi2,
            "chi2_change": postfit_chi2 - reference_chi2,
            "postfit_reduced_chi2": float(postfit_residuals.reduced_chi2),
        },
        "whitened_residual_diagnostics": {
            "gate_use": "descriptive_not_acceptance_criterion",
            "combined": _normality_diagnostics(whitened),
            "toa": _normality_diagnostics(whitened_toa),
            "dm": _normality_diagnostics(whitened_dm),
        },
        "parameter_comparison": {
            "sigma_multiplier": config.parameter_sigma_tolerance,
            "numerical_tolerance_ulps": config.numerical_tolerance_ulps,
            "parameters_checked": len(comparisons),
            "failure_count": len(parameter_failures),
            "failures": parameter_failures,
            "worst_absolute_delta_sigma": worst_delta_sigma,
            "median_absolute_uncertainty_relative_change": float(
                np.median([value for value, _ in uncertainty_changes])
            ),
            "maximum_absolute_uncertainty_relative_change": worst_uncertainty_change,
            "maximum_uncertainty_change_parameter": worst_uncertainty_parameter,
            "parameters": comparisons,
        },
        "warnings": warnings,
        "resources": {
            "fit_wall_seconds": fit_wall_seconds,
            "total_wall_seconds": total_wall_seconds,
            "cpu_seconds": time.process_time() - cpu_start,
            "peak_rss_mib": peak_rss_mib,
        },
        "criteria": criteria,
        "outputs": {
            "postfit_model": logical_path(postfit_path, data_root),
            "log": logical_path(log_path, data_root),
            "full_record": logical_path(record_path, data_root),
        },
        "injection_authorized": False,
        "review_required_before_injection": True,
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
