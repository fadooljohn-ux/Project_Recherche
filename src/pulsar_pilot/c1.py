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

from .c0 import build_frequency_grid, fit_weighted_sinusoid
from .config import PilotConfig
from .g2 import classify_warning_lines, validate_free_parameters
from .paths import repository_root
from .provenance import hash_file, logical_path


def generate_circular_delay_us(
    tdb_mjd: np.ndarray,
    period_days: float,
    amplitude_us: float,
    phase_radians: float,
    reference_epoch_mjd: float,
) -> np.ndarray:
    phase = (
        2
        * np.longdouble(np.pi)
        * (tdb_mjd.astype(np.longdouble) - np.longdouble(reference_epoch_mjd))
        / np.longdouble(period_days)
        + np.longdouble(phase_radians)
    )
    return np.asarray(np.longdouble(amplitude_us) * np.sin(phase), dtype=np.longdouble)


def complex_amplitude_difference(
    sine_value: float,
    cosine_value: float,
    null_sine_value: float,
    null_cosine_value: float,
) -> dict[str, float]:
    sine_difference = sine_value - null_sine_value
    cosine_difference = cosine_value - null_cosine_value
    return {
        "sine_difference": sine_difference,
        "cosine_difference": cosine_difference,
        "amplitude": float(np.hypot(sine_difference, cosine_difference)),
        "phase_radians": float(np.arctan2(cosine_difference, sine_difference)),
    }


def validate_c1_configuration(injections: dict[str, Any]) -> dict[str, Any]:
    cases = {str(case["id"]): case for case in injections.get("cases", [])}
    c1 = cases.get("C1")
    stage_c = injections.get("stage_c", {})
    c1_config = stage_c.get("c1", {})
    problems: list[str] = []
    if stage_c.get("authorization") != "c1_only":
        problems.append("Stage C authorization is not limited to C1")
    if c1 is None:
        problems.append("C1 is missing")
    else:
        if float(c1.get("period_days", -1)) != 100.0:
            problems.append("C1 period is not 100 days")
        if float(c1.get("amplitude_microseconds", -1)) != 20.0:
            problems.append("C1 amplitude is not 20 microseconds")
        if c1.get("hard_recovery_gate") is not True:
            problems.append("C1 is not marked as the hard recovery gate")
    if float(c1_config.get("reference_epoch_mjd_tdb", -1)) != 56078.0:
        problems.append("C1 reference epoch is not frozen to MJD 56078 TDB")
    if c1_config.get("joint_component") != "PINT_WaveX":
        problems.append("C1 joint grader is not PINT WaveX")
    if injections.get("trigger", {}).get("false_alarm_probability") != "prohibited":
        problems.append("False-alarm probability prohibition is missing")
    return {"status": "pass" if not problems else "fail", "problems": problems}


def _peak_rss_mib() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**2 if platform.system() == "Darwin" else 1024
    return peak / divisor


def _add_wavex(model: Any, frequency_per_day: float, epoch_mjd_tdb: float) -> Any:
    from pint.models.wavex import WaveX

    joint_model = copy.deepcopy(model)
    wavex = WaveX()
    wavex.WXEPOCH.value = epoch_mjd_tdb
    wavex.WXEPOCH.frozen = True
    wavex.WXFREQ_0001.value = frequency_per_day
    wavex.WXFREQ_0001.frozen = True
    wavex.WXSIN_0001.value = 0.0
    wavex.WXCOS_0001.value = 0.0
    wavex.WXSIN_0001.frozen = False
    wavex.WXCOS_0001.frozen = False
    joint_model.add_component(wavex, validate=True)
    return joint_model


