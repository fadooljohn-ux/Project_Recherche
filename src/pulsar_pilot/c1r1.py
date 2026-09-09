from __future__ import annotations

import copy
import json
import os
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .c0 import build_frequency_grid, fit_weighted_sinusoid
from .c1 import complex_amplitude_difference, generate_circular_delay_us
from .circular_signal import ProjectCircularSignal
from .config import PilotConfig
from .g2 import classify_warning_lines, validate_free_parameters
from .paths import repository_root
from .provenance import hash_file, logical_path


def wrapped_phase_difference(value: float, reference: float) -> float:
    return float(np.arctan2(np.sin(value - reference), np.cos(value - reference)))


def validate_c1r1_configuration(injections: dict[str, Any]) -> dict[str, Any]:
    cases = {str(case["id"]): case for case in injections.get("cases", [])}
    c1 = cases.get("C1")
    stage_c = injections.get("stage_c", {})
    method = stage_c.get("c1_r1", {})
    problems: list[str] = []
    if stage_c.get("authorization") != "c1_r1_only":
        problems.append("Stage C authorization is not limited to C1-R1")
    if c1 is None or float(c1.get("period_days", -1)) != 100.0:
        problems.append("The unchanged C1 100-day case is missing")
    if c1 is None or float(c1.get("amplitude_microseconds", -1)) != 20.0:
        problems.append("The unchanged C1 20-microsecond amplitude is missing")
    if method.get("injection_waveform_unchanged") is not True:
        problems.append("C1-R1 does not preserve the C1 injection waveform")
    if method.get("joint_component") != "ProjectCircularSignal":
        problems.append("C1-R1 joint component is not ProjectCircularSignal")
    if method.get("independent_crosscheck") != (
        "WidebandTOAFitter_explicit_full_covariance"
    ):
        problems.append("C1-R1 full-covariance cross-check is not frozen")
    if method.get("blind_global_peak_role") != "diagnostic_not_acceptance_gate":
        problems.append("The global blind peak is not limited to a diagnostic role")
    if injections.get("trigger", {}).get("false_alarm_probability") != "prohibited":
        problems.append("False-alarm probability prohibition is missing")
    return {"status": "pass" if not problems else "fail", "problems": problems}


def verify_c1r1_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / "protocol" / "FREEZE_RECORD_v0.5.json"
    authorization_path = root / "protocol" / "STAGE_C_AUTHORIZATION_v0.3.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_first_c1_r1_run":
        failures.append("C1-R1 freeze status is invalid")
    if freeze.get("authorized_cases") != ["C1-R1"]:
        failures.append("C1-R1 is not the only authorized case")
    for section in ("config_sha256", "implementation_sha256", "scorecard_sha256"):
        for relative, expected in freeze.get(section, {}).items():
            if hash_file(root / relative, "sha256") != expected:
                failures.append(f"Hash mismatch: {relative}")
    if hash_file(root / "pixi.lock", "sha256") != freeze.get("pixi_lock_sha256"):
        failures.append("Pixi lock hash mismatch")
    authorization_hash = hash_file(authorization_path, "sha256")
    if authorization_hash != freeze.get("stage_c_authorization_sha256"):
        failures.append("Stage C authorization hash mismatch")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_id": freeze.get("freeze_id"),
        "freeze_sha256": hash_file(freeze_path, "sha256"),
        "authorization_sha256": authorization_hash,
    }


def _peak_rss_mib() -> float:
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**2 if platform.system() == "Darwin" else 1024
    return peak / divisor


def _add_project_signal(model: Any, frequency_per_day: float, epoch_mjd_tdb: float) -> Any:
    joint_model = copy.deepcopy(model)
    signal = ProjectCircularSignal()
    signal.CSEPOCH.value = epoch_mjd_tdb
    signal.CSEPOCH.frozen = True
    signal.CSFREQ.value = frequency_per_day
    signal.CSFREQ.frozen = True
    signal.CSSIN.value = 0.0
    signal.CSCOS.value = 0.0
    signal.CSSIN.frozen = False
    signal.CSCOS.frozen = False
    joint_model.add_component(signal, validate=True)
    return joint_model


