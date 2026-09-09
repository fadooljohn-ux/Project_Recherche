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
from .g2 import classify_warning_lines, validate_free_parameters
from .paths import repository_root
from .provenance import hash_file, logical_path


def build_frequency_grid(
    span_days: float,
    minimum_period_days: float,
    maximum_period_span_fraction: float,
    oversampling: int,
) -> tuple[np.ndarray, dict[str, float | int]]:
    maximum_period_days = span_days * maximum_period_span_fraction
    minimum_frequency = 1.0 / maximum_period_days
    maximum_frequency = 1.0 / minimum_period_days
    independent_bin = 1.0 / span_days
    step = independent_bin / oversampling
    frequencies = np.arange(minimum_frequency, maximum_frequency + step / 2, step)
    return frequencies, {
        "span_days": span_days,
        "minimum_period_days": minimum_period_days,
        "maximum_period_days": maximum_period_days,
        "minimum_frequency_per_day": minimum_frequency,
        "maximum_frequency_per_day": maximum_frequency,
        "independent_fourier_bin_per_day": independent_bin,
        "frequency_step_per_day": step,
        "oversampling": oversampling,
        "frequency_count": len(frequencies),
    }


def fit_weighted_sinusoid(
    times_days: np.ndarray,
    residuals: np.ndarray,
    uncertainties: np.ndarray,
    frequency_per_day: float,
) -> dict[str, float]:
    omega_t = 2 * np.pi * frequency_per_day * times_days
    design = np.column_stack((np.ones(len(times_days)), np.sin(omega_t), np.cos(omega_t)))
    sqrt_weight = 1.0 / uncertainties
    weighted_design = design * sqrt_weight[:, None]
    weighted_residuals = residuals * sqrt_weight
    coefficients, _, _, singular_values = np.linalg.lstsq(
        weighted_design, weighted_residuals, rcond=None
    )
    fitted = design @ coefficients
    weighted_mean = np.average(residuals, weights=1.0 / uncertainties**2)
    chi2_constant = float(np.sum(((residuals - weighted_mean) / uncertainties) ** 2))
    chi2_sinusoid = float(np.sum(((residuals - fitted) / uncertainties) ** 2))
    sine_coefficient = float(coefficients[1])
    cosine_coefficient = float(coefficients[2])
    return {
        "offset": float(coefficients[0]),
        "sine_coefficient": sine_coefficient,
        "cosine_coefficient": cosine_coefficient,
        "amplitude": float(np.hypot(sine_coefficient, cosine_coefficient)),
        "phase_radians": float(np.arctan2(cosine_coefficient, sine_coefficient)),
        "chi2_constant": chi2_constant,
        "chi2_sinusoid": chi2_sinusoid,
        "delta_chi2": chi2_constant - chi2_sinusoid,
        "design_condition_number": float(singular_values[0] / singular_values[-1]),
    }


def validate_c0_configuration(injections: dict[str, Any]) -> dict[str, Any]:
    cases = {str(case["id"]): case for case in injections.get("cases", [])}
    c0 = cases.get("C0")
    problems: list[str] = []
    if injections.get("stage_c", {}).get("authorization") != "c0_only":
        problems.append("Stage C authorization is not limited to C0")
    if c0 is None:
        problems.append("C0 is missing")
    elif c0.get("period_days") is not None or float(c0.get("amplitude_microseconds", -1)) != 0:
        problems.append("C0 is not the frozen zero-amplitude, no-period case")
    if injections.get("trigger", {}).get("false_alarm_probability") != "prohibited":
        problems.append("False-alarm probability prohibition is missing")
    return {"status": "pass" if not problems else "fail", "problems": problems}


def _peak_rss_mib() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**2 if platform.system() == "Darwin" else 1024
    return peak / divisor