def _joint_fit(
    toas: Any,
    release_model: Any,
    frequency_per_day: float,
    epoch_mjd_tdb: float,
    max_iterations: int,
) -> dict[str, Any]:
    import astropy.units as u
    from pint.fitter import WidebandDownhillFitter
    from pint.residuals import WidebandTOAResiduals

    joint_model = _add_wavex(release_model, frequency_per_day, epoch_mjd_tdb)
    fitter = WidebandDownhillFitter(toas, joint_model)
    returned_converged = bool(fitter.fit_toas(maxiter=max_iterations))
    residuals = WidebandTOAResiduals(toas, fitter.model)
    sine_us = float(fitter.model.WXSIN_0001.quantity.to_value(u.us))
    cosine_us = float(fitter.model.WXCOS_0001.quantity.to_value(u.us))
    return {
        "fitter": fitter,
        "model": fitter.model,
        "residuals": residuals,
        "returned_converged": returned_converged,
        "fitter_converged": bool(fitter.converged),
        "sine_us": sine_us,
        "cosine_us": cosine_us,
        "amplitude_us": float(np.hypot(sine_us, cosine_us)),
        "phase_radians": float(np.arctan2(cosine_us, sine_us)),
        "sine_uncertainty_us": float(fitter.model.WXSIN_0001.uncertainty.to_value(u.us)),
        "cosine_uncertainty_us": float(fitter.model.WXCOS_0001.uncertainty.to_value(u.us)),
        "chi2": float(residuals.chi2),
        "reduced_chi2": float(residuals.reduced_chi2),
        "weighted_rms_us": float(residuals.toa.rms_weighted().to_value(u.us)),
        "free_parameter_count": len(fitter.model.free_params),
    }