def _fit_measurements(fitter: Any, residuals: Any) -> dict[str, Any]:
    import astropy.units as u

    sine_us = float(fitter.model.CSSIN.quantity.to_value(u.us))
    cosine_us = float(fitter.model.CSCOS.quantity.to_value(u.us))
    return {
        "sine_us": sine_us,
        "cosine_us": cosine_us,
        "amplitude_us": float(np.hypot(sine_us, cosine_us)),
        "phase_radians": float(np.arctan2(cosine_us, sine_us)),
        "sine_uncertainty_us": float(fitter.model.CSSIN.uncertainty.to_value(u.us)),
        "cosine_uncertainty_us": float(fitter.model.CSCOS.uncertainty.to_value(u.us)),
        "chi2": float(residuals.chi2),
        "reduced_chi2": float(residuals.reduced_chi2),
        "weighted_rms_us": float(residuals.toa.rms_weighted().to_value(u.us)),
        "free_parameter_count": len(fitter.model.free_params),
        "release_red_noise_preserved": "PLRedNoise" in fitter.model.components,
        "wavex_absent": "WaveX" not in fitter.model.components,
    }


def _joint_downhill_fit(
    toas: Any,
    release_model: Any,
    frequency_per_day: float,
    epoch_mjd_tdb: float,
    max_iterations: int,
) -> dict[str, Any]:
    from pint.fitter import WidebandDownhillFitter
    from pint.residuals import WidebandTOAResiduals

    fitter = WidebandDownhillFitter(
        toas, _add_project_signal(release_model, frequency_per_day, epoch_mjd_tdb)
    )
    returned_converged = bool(fitter.fit_toas(maxiter=max_iterations))
    residuals = WidebandTOAResiduals(toas, fitter.model)
    return {
        "fitter": fitter,
        "model": fitter.model,
        "residuals": residuals,
        "solver": "WidebandDownhillFitter_low_rank_covariance",
        "returned_converged": returned_converged,
        "fitter_converged": bool(fitter.converged),
        **_fit_measurements(fitter, residuals),
    }


def _joint_full_covariance_fit(
    toas: Any,
    release_model: Any,
    frequency_per_day: float,
    epoch_mjd_tdb: float,
    max_iterations: int,
) -> dict[str, Any]:
    from pint.fitter import WidebandTOAFitter
    from pint.residuals import WidebandTOAResiduals

    fitter = WidebandTOAFitter(
        toas, _add_project_signal(release_model, frequency_per_day, epoch_mjd_tdb)
    )
    returned_chi2 = float(
        fitter.fit_toas(maxiter=max_iterations, threshold=1e-14, full_cov=True)
    )
    residuals = WidebandTOAResiduals(toas, fitter.model)
    return {
        "fitter": fitter,
        "model": fitter.model,
        "residuals": residuals,
        "solver": "WidebandTOAFitter_explicit_full_covariance",
        "completed": bool(np.isfinite(returned_chi2)),
        "returned_chi2": returned_chi2,
        **_fit_measurements(fitter, residuals),
    }