def run_c0(config: PilotConfig, injections: dict[str, Any], data_root: Path) -> dict[str, Any]:
    c0_configuration = validate_c0_configuration(injections)
    if c0_configuration["status"] != "pass":
        raise RuntimeError(f"Frozen C0 configuration is invalid: {c0_configuration}")

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
    derived_dir = data_root / "derived" / "g3" / "c0"
    cache_root = data_root / "derived" / "cache"
    for directory in (run_dir, derived_dir, cache_root):
        directory.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"c0_matched_null_{run_id}.log"
    record_path = run_dir / f"c0_matched_null_{run_id}.json"
    postfit_path = derived_dir / f"J1744-1134_C0_{run_id}.postfit.par"
    periodogram_path = derived_dir / f"J1744-1134_C0_{run_id}.periodogram.npz"

    os.environ["PINT_CLOCK_OVERRIDE"] = str(clock_dir)
    os.environ["XDG_CACHE_HOME"] = str(cache_root)

    import astropy.units as u
    import pint
    import pint.logging
    from astropy.timeseries import LombScargle
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
    release_model, release_toas = get_model_and_toas(
        par_path,
        tim_path,
        ephem="DE440",
        include_bipm=True,
        bipm_version="BIPM2019",
        planets=True,
        usepickle=False,
        limits="warn",
    )
    free_parameters = validate_free_parameters(release_model.free_params, config.free_base_parameters)
    if free_parameters["status"] != "pass":
        raise RuntimeError(f"Released free-parameter set violates the frozen model: {free_parameters}")

    c0_toas = copy.deepcopy(release_toas)
    original_mjds_high_precision = release_toas.get_mjds(high_precision=True).copy()
    original_mjds_float = release_toas.get_mjds().copy()
    c0_toas.adjust_TOAs(np.zeros(len(c0_toas)) * u.us)
    adjusted_mjds_high_precision = c0_toas.get_mjds(high_precision=True).copy()
    adjusted_mjds_float = c0_toas.get_mjds().copy()
    achieved_delays_us = np.array(
        [
            (adjusted - original).to_value(u.us)
            for adjusted, original in zip(
                adjusted_mjds_high_precision, original_mjds_high_precision
            )
        ]
    )
    mjd_float_refresh_difference_us = (
        adjusted_mjds_float - original_mjds_float
    ).to_value(u.us)

    fit_start = time.perf_counter()
    fitter = WidebandDownhillFitter(c0_toas, copy.deepcopy(release_model))
    fit_returned_converged = bool(fitter.fit_toas(maxiter=config.max_fit_iterations))
    fit_wall_seconds = time.perf_counter() - fit_start
    postfit_model = fitter.model
    postfit_residuals = WidebandTOAResiduals(c0_toas, postfit_model)
    toa_residuals_us = postfit_residuals.toa.calc_time_resids().to_value(u.us).astype(float)
    toa_uncertainties_us = postfit_model.scaled_toa_uncertainty(c0_toas).to_value(u.us)
    mjds = np.asarray(c0_toas.get_mjds().value, dtype=float)
    relative_days = mjds - mjds.min()
    span_days = float(mjds.max() - mjds.min())

    trigger = injections["trigger"]
    frequencies, grid = build_frequency_grid(
        span_days,
        float(trigger["minimum_period_days"]),
        float(trigger["maximum_period_span_fraction"]),
        int(trigger["frequency_oversampling"]),
    )
    periodogram = LombScargle(
        relative_days,
        toa_residuals_us,
        dy=toa_uncertainties_us,
        fit_mean=bool(trigger["fit_mean"]),
        center_data=bool(trigger["center_data"]),
        nterms=1,
    )
    powers = periodogram.power(frequencies, normalization=str(trigger["normalization"]))
    peak_index = int(np.nanargmax(powers))
    peak_frequency = float(frequencies[peak_index])
    peak_period = 1.0 / peak_frequency
    sinusoid = fit_weighted_sinusoid(
        relative_days, toa_residuals_us, toa_uncertainties_us, peak_frequency
    )
    probe_cases: dict[float, list[str]] = {}
    for case in injections["cases"]:
        if case["period_days"] is not None:
            probe_cases.setdefault(float(case["period_days"]), []).append(str(case["id"]))
    frozen_case_frequency_probes: list[dict[str, Any]] = []
    for period_days, case_ids in sorted(probe_cases.items()):
        frequency_per_day = 1.0 / period_days
        probe_sinusoid = fit_weighted_sinusoid(
            relative_days, toa_residuals_us, toa_uncertainties_us, frequency_per_day
        )
        nearest_index = int(np.argmin(np.abs(frequencies - frequency_per_day)))
        frozen_case_frequency_probes.append(
            {
                "case_ids": case_ids,
                "period_days": period_days,
                "frequency_per_day": frequency_per_day,
                "power_at_exact_frequency": float(
                    periodogram.power(frequency_per_day, normalization=str(trigger["normalization"]))
                ),
                "recovered_amplitude_us": probe_sinusoid["amplitude"],
                "weighted_linear_sinusoid": probe_sinusoid,
                "nearest_grid_frequency_per_day": float(frequencies[nearest_index]),
                "nearest_grid_bin_offset_in_independent_bins": float(
                    (frequencies[nearest_index] - frequency_per_day)
                    / float(grid["independent_fourier_bin_per_day"])
                ),
            }
        )

    np.savez_compressed(
        periodogram_path,
        frequency_per_day=frequencies,
        period_days=1.0 / frequencies,
        power=powers,
    )
    postfit_path.write_text(
        postfit_model.as_parfile(comment="Project Recherche C0 matched-null refit"),
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
        "configuration_frozen_and_c0_only": c0_configuration["status"] == "pass",
        "zero_delay_applied_exactly": bool(np.max(np.abs(achieved_delays_us)) == 0),
        "toa_count_unchanged": len(c0_toas) == len(release_toas) == 433,
        "fit_converged": fit_returned_converged and bool(fitter.converged),
        "periodogram_finite": bool(np.all(np.isfinite(powers))),
        "material_warnings_dispositioned": warnings["status"] == "pass",
        "runtime_under_60_minutes": total_wall_seconds <= 3600,
        "peak_memory_under_16_gib": peak_rss_mib <= 16 * 1024,
    }
    status = "pass" if all(criteria.values()) else "fail"

    record: dict[str, Any] = {
        "schema_version": 1,
        "recorded_utc": recorded.isoformat(),
        "run_id": run_id,
        "case": "C0",
        "case_purpose": "matched_null_pipeline_control",
        "status": status,
        "dataset": "nanograv15yr-v2.1.0",
        "target": "J1744-1134",
        "inputs": {
            "par": logical_path(par_path, data_root),
            "tim": logical_path(tim_path, data_root),
            "clock_override": logical_path(clock_dir, data_root),
            "ephemeris": "DE440",
            "timescale": "TT(BIPM2019)",
            "fitter": "WidebandDownhillFitter",
            "max_iterations": config.max_fit_iterations,
            "noise_model": "fixed_release_values",
        },
        "software": {
            "python": platform.python_version(),
            "pint_pulsar": pint.__version__,
            "numpy": np.__version__,
            "process_machine": platform.machine(),
            "longdouble_mantissa_bits": int(np.finfo(np.longdouble).nmant),
            "pixi_lock_sha256": hash_file(repository_root() / "pixi.lock", "sha256"),
        },
        "injection": {
            "requested_period_days": None,
            "requested_amplitude_us": 0.0,
            "achieved_amplitude_us": float(np.max(np.abs(achieved_delays_us))),
            "maximum_absolute_toa_shift_us": float(np.max(np.abs(achieved_delays_us))),
            "comparison_basis": "high_precision_astropy_time",
            "mjd_float_cache_refresh_max_difference_us": float(
                np.max(np.abs(mjd_float_refresh_difference_us))
            ),
            "mjd_float_cache_refresh_nonzero_rows": int(
                np.count_nonzero(mjd_float_refresh_difference_us)
            ),
            "mjd_float_cache_disposition": (
                "PINT adjust_TOAs recomputed the auxiliary float64 cache from unchanged "
                "high-precision Time values"
            ),
            "toa_adjustment_path_exercised": True,
        },
        "refit": {
            "returned_converged": fit_returned_converged,
            "fitter_converged": bool(fitter.converged),
            "ntoas": len(c0_toas),
            "weighted_rms_us": float(postfit_residuals.toa.rms_weighted().to_value(u.us)),
            "wideband_chi2": float(postfit_residuals.chi2),
            "reduced_chi2": float(postfit_residuals.reduced_chi2),
        },
        "trigger": {
            "role": "diagnostic_artifact_not_detection",
            "method": trigger["method"],
            "normalization": trigger["normalization"],
            "weights": trigger["weights"],
            "correlated_noise_in_periodogram": "not_modeled",
            "grid": grid,
            "peak_frequency_per_day": peak_frequency,
            "peak_period_days": peak_period,
            "peak_power": float(powers[peak_index]),
            "peak_fourier_index": peak_frequency * span_days,
            "recovered_amplitude_us": sinusoid["amplitude"],
            "weighted_linear_sinusoid": sinusoid,
            "frozen_case_frequency_probes": frozen_case_frequency_probes,
            "injected_frequency_bin_offset": None,
            "false_alarm_probability": None,
        },
        "transfer": {
            "absorption_fraction": None,
            "disposition": "not_defined_for_zero_amplitude_matched_null",
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
            "postfit_model": {
                "logical_path": logical_path(postfit_path, data_root),
                "sha256": hash_file(postfit_path, "sha256"),
            },
            "periodogram": {
                "logical_path": logical_path(periodogram_path, data_root),
                "sha256": hash_file(periodogram_path, "sha256"),
            },
            "log": {
                "logical_path": logical_path(log_path, data_root),
                "sha256": hash_file(log_path, "sha256"),
            },
            "full_record": logical_path(record_path, data_root),
        },
        "claim_boundary": "C0 peak is an uncalibrated diagnostic artifact",
        "authorized_next_cases": [],
        "blocked_cases": ["C1", "C2", "C3"],
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