def _load_c0_record(injections: dict[str, Any], data_root: Path) -> dict[str, Any]:
    summary_path = repository_root() / injections["stage_c"]["c1"]["matched_null_source"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    external = summary["external_outputs"]["full_record"]
    record_path = data_root / external["logical_path"]
    actual_hash = hash_file(record_path, "sha256")
    if actual_hash != external["sha256"]:
        raise RuntimeError("Authoritative C0 record hash does not match its tracked summary")
    return json.loads(record_path.read_text(encoding="utf-8"))


def run_c1(config: PilotConfig, injections: dict[str, Any], data_root: Path) -> dict[str, Any]:
    c1_configuration = validate_c1_configuration(injections)
    if c1_configuration["status"] != "pass":
        raise RuntimeError(f"Frozen C1 configuration is invalid: {c1_configuration}")

    c1_case = next(case for case in injections["cases"] if case["id"] == "C1")
    stage_c = injections["stage_c"]
    c1_config = stage_c["c1"]
    trigger_config = injections["trigger"]
    period_days = float(c1_case["period_days"])
    injected_frequency = 1.0 / period_days
    requested_amplitude_us = float(c1_case["amplitude_microseconds"])
    phase_radians = float(injections["phase_radians"])
    epoch_mjd_tdb = float(c1_config["reference_epoch_mjd_tdb"])

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
    derived_dir = data_root / "derived" / "g3" / "c1"
    cache_root = data_root / "derived" / "cache"
    for directory in (run_dir, derived_dir, cache_root):
        directory.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"c1_positive_control_{run_id}.log"
    record_path = run_dir / f"c1_positive_control_{run_id}.json"
    periodogram_path = derived_dir / f"J1744-1134_C1_{run_id}.periodogram.npz"
    unmodeled_path = derived_dir / f"J1744-1134_C1_{run_id}.unmodeled.postfit.par"
    joint_path = derived_dir / f"J1744-1134_C1_{run_id}.joint-wavex.postfit.par"
    c0_joint_path = derived_dir / f"J1744-1134_C0_{run_id}.joint-wavex.postfit.par"

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

    c0_record = _load_c0_record(injections, data_root)
    c0_probe = next(
        probe
        for probe in c0_record["trigger"]["frozen_case_frequency_probes"]
        if float(probe["period_days"]) == period_days
    )
    c0_sinusoid = c0_probe["weighted_linear_sinusoid"]

    pre_injection_tdb_mjd = np.asarray(release_toas.table["tdbld"], dtype=np.longdouble)
    requested_delays_us = generate_circular_delay_us(
        pre_injection_tdb_mjd,
        period_days,
        requested_amplitude_us,
        phase_radians,
        epoch_mjd_tdb,
    )
    achieved_waveform = fit_weighted_sinusoid(
        np.asarray(pre_injection_tdb_mjd - np.longdouble(epoch_mjd_tdb), dtype=float),
        np.asarray(requested_delays_us, dtype=float),
        np.ones(len(requested_delays_us)),
        injected_frequency,
    )

    c1_toas = copy.deepcopy(release_toas)
    original_mjds = release_toas.get_mjds(high_precision=True).copy()
    c1_toas.adjust_TOAs(requested_delays_us * u.us)
    adjusted_mjds = c1_toas.get_mjds(high_precision=True).copy()
    actual_delays_us = np.array(
        [
            (adjusted - original).to_value(u.us)
            for adjusted, original in zip(adjusted_mjds, original_mjds)
        ]
    )
    maximum_application_error_us = float(
        np.max(np.abs(actual_delays_us - np.asarray(requested_delays_us, dtype=float)))
    )

    c0_base_residuals = WidebandTOAResiduals(release_toas, release_model)
    c0_base_chi2 = float(c0_base_residuals.chi2)
    c0_joint_start = time.perf_counter()
    c0_joint = _joint_fit(
        release_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        config.max_fit_iterations,
    )
    c0_joint_wall_seconds = time.perf_counter() - c0_joint_start
    c0_joint_improvement = c0_base_chi2 - float(c0_joint["chi2"])

    unmodeled_start = time.perf_counter()
    unmodeled_fitter = WidebandDownhillFitter(c1_toas, copy.deepcopy(release_model))
    unmodeled_returned_converged = bool(
        unmodeled_fitter.fit_toas(maxiter=config.max_fit_iterations)
    )
    unmodeled_wall_seconds = time.perf_counter() - unmodeled_start
    unmodeled_residuals = WidebandTOAResiduals(c1_toas, unmodeled_fitter.model)
    unmodeled_chi2 = float(unmodeled_residuals.chi2)

    toa_residuals_us = unmodeled_residuals.toa.calc_time_resids().to_value(u.us).astype(float)
    toa_uncertainties_us = unmodeled_fitter.model.scaled_toa_uncertainty(c1_toas).to_value(u.us)
    mjds = np.asarray(c1_toas.get_mjds().value, dtype=float)
    relative_days = mjds - mjds.min()
    span_days = float(mjds.max() - mjds.min())
    frequencies, grid = build_frequency_grid(
        span_days,
        float(trigger_config["minimum_period_days"]),
        float(trigger_config["maximum_period_span_fraction"]),
        int(trigger_config["frequency_oversampling"]),
    )
    periodogram = LombScargle(
        relative_days,
        toa_residuals_us,
        dy=toa_uncertainties_us,
        fit_mean=bool(trigger_config["fit_mean"]),
        center_data=bool(trigger_config["center_data"]),
        nterms=1,
    )
    powers = periodogram.power(frequencies, normalization=str(trigger_config["normalization"]))
    peak_index = int(np.nanargmax(powers))
    peak_frequency = float(frequencies[peak_index])
    peak_period = 1.0 / peak_frequency
    peak_bin_offset = (peak_frequency - injected_frequency) / float(
        grid["independent_fourier_bin_per_day"]
    )
    peak_sinusoid = fit_weighted_sinusoid(
        relative_days, toa_residuals_us, toa_uncertainties_us, peak_frequency
    )
    exact_sinusoid = fit_weighted_sinusoid(
        relative_days, toa_residuals_us, toa_uncertainties_us, injected_frequency
    )
    exact_power = float(
        periodogram.power(injected_frequency, normalization=str(trigger_config["normalization"]))
    )
    blind_matched_null = complex_amplitude_difference(
        exact_sinusoid["sine_coefficient"],
        exact_sinusoid["cosine_coefficient"],
        float(c0_sinusoid["sine_coefficient"]),
        float(c0_sinusoid["cosine_coefficient"]),
    )

    joint_start = time.perf_counter()
    c1_joint = _joint_fit(
        c1_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        config.max_fit_iterations,
    )
    joint_wall_seconds = time.perf_counter() - joint_start
    c1_joint_improvement = unmodeled_chi2 - float(c1_joint["chi2"])
    joint_matched_null = complex_amplitude_difference(
        float(c1_joint["sine_us"]),
        float(c1_joint["cosine_us"]),
        float(c0_joint["sine_us"]),
        float(c0_joint["cosine_us"]),
    )

    np.savez_compressed(
        periodogram_path,
        frequency_per_day=frequencies,
        period_days=1.0 / frequencies,
        power=powers,
    )
    unmodeled_path.write_text(
        unmodeled_fitter.model.as_parfile(comment="Project Recherche C1 unmodeled refit"),
        encoding="utf-8",
    )
    joint_path.write_text(
        c1_joint["model"].as_parfile(comment="Project Recherche C1 joint WaveX refit"),
        encoding="utf-8",
    )
    c0_joint_path.write_text(
        c0_joint["model"].as_parfile(comment="Project Recherche same-run C0 joint WaveX refit"),
        encoding="utf-8",
    )
    for path in (unmodeled_path, joint_path, c0_joint_path):
        path.chmod(0o444)

    sanitized_lines = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    warnings = classify_warning_lines(sanitized_lines)
    total_wall_seconds = time.perf_counter() - wall_start
    peak_rss_mib = _peak_rss_mib()
    criteria = {
        "configuration_frozen_and_c1_only": c1_configuration["status"] == "pass",
        "injection_application_within_tolerance": maximum_application_error_us
        <= float(c1_config["maximum_application_error_microseconds"]),
        "toa_count_unchanged": len(c1_toas) == len(release_toas) == 433,
        "unmodeled_refit_converged": unmodeled_returned_converged
        and bool(unmodeled_fitter.converged),
        "blind_peak_within_one_fourier_bin": abs(peak_bin_offset)
        <= float(c1_config["blind_peak_maximum_fourier_bin_offset"]),
        "exact_frequency_power_exceeds_c0": exact_power > float(c0_probe["power_at_exact_frequency"]),
        "exact_frequency_amplitude_exceeds_c0": exact_sinusoid["amplitude"]
        > float(c0_probe["recovered_amplitude_us"]),
        "c0_joint_fit_converged": bool(c0_joint["returned_converged"])
        and bool(c0_joint["fitter_converged"]),
        "c1_joint_fit_converged": bool(c1_joint["returned_converged"])
        and bool(c1_joint["fitter_converged"]),
        "joint_amplitude_exceeds_c0": float(c1_joint["amplitude_us"])
        > float(c0_joint["amplitude_us"]),
        "joint_chi2_improvement_exceeds_c0": c1_joint_improvement > c0_joint_improvement,
        "periodogram_finite": bool(np.all(np.isfinite(powers))),
        "material_warnings_dispositioned": warnings["status"] == "pass",
        "runtime_under_60_minutes": total_wall_seconds <= 3600,
        "peak_memory_under_16_gib": peak_rss_mib <= 16 * 1024,
    }
    status = "pass" if all(criteria.values()) else "fail"

    injection_phase_error = float(
        np.arctan2(
            np.sin(joint_matched_null["phase_radians"] - phase_radians),
            np.cos(joint_matched_null["phase_radians"] - phase_radians),
        )
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "recorded_utc": recorded.isoformat(),
        "run_id": run_id,
        "case": "C1",
        "case_purpose": "strong_positive_control",
        "status": status,
        "dataset": "nanograv15yr-v2.1.0",
        "target": "J1744-1134",
        "software": {
            "python": platform.python_version(),
            "pint_pulsar": pint.__version__,
            "numpy": np.__version__,
            "process_machine": platform.machine(),
            "longdouble_mantissa_bits": int(np.finfo(np.longdouble).nmant),
            "pixi_lock_sha256": hash_file(repository_root() / "pixi.lock", "sha256"),
        },
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
        "injection": {
            "period_days": period_days,
            "frequency_per_day": injected_frequency,
            "requested_amplitude_us": requested_amplitude_us,
            "phase_radians": phase_radians,
            "reference_epoch_mjd_tdb": epoch_mjd_tdb,
            "phase_time_coordinate": c1_config["phase_time_coordinate"],
            "toa_shift_sign": c1_config["toa_shift_sign"],
            "achieved_fitted_amplitude_us": achieved_waveform["amplitude"],
            "sampled_maximum_absolute_delay_us": float(np.max(np.abs(requested_delays_us))),
            "sampled_half_peak_to_peak_us": float(
                (np.max(requested_delays_us) - np.min(requested_delays_us)) / 2
            ),
            "maximum_application_error_us": maximum_application_error_us,
            "application_tolerance_us": float(
                c1_config["maximum_application_error_microseconds"]
            ),
        },
        "blind_unmodeled_refit": {
            "returned_converged": unmodeled_returned_converged,
            "fitter_converged": bool(unmodeled_fitter.converged),
            "weighted_rms_us": float(unmodeled_residuals.toa.rms_weighted().to_value(u.us)),
            "wideband_chi2": unmodeled_chi2,
            "reduced_chi2": float(unmodeled_residuals.reduced_chi2),
        },
        "blind_trigger": {
            "grid": grid,
            "peak_frequency_per_day": peak_frequency,
            "peak_period_days": peak_period,
            "peak_power": float(powers[peak_index]),
            "peak_fourier_bin_offset": peak_bin_offset,
            "peak_sinusoid": peak_sinusoid,
            "exact_injected_frequency_power": exact_power,
            "exact_injected_frequency_sinusoid": exact_sinusoid,
            "c0_exact_frequency_probe": c0_probe,
            "matched_null_subtracted": blind_matched_null,
            "false_alarm_probability": None,
            "correlated_noise_in_periodogram": "not_modeled",
        },
        "joint_wavex": {
            "frequency_per_day": injected_frequency,
            "epoch_mjd_tdb": epoch_mjd_tdb,
            "c0": {key: value for key, value in c0_joint.items() if key not in {"fitter", "model", "residuals"}},
            "c1": {key: value for key, value in c1_joint.items() if key not in {"fitter", "model", "residuals"}},
            "matched_null_subtracted": joint_matched_null,
            "matched_null_phase_error_radians": injection_phase_error,
            "c0_chi2_improvement": c0_joint_improvement,
            "c1_chi2_improvement": c1_joint_improvement,
        },
        "transfer": {
            "blind_residual_recovery_fraction": blind_matched_null["amplitude"]
            / achieved_waveform["amplitude"],
            "standard_timing_model_absorption_fraction": 1
            - blind_matched_null["amplitude"] / achieved_waveform["amplitude"],
            "joint_matched_null_recovery_fraction": joint_matched_null["amplitude"]
            / achieved_waveform["amplitude"],
        },
        "warnings": warnings,
        "resources": {
            "c0_joint_wall_seconds": c0_joint_wall_seconds,
            "c1_unmodeled_wall_seconds": unmodeled_wall_seconds,
            "c1_joint_wall_seconds": joint_wall_seconds,
            "total_wall_seconds": total_wall_seconds,
            "cpu_seconds": time.process_time() - cpu_start,
            "peak_rss_mib": peak_rss_mib,
        },
        "criteria": criteria,
        "outputs": {
            "periodogram": {
                "logical_path": logical_path(periodogram_path, data_root),
                "sha256": hash_file(periodogram_path, "sha256"),
            },
            "c1_unmodeled_model": {
                "logical_path": logical_path(unmodeled_path, data_root),
                "sha256": hash_file(unmodeled_path, "sha256"),
            },
            "c1_joint_model": {
                "logical_path": logical_path(joint_path, data_root),
                "sha256": hash_file(joint_path, "sha256"),
            },
            "c0_joint_model": {
                "logical_path": logical_path(c0_joint_path, data_root),
                "sha256": hash_file(c0_joint_path, "sha256"),
            },
            "log": {
                "logical_path": logical_path(log_path, data_root),
                "sha256": hash_file(log_path, "sha256"),
            },
            "full_record": logical_path(record_path, data_root),
        },
        "claim_boundary": "C1 is a positive-control recovery, not a detection",
        "authorized_next_cases": [],
        "blocked_cases": ["C2", "C3"],
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