def _load_c0_record(method: dict[str, Any], data_root: Path) -> dict[str, Any]:
    summary_path = repository_root() / method["matched_null_source"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    external = summary["external_outputs"]["full_record"]
    record_path = data_root / external["logical_path"]
    if hash_file(record_path, "sha256") != external["sha256"]:
        raise RuntimeError("Authoritative C0 record hash does not match its tracked summary")
    return json.loads(record_path.read_text(encoding="utf-8"))


def _scorecard(criteria: dict[str, bool]) -> dict[str, Any]:
    groups = {
        "protocol_control": [
            "configuration_frozen_and_c1_r1_only",
            "release_red_noise_preserved_and_wavex_absent",
        ],
        "injection_integrity": [
            "injection_application_within_tolerance",
            "toa_count_unchanged",
        ],
        "ordinary_refit": ["unmodeled_refit_converged"],
        "frequency_recovery": [
            "exact_frequency_power_exceeds_c0",
            "exact_frequency_amplitude_exceeds_c0",
        ],
        "joint_recovery": [
            "c0_joint_fit_converged",
            "c1_joint_fit_converged",
            "joint_recovery_fraction_within_bounds",
            "joint_phase_error_within_bound",
            "joint_chi2_improvement_exceeds_c0",
        ],
        "independent_crosscheck": [
            "full_covariance_fit_completed",
            "solver_amplitudes_agree",
            "solver_phases_agree",
            "solver_chi2_values_agree",
        ],
        "warning_hygiene": ["material_warnings_dispositioned"],
        "reproducibility": ["periodogram_finite"],
        "resource_envelope": ["runtime_under_60_minutes", "peak_memory_under_16_gib"],
        "scientific_authorization": ["later_cases_remain_blocked"],
    }
    rows: dict[str, Any] = {}
    for name, tests in groups.items():
        passed = all(criteria[test] for test in tests)
        rows[name] = {
            "status": "PASS" if passed else "FAIL",
            "hard_gate": True,
            "tests": {test: criteria[test] for test in tests},
        }
    rows["global_strongest_peak"] = {
        "status": "DIAGNOSTIC",
        "hard_gate": False,
        "tests": {},
    }
    return {"overall": "PASS" if all(criteria.values()) else "FAIL", "rows": rows}


def run_c1_r1(config: PilotConfig, injections: dict[str, Any], data_root: Path) -> dict[str, Any]:
    configuration = validate_c1r1_configuration(injections)
    freeze = verify_c1r1_freeze()
    if configuration["status"] != "pass" or freeze["status"] != "pass":
        raise RuntimeError(
            f"Frozen C1-R1 controls are invalid: configuration={configuration}, freeze={freeze}"
        )

    c1_case = next(case for case in injections["cases"] if case["id"] == "C1")
    stage_c = injections["stage_c"]
    method = stage_c["c1_r1"]
    trigger_config = injections["trigger"]
    period_days = float(c1_case["period_days"])
    injected_frequency = 1.0 / period_days
    requested_amplitude_us = float(c1_case["amplitude_microseconds"])
    phase_radians = float(injections["phase_radians"])
    epoch_mjd_tdb = float(method["reference_epoch_mjd_tdb"])

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
    derived_dir = data_root / "derived" / "g3" / "c1_r1"
    cache_root = data_root / "derived" / "cache"
    for directory in (run_dir, derived_dir, cache_root):
        directory.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"c1_r1_corrective_control_{run_id}.log"
    record_path = run_dir / f"c1_r1_corrective_control_{run_id}.json"
    periodogram_path = derived_dir / f"J1744-1134_C1-R1_{run_id}.periodogram.npz"
    unmodeled_path = derived_dir / f"J1744-1134_C1-R1_{run_id}.unmodeled.postfit.par"
    joint_path = derived_dir / f"J1744-1134_C1-R1_{run_id}.joint-circular.postfit.par"
    c0_joint_path = derived_dir / f"J1744-1134_C0_{run_id}.joint-circular.postfit.par"
    full_cov_path = derived_dir / f"J1744-1134_C1-R1_{run_id}.full-cov.postfit.par"

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

    c0_record = _load_c0_record(method, data_root)
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

    c0_base_chi2 = float(WidebandTOAResiduals(release_toas, release_model).chi2)
    c0_joint_start = time.perf_counter()
    c0_joint = _joint_downhill_fit(
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
    c1_joint = _joint_downhill_fit(
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
    injection_phase_error = wrapped_phase_difference(
        joint_matched_null["phase_radians"], phase_radians
    )

    full_cov_start = time.perf_counter()
    full_cov = _joint_full_covariance_fit(
        c1_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        int(method["independent_crosscheck_max_iterations"]),
    )
    full_cov_wall_seconds = time.perf_counter() - full_cov_start
    solver_amplitude_difference_us = abs(
        float(c1_joint["amplitude_us"]) - float(full_cov["amplitude_us"])
    )
    solver_phase_difference_radians = abs(
        wrapped_phase_difference(
            float(c1_joint["phase_radians"]), float(full_cov["phase_radians"])
        )
    )
    solver_chi2_difference = abs(float(c1_joint["chi2"]) - float(full_cov["chi2"]))

    np.savez_compressed(
        periodogram_path,
        frequency_per_day=frequencies,
        period_days=1.0 / frequencies,
        power=powers,
    )
    model_outputs = [
        (unmodeled_path, unmodeled_fitter.model, "C1-R1 ordinary refit"),
        (joint_path, c1_joint["model"], "C1-R1 joint deterministic circular-signal refit"),
        (c0_joint_path, c0_joint["model"], "same-run C0 joint circular-signal refit"),
        (full_cov_path, full_cov["model"], "C1-R1 explicit full-covariance refit"),
    ]
    for path, model, comment in model_outputs:
        path.write_text(model.as_parfile(comment=f"Project Recherche {comment}"), encoding="utf-8")
        path.chmod(0o444)

    sanitized_lines = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    warnings = classify_warning_lines(sanitized_lines)
    total_wall_seconds = time.perf_counter() - wall_start
    peak_rss_mib = _peak_rss_mib()
    joint_recovery_fraction = joint_matched_null["amplitude"] / achieved_waveform["amplitude"]
    criteria = {
        "configuration_frozen_and_c1_r1_only": configuration["status"] == "pass"
        and freeze["status"] == "pass",
        "release_red_noise_preserved_and_wavex_absent": bool(
            c0_joint["release_red_noise_preserved"]
            and c0_joint["wavex_absent"]
            and c1_joint["release_red_noise_preserved"]
            and c1_joint["wavex_absent"]
            and full_cov["release_red_noise_preserved"]
            and full_cov["wavex_absent"]
        ),
        "injection_application_within_tolerance": maximum_application_error_us
        <= float(method["maximum_application_error_microseconds"]),
        "toa_count_unchanged": len(c1_toas) == len(release_toas) == 433,
        "unmodeled_refit_converged": unmodeled_returned_converged
        and bool(unmodeled_fitter.converged),
        "exact_frequency_power_exceeds_c0": exact_power > float(c0_probe["power_at_exact_frequency"]),
        "exact_frequency_amplitude_exceeds_c0": exact_sinusoid["amplitude"]
        > float(c0_probe["recovered_amplitude_us"]),
        "c0_joint_fit_converged": bool(c0_joint["returned_converged"])
        and bool(c0_joint["fitter_converged"]),
        "c1_joint_fit_converged": bool(c1_joint["returned_converged"])
        and bool(c1_joint["fitter_converged"]),
        "joint_recovery_fraction_within_bounds": float(method["minimum_joint_recovery_fraction"])
        <= joint_recovery_fraction
        <= float(method["maximum_joint_recovery_fraction"]),
        "joint_phase_error_within_bound": abs(injection_phase_error)
        <= float(method["maximum_joint_phase_error_radians"]),
        "joint_chi2_improvement_exceeds_c0": c1_joint_improvement > c0_joint_improvement,
        "full_covariance_fit_completed": bool(full_cov["completed"]),
        "solver_amplitudes_agree": solver_amplitude_difference_us
        <= float(method["maximum_solver_amplitude_difference_microseconds"]),
        "solver_phases_agree": solver_phase_difference_radians
        <= float(method["maximum_solver_phase_difference_radians"]),
        "solver_chi2_values_agree": solver_chi2_difference
        <= float(method["maximum_solver_chi2_difference"]),
        "material_warnings_dispositioned": warnings["status"] == "pass",
        "periodogram_finite": bool(np.all(np.isfinite(powers))),
        "runtime_under_60_minutes": total_wall_seconds <= 3600,
        "peak_memory_under_16_gib": peak_rss_mib <= 16 * 1024,
        "later_cases_remain_blocked": True,
    }
    scorecard = _scorecard(criteria)
    status = "pass" if scorecard["overall"] == "PASS" else "fail"

    def clean_fit(result: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in result.items()
            if key not in {"fitter", "model", "residuals"}
        }

    record: dict[str, Any] = {
        "schema_version": 1,
        "recorded_utc": recorded.isoformat(),
        "run_id": run_id,
        "case": "C1-R1",
        "case_purpose": "corrective_strong_positive_control",
        "status": status,
        "dataset": "nanograv15yr-v2.1.0",
        "target": "J1744-1134",
        "freeze": freeze,
        "software": {
            "python": platform.python_version(),
            "pint_pulsar": pint.__version__,
            "numpy": np.__version__,
            "process_machine": platform.machine(),
            "longdouble_mantissa_bits": int(np.finfo(np.longdouble).nmant),
            "pixi_lock_sha256": hash_file(repository_root() / "pixi.lock", "sha256"),
        },
        "injection": {
            "period_days": period_days,
            "frequency_per_day": injected_frequency,
            "requested_amplitude_us": requested_amplitude_us,
            "phase_radians": phase_radians,
            "reference_epoch_mjd_tdb": epoch_mjd_tdb,
            "achieved_fitted_amplitude_us": achieved_waveform["amplitude"],
            "maximum_application_error_us": maximum_application_error_us,
            "application_tolerance_us": float(method["maximum_application_error_microseconds"]),
        },
        "ordinary_refit": {
            "returned_converged": unmodeled_returned_converged,
            "fitter_converged": bool(unmodeled_fitter.converged),
            "weighted_rms_us": float(unmodeled_residuals.toa.rms_weighted().to_value(u.us)),
            "wideband_chi2": unmodeled_chi2,
            "reduced_chi2": float(unmodeled_residuals.reduced_chi2),
        },
        "frequency_diagnostic": {
            "grid": grid,
            "global_peak_role": method["blind_global_peak_role"],
            "global_peak_frequency_per_day": peak_frequency,
            "global_peak_period_days": 1.0 / peak_frequency,
            "global_peak_power": float(powers[peak_index]),
            "global_peak_sinusoid": peak_sinusoid,
            "exact_injected_frequency_power": exact_power,
            "exact_injected_frequency_sinusoid": exact_sinusoid,
            "c0_exact_frequency_probe": c0_probe,
            "matched_null_subtracted": blind_matched_null,
            "false_alarm_probability": None,
            "correlated_noise_in_periodogram": "not_modeled",
        },
        "compatible_joint_recovery": {
            "component": "ProjectCircularSignal",
            "c0": clean_fit(c0_joint),
            "c1_r1": clean_fit(c1_joint),
            "matched_null_subtracted": joint_matched_null,
            "matched_null_recovery_fraction": joint_recovery_fraction,
            "matched_null_phase_error_radians": injection_phase_error,
            "c0_chi2_improvement": c0_joint_improvement,
            "c1_r1_chi2_improvement": c1_joint_improvement,
        },
        "independent_full_covariance_crosscheck": {
            "fit": clean_fit(full_cov),
            "low_rank_amplitude_difference_us": solver_amplitude_difference_us,
            "low_rank_phase_difference_radians": solver_phase_difference_radians,
            "low_rank_chi2_difference": solver_chi2_difference,
        },
        "transfer": {
            "blind_residual_recovery_fraction": blind_matched_null["amplitude"]
            / achieved_waveform["amplitude"],
            "standard_timing_model_absorption_fraction": 1
            - blind_matched_null["amplitude"] / achieved_waveform["amplitude"],
            "joint_matched_null_recovery_fraction": joint_recovery_fraction,
        },
        "warnings": warnings,
        "resources": {
            "c0_joint_wall_seconds": c0_joint_wall_seconds,
            "c1_r1_unmodeled_wall_seconds": unmodeled_wall_seconds,
            "c1_r1_joint_wall_seconds": joint_wall_seconds,
            "full_covariance_wall_seconds": full_cov_wall_seconds,
            "total_wall_seconds": total_wall_seconds,
            "cpu_seconds": time.process_time() - cpu_start,
            "peak_rss_mib": peak_rss_mib,
        },
        "criteria": criteria,
        "scorecard": scorecard,
        "outputs": {
            "periodogram": {
                "logical_path": logical_path(periodogram_path, data_root),
                "sha256": hash_file(periodogram_path, "sha256"),
            },
            "unmodeled_model": {
                "logical_path": logical_path(unmodeled_path, data_root),
                "sha256": hash_file(unmodeled_path, "sha256"),
            },
            "joint_model": {
                "logical_path": logical_path(joint_path, data_root),
                "sha256": hash_file(joint_path, "sha256"),
            },
            "c0_joint_model": {
                "logical_path": logical_path(c0_joint_path, data_root),
                "sha256": hash_file(c0_joint_path, "sha256"),
            },
            "full_covariance_model": {
                "logical_path": logical_path(full_cov_path, data_root),
                "sha256": hash_file(full_cov_path, "sha256"),
            },
            "log": {
                "logical_path": logical_path(log_path, data_root),
                "sha256": hash_file(log_path, "sha256"),
            },
            "full_record": logical_path(record_path, data_root),
        },
        "claim_boundary": "C1-R1 validates recovery machinery and is not a detection",
        "authorized_next_cases": [],
        "blocked_cases": ["C2", "C3"],
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
