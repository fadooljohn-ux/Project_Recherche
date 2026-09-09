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
from .c1r1 import (
    _joint_downhill_fit,
    _joint_full_covariance_fit,
    wrapped_phase_difference,
)
from .c2 import classify_boundary_recovery
from .config import PilotConfig
from .g2 import classify_warning_lines, validate_free_parameters
from .paths import repository_root
from .provenance import hash_file, logical_path


def validate_c3_configuration(injections: dict[str, Any]) -> dict[str, Any]:
    cases = {str(case["id"]): case for case in injections.get("cases", [])}
    c3 = cases.get("C3")
    stage_c = injections.get("stage_c", {})
    method = stage_c.get("c3", {})
    problems: list[str] = []
    if stage_c.get("authorization") != "c3_only":
        problems.append("Stage C authorization is not limited to C3")
    if c3 is None or float(c3.get("period_days", -1)) != 365.25:
        problems.append("The frozen C3 period is not 365.25 days")
    if c3 is None or float(c3.get("amplitude_microseconds", -1)) != 20.0:
        problems.append("The frozen C3 amplitude is not 20 microseconds")
    if c3 is None or c3.get("hard_recovery_gate") is not False:
        problems.append("C3 is not marked as an annual stress diagnostic")
    if method.get("joint_component") != "ProjectCircularSignal":
        problems.append("C3 joint component is not ProjectCircularSignal")
    if method.get("same_run_c0_ordinary_comparator") is not True:
        problems.append("C3 same-run C0 ordinary comparator is not required")
    if method.get("independent_crosscheck") != (
        "WidebandTOAFitter_explicit_full_covariance"
    ):
        problems.append("C3 full-covariance cross-check is not frozen")
    if method.get("annual_identifiability_role") != "diagnostic_not_hard_gate":
        problems.append("C3 annual identifiability is not diagnostic")
    if method.get("final_pilot0_injection_case") is not True:
        problems.append("C3 is not frozen as the final Pilot 0 injection case")
    if injections.get("trigger", {}).get("false_alarm_probability") != "prohibited":
        problems.append("False-alarm probability prohibition is missing")
    return {"status": "pass" if not problems else "fail", "problems": problems}


def verify_c3_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / "protocol" / "FREEZE_RECORD_v0.7.json"
    authorization_path = root / "protocol" / "STAGE_C_AUTHORIZATION_v0.5.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_first_c3_run":
        failures.append("C3 freeze status is invalid")
    if freeze.get("authorized_cases") != ["C3"]:
        failures.append("C3 is not the only authorized case")
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


def classify_annual_coupling(maximum_absolute_correlation: float, method: dict[str, Any]) -> str:
    if maximum_absolute_correlation >= float(method["strong_correlation_minimum"]):
        return "strong"
    if maximum_absolute_correlation >= float(method["moderate_correlation_minimum"]):
        return "moderate"
    return "low"


def classify_astrometric_shift(maximum_absolute_delta_sigma: float, method: dict[str, Any]) -> str:
    if maximum_absolute_delta_sigma >= float(method["severe_astrometric_shift_sigma"]):
        return "severe"
    if maximum_absolute_delta_sigma >= float(method["material_astrometric_shift_sigma"]):
        return "material"
    return "small"


def classify_absorption(absorption_fraction: float, method: dict[str, Any]) -> str:
    if absorption_fraction >= float(method["strong_absorption_fraction"]):
        return "strong"
    if absorption_fraction >= float(method["material_absorption_fraction"]):
        return "material"
    return "limited"


def classify_solver_stability(
    amplitude_difference_us: float,
    phase_difference_radians: float,
    chi2_improvement_difference: float,
    method: dict[str, Any],
) -> str:
    if (
        amplitude_difference_us
        <= float(method["solver_stability_amplitude_difference_microseconds"])
        and phase_difference_radians
        <= float(method["solver_stability_phase_difference_radians"])
        and chi2_improvement_difference
        <= float(method["solver_stability_chi2_improvement_difference"])
    ):
        return "stable"
    return "sensitive"


def extract_annual_correlation_diagnostic(
    fitter: Any, astrometric_parameters: list[str]
) -> dict[str, Any]:
    signal_parameters = ["CSSIN", "CSCOS"]
    labels = signal_parameters + astrometric_parameters
    matrix = fitter.parameter_correlation_matrix.get_label_matrix(labels)
    ordered = matrix.get_label_names(0)
    index = {name: position for position, name in enumerate(ordered)}
    correlations: dict[str, dict[str, float]] = {}
    candidates: list[tuple[float, str, str, float]] = []
    for signal in signal_parameters:
        correlations[signal] = {}
        for astrometric in astrometric_parameters:
            value = float(matrix.matrix[index[signal], index[astrometric]])
            correlations[signal][astrometric] = value
            candidates.append((abs(value), signal, astrometric, value))
    maximum, signal, astrometric, signed_value = max(candidates)
    return {
        "labels": ordered,
        "matrix": matrix.matrix.tolist(),
        "signal_to_astrometry": correlations,
        "maximum_absolute_correlation": maximum,
        "maximum_pair": {
            "signal_parameter": signal,
            "astrometric_parameter": astrometric,
            "correlation": signed_value,
        },
        "submatrix_condition_number": float(np.linalg.cond(matrix.matrix)),
    }


def compare_astrometric_parameters(
    c0_model: Any, injected_model: Any, parameter_names: list[str]
) -> dict[str, Any]:
    parameters: list[dict[str, Any]] = []
    for name in parameter_names:
        c0_parameter = getattr(c0_model, name)
        injected_parameter = getattr(injected_model, name)
        unit = c0_parameter.units
        c0_value = float(c0_parameter.quantity.to_value(unit))
        injected_value = float(injected_parameter.quantity.to_value(unit))
        delta = injected_value - c0_value
        c0_uncertainty = float(c0_parameter.uncertainty.to_value(unit))
        injected_uncertainty = float(injected_parameter.uncertainty.to_value(unit))
        parameters.append(
            {
                "name": name,
                "unit": str(unit),
                "c0_value": c0_value,
                "c3_value": injected_value,
                "delta": delta,
                "c0_postfit_uncertainty": c0_uncertainty,
                "c3_postfit_uncertainty": injected_uncertainty,
                "absolute_delta_sigma": abs(delta) / c0_uncertainty,
                "uncertainty_ratio_c3_to_c0": injected_uncertainty / c0_uncertainty,
            }
        )
    worst = max(parameters, key=lambda item: float(item["absolute_delta_sigma"]))
    return {
        "parameters": parameters,
        "maximum_absolute_delta_sigma": worst["absolute_delta_sigma"],
        "maximum_parameter": worst["name"],
    }


def _load_c0_record(method: dict[str, Any], data_root: Path) -> dict[str, Any]:
    summary_path = repository_root() / method["matched_null_source"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    external = summary["external_outputs"]["full_record"]
    record_path = data_root / external["logical_path"]
    if hash_file(record_path, "sha256") != external["sha256"]:
        raise RuntimeError("Authoritative C0 record hash does not match its tracked summary")
    return json.loads(record_path.read_text(encoding="utf-8"))


def _peak_rss_mib() -> float:
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**2 if platform.system() == "Darwin" else 1024
    return peak / divisor


def _scorecard(
    hard_criteria: dict[str, bool], diagnostic_outcomes: dict[str, Any]
) -> dict[str, Any]:
    groups = {
        "protocol_control": [
            "configuration_frozen_and_c3_only",
            "release_red_noise_preserved_and_wavex_absent",
        ],
        "injection_integrity": [
            "injection_application_within_tolerance",
            "toa_count_unchanged",
        ],
        "ordinary_execution": [
            "c0_ordinary_fit_converged",
            "c3_ordinary_fit_converged",
        ],
        "joint_execution": [
            "c0_joint_fit_converged",
            "c3_joint_fit_converged",
            "joint_outputs_finite",
        ],
        "full_covariance_execution": [
            "c0_full_covariance_fit_completed",
            "c3_full_covariance_fit_completed",
            "full_covariance_outputs_finite",
        ],
        "warning_hygiene": ["material_warnings_dispositioned"],
        "reproducibility": ["periodogram_finite"],
        "resource_envelope": ["runtime_under_60_minutes", "peak_memory_under_16_gib"],
        "scientific_authorization": ["pilot0_injections_complete_and_no_next_case_authorized"],
    }
    rows: dict[str, Any] = {}
    for name, tests in groups.items():
        passed = all(hard_criteria[test] for test in tests)
        rows[name] = {
            "status": "PASS" if passed else "FAIL",
            "hard_gate": True,
            "tests": {test: hard_criteria[test] for test in tests},
        }
    diagnostic_rows = {
        "ordinary_model_absorption": "absorption_classification",
        "annual_recovery": "recovery_classification",
        "annual_identifiability": "annual_coupling_classification",
        "astrometric_displacement": "astrometric_shift_classification",
        "solver_stability": "solver_stability_classification",
        "exact_frequency_comparison": "exact_frequency_comparison",
        "global_strongest_peak": "global_peak_role",
    }
    for row, outcome in diagnostic_rows.items():
        rows[row] = {
            "status": "DIAGNOSTIC",
            "hard_gate": False,
            "outcome": diagnostic_outcomes[outcome],
        }
    return {
        "overall": "PASS" if all(hard_criteria.values()) else "FAIL",
        "rows": rows,
    }


def run_c3(config: PilotConfig, injections: dict[str, Any], data_root: Path) -> dict[str, Any]:
    configuration = validate_c3_configuration(injections)
    freeze = verify_c3_freeze()
    if configuration["status"] != "pass" or freeze["status"] != "pass":
        raise RuntimeError(
            f"Frozen C3 controls are invalid: configuration={configuration}, freeze={freeze}"
        )

    c3_case = next(case for case in injections["cases"] if case["id"] == "C3")
    stage_c = injections["stage_c"]
    method = stage_c["c3"]
    trigger_config = injections["trigger"]
    astrometric_parameters = list(method["astrometric_parameters"])
    period_days = float(c3_case["period_days"])
    injected_frequency = 1.0 / period_days
    requested_amplitude_us = float(c3_case["amplitude_microseconds"])
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
    derived_dir = data_root / "derived" / "g3" / "c3"
    cache_root = data_root / "derived" / "cache"
    for directory in (run_dir, derived_dir, cache_root):
        directory.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"c3_annual_stress_{run_id}.log"
    record_path = run_dir / f"c3_annual_stress_{run_id}.json"
    periodogram_path = derived_dir / f"J1744-1134_C3_{run_id}.periodogram.npz"
    c0_ordinary_path = derived_dir / f"J1744-1134_C0_{run_id}.ordinary.postfit.par"
    c3_ordinary_path = derived_dir / f"J1744-1134_C3_{run_id}.ordinary.postfit.par"
    c0_joint_path = derived_dir / f"J1744-1134_C0_{run_id}.joint-circular.postfit.par"
    c3_joint_path = derived_dir / f"J1744-1134_C3_{run_id}.joint-circular.postfit.par"
    c0_full_cov_path = derived_dir / f"J1744-1134_C0_{run_id}.full-cov.postfit.par"
    c3_full_cov_path = derived_dir / f"J1744-1134_C3_{run_id}.full-cov.postfit.par"

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

    c3_toas = copy.deepcopy(release_toas)
    original_mjds = release_toas.get_mjds(high_precision=True).copy()
    c3_toas.adjust_TOAs(requested_delays_us * u.us)
    adjusted_mjds = c3_toas.get_mjds(high_precision=True).copy()
    actual_delays_us = np.array(
        [
            (adjusted - original).to_value(u.us)
            for adjusted, original in zip(adjusted_mjds, original_mjds)
        ]
    )
    maximum_application_error_us = float(
        np.max(np.abs(actual_delays_us - np.asarray(requested_delays_us, dtype=float)))
    )

    c0_ordinary_start = time.perf_counter()
    c0_ordinary_fitter = WidebandDownhillFitter(release_toas, copy.deepcopy(release_model))
    c0_ordinary_returned_converged = bool(
        c0_ordinary_fitter.fit_toas(maxiter=config.max_fit_iterations)
    )
    c0_ordinary_wall_seconds = time.perf_counter() - c0_ordinary_start
    c0_ordinary_residuals = WidebandTOAResiduals(release_toas, c0_ordinary_fitter.model)
    c0_ordinary_chi2 = float(c0_ordinary_residuals.chi2)

    c3_ordinary_start = time.perf_counter()
    c3_ordinary_fitter = WidebandDownhillFitter(c3_toas, copy.deepcopy(release_model))
    c3_ordinary_returned_converged = bool(
        c3_ordinary_fitter.fit_toas(maxiter=config.max_fit_iterations)
    )
    c3_ordinary_wall_seconds = time.perf_counter() - c3_ordinary_start
    c3_ordinary_residuals = WidebandTOAResiduals(c3_toas, c3_ordinary_fitter.model)
    c3_ordinary_chi2 = float(c3_ordinary_residuals.chi2)
    astrometric_displacement = compare_astrometric_parameters(
        c0_ordinary_fitter.model, c3_ordinary_fitter.model, astrometric_parameters
    )
    astrometric_shift_classification = classify_astrometric_shift(
        float(astrometric_displacement["maximum_absolute_delta_sigma"]), method
    )

    toa_residuals_us = c3_ordinary_residuals.toa.calc_time_resids().to_value(u.us).astype(float)
    toa_uncertainties_us = c3_ordinary_fitter.model.scaled_toa_uncertainty(c3_toas).to_value(u.us)
    mjds = np.asarray(c3_toas.get_mjds().value, dtype=float)
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
    blind_recovery_fraction = blind_matched_null["amplitude"] / achieved_waveform["amplitude"]
    absorption_fraction = 1 - blind_recovery_fraction
    absorption_classification = classify_absorption(absorption_fraction, method)

    c0_joint_start = time.perf_counter()
    c0_joint = _joint_downhill_fit(
        release_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        config.max_fit_iterations,
    )
    c0_joint_wall_seconds = time.perf_counter() - c0_joint_start
    c0_joint_improvement = c0_ordinary_chi2 - float(c0_joint["chi2"])

    c3_joint_start = time.perf_counter()
    c3_joint = _joint_downhill_fit(
        c3_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        config.max_fit_iterations,
    )
    c3_joint_wall_seconds = time.perf_counter() - c3_joint_start
    c3_joint_improvement = c3_ordinary_chi2 - float(c3_joint["chi2"])
    joint_matched_null = complex_amplitude_difference(
        float(c3_joint["sine_us"]),
        float(c3_joint["cosine_us"]),
        float(c0_joint["sine_us"]),
        float(c0_joint["cosine_us"]),
    )
    injection_phase_error = wrapped_phase_difference(
        joint_matched_null["phase_radians"], phase_radians
    )
    joint_recovery_fraction = joint_matched_null["amplitude"] / achieved_waveform["amplitude"]
    recovery_classification = classify_boundary_recovery(
        joint_recovery_fraction, abs(injection_phase_error), method
    )
    low_rank_correlation = extract_annual_correlation_diagnostic(
        c3_joint["fitter"], astrometric_parameters
    )
    annual_coupling_classification = classify_annual_coupling(
        float(low_rank_correlation["maximum_absolute_correlation"]), method
    )

    c0_full_cov_start = time.perf_counter()
    c0_full_cov = _joint_full_covariance_fit(
        release_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        int(method["independent_crosscheck_max_iterations"]),
    )
    c0_full_cov_wall_seconds = time.perf_counter() - c0_full_cov_start
    c0_full_cov_improvement = c0_ordinary_chi2 - float(c0_full_cov["chi2"])

    c3_full_cov_start = time.perf_counter()
    c3_full_cov = _joint_full_covariance_fit(
        c3_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        int(method["independent_crosscheck_max_iterations"]),
    )
    c3_full_cov_wall_seconds = time.perf_counter() - c3_full_cov_start
    c3_full_cov_improvement = c3_ordinary_chi2 - float(c3_full_cov["chi2"])
    full_cov_matched_null = complex_amplitude_difference(
        float(c3_full_cov["sine_us"]),
        float(c3_full_cov["cosine_us"]),
        float(c0_full_cov["sine_us"]),
        float(c0_full_cov["cosine_us"]),
    )
    solver_amplitude_difference_us = abs(
        float(joint_matched_null["amplitude"]) - float(full_cov_matched_null["amplitude"])
    )
    solver_phase_difference_radians = abs(
        wrapped_phase_difference(
            float(joint_matched_null["phase_radians"]),
            float(full_cov_matched_null["phase_radians"]),
        )
    )
    low_rank_differential_improvement = c3_joint_improvement - c0_joint_improvement
    full_cov_differential_improvement = c3_full_cov_improvement - c0_full_cov_improvement
    solver_chi2_improvement_difference = abs(
        low_rank_differential_improvement - full_cov_differential_improvement
    )
    solver_stability_classification = classify_solver_stability(
        solver_amplitude_difference_us,
        solver_phase_difference_radians,
        solver_chi2_improvement_difference,
        method,
    )
    full_cov_correlation = extract_annual_correlation_diagnostic(
        c3_full_cov["fitter"], astrometric_parameters
    )

    np.savez_compressed(
        periodogram_path,
        frequency_per_day=frequencies,
        period_days=1.0 / frequencies,
        power=powers,
    )
    model_outputs = [
        (c0_ordinary_path, c0_ordinary_fitter.model, "same-run C0 ordinary refit"),
        (c3_ordinary_path, c3_ordinary_fitter.model, "C3 ordinary refit"),
        (c0_joint_path, c0_joint["model"], "same-run C0 joint circular-signal refit"),
        (c3_joint_path, c3_joint["model"], "C3 joint circular-signal refit"),
        (c0_full_cov_path, c0_full_cov["model"], "same-run C0 full-covariance refit"),
        (c3_full_cov_path, c3_full_cov["model"], "C3 full-covariance refit"),
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
    joint_finite_values = [
        c0_joint["amplitude_us"],
        c0_joint["chi2"],
        c3_joint["amplitude_us"],
        c3_joint["chi2"],
    ]
    full_cov_finite_values = [
        c0_full_cov["amplitude_us"],
        c0_full_cov["chi2"],
        c3_full_cov["amplitude_us"],
        c3_full_cov["chi2"],
    ]
    hard_criteria = {
        "configuration_frozen_and_c3_only": configuration["status"] == "pass"
        and freeze["status"] == "pass",
        "release_red_noise_preserved_and_wavex_absent": bool(
            c0_joint["release_red_noise_preserved"]
            and c0_joint["wavex_absent"]
            and c3_joint["release_red_noise_preserved"]
            and c3_joint["wavex_absent"]
            and c0_full_cov["release_red_noise_preserved"]
            and c0_full_cov["wavex_absent"]
            and c3_full_cov["release_red_noise_preserved"]
            and c3_full_cov["wavex_absent"]
        ),
        "injection_application_within_tolerance": maximum_application_error_us
        <= float(method["maximum_application_error_microseconds"]),
        "toa_count_unchanged": len(c3_toas) == len(release_toas) == 433,
        "c0_ordinary_fit_converged": c0_ordinary_returned_converged
        and bool(c0_ordinary_fitter.converged),
        "c3_ordinary_fit_converged": c3_ordinary_returned_converged
        and bool(c3_ordinary_fitter.converged),
        "c0_joint_fit_converged": bool(c0_joint["returned_converged"])
        and bool(c0_joint["fitter_converged"]),
        "c3_joint_fit_converged": bool(c3_joint["returned_converged"])
        and bool(c3_joint["fitter_converged"]),
        "joint_outputs_finite": bool(np.all(np.isfinite(joint_finite_values))),
        "c0_full_covariance_fit_completed": bool(c0_full_cov["completed"]),
        "c3_full_covariance_fit_completed": bool(c3_full_cov["completed"]),
        "full_covariance_outputs_finite": bool(
            np.all(np.isfinite(full_cov_finite_values))
        ),
        "material_warnings_dispositioned": warnings["status"] == "pass",
        "periodogram_finite": bool(np.all(np.isfinite(powers))),
        "runtime_under_60_minutes": total_wall_seconds <= 3600,
        "peak_memory_under_16_gib": peak_rss_mib <= 16 * 1024,
        "pilot0_injections_complete_and_no_next_case_authorized": True,
    }
    exact_frequency_comparison = (
        "exceeds_c0"
        if exact_power > float(c0_probe["power_at_exact_frequency"])
        and exact_sinusoid["amplitude"] > float(c0_probe["recovered_amplitude_us"])
        else "at_or_below_c0"
    )
    diagnostic_outcomes = {
        "absorption_classification": absorption_classification,
        "recovery_classification": recovery_classification,
        "annual_coupling_classification": annual_coupling_classification,
        "astrometric_shift_classification": astrometric_shift_classification,
        "solver_stability_classification": solver_stability_classification,
        "exact_frequency_comparison": exact_frequency_comparison,
        "global_peak_role": method["blind_global_peak_role"],
    }
    scorecard = _scorecard(hard_criteria, diagnostic_outcomes)
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
        "case": "C3",
        "case_purpose": "annual_absorption_and_identifiability_stress_test",
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
        "ordinary_refits": {
            "c0": {
                "returned_converged": c0_ordinary_returned_converged,
                "fitter_converged": bool(c0_ordinary_fitter.converged),
                "weighted_rms_us": float(
                    c0_ordinary_residuals.toa.rms_weighted().to_value(u.us)
                ),
                "wideband_chi2": c0_ordinary_chi2,
                "reduced_chi2": float(c0_ordinary_residuals.reduced_chi2),
            },
            "c3": {
                "returned_converged": c3_ordinary_returned_converged,
                "fitter_converged": bool(c3_ordinary_fitter.converged),
                "weighted_rms_us": float(
                    c3_ordinary_residuals.toa.rms_weighted().to_value(u.us)
                ),
                "wideband_chi2": c3_ordinary_chi2,
                "reduced_chi2": float(c3_ordinary_residuals.reduced_chi2),
            },
            "astrometric_displacement": astrometric_displacement,
            "astrometric_shift_classification": astrometric_shift_classification,
        },
        "frequency_diagnostic": {
            "grid": grid,
            "exact_frequency_comparison": exact_frequency_comparison,
            "global_peak_role": method["blind_global_peak_role"],
            "global_peak_frequency_per_day": peak_frequency,
            "global_peak_period_days": 1.0 / peak_frequency,
            "global_peak_power": float(powers[peak_index]),
            "global_peak_sinusoid": peak_sinusoid,
            "exact_injected_frequency_power": exact_power,
            "exact_injected_frequency_sinusoid": exact_sinusoid,
            "c0_exact_frequency_probe": c0_probe,
            "matched_null_subtracted": blind_matched_null,
            "blind_residual_recovery_fraction": blind_recovery_fraction,
            "ordinary_model_absorption_fraction": absorption_fraction,
            "absorption_classification": absorption_classification,
            "false_alarm_probability": None,
            "correlated_noise_in_periodogram": "not_modeled",
        },
        "compatible_joint_recovery": {
            "component": "ProjectCircularSignal",
            "c0": clean_fit(c0_joint),
            "c3": clean_fit(c3_joint),
            "matched_null_subtracted": joint_matched_null,
            "matched_null_recovery_fraction": joint_recovery_fraction,
            "matched_null_phase_error_radians": injection_phase_error,
            "recovery_classification": recovery_classification,
            "c0_chi2_improvement": c0_joint_improvement,
            "c3_chi2_improvement": c3_joint_improvement,
            "differential_chi2_improvement": low_rank_differential_improvement,
            "annual_correlation": low_rank_correlation,
            "annual_coupling_classification": annual_coupling_classification,
        },
        "independent_full_covariance_crosscheck": {
            "c0": clean_fit(c0_full_cov),
            "c3": clean_fit(c3_full_cov),
            "matched_null_subtracted": full_cov_matched_null,
            "c0_chi2_improvement": c0_full_cov_improvement,
            "c3_chi2_improvement": c3_full_cov_improvement,
            "differential_chi2_improvement": full_cov_differential_improvement,
            "low_rank_amplitude_difference_us": solver_amplitude_difference_us,
            "low_rank_phase_difference_radians": solver_phase_difference_radians,
            "low_rank_chi2_improvement_difference": solver_chi2_improvement_difference,
            "solver_stability_classification": solver_stability_classification,
            "annual_correlation": full_cov_correlation,
        },
        "warnings": warnings,
        "resources": {
            "c0_ordinary_wall_seconds": c0_ordinary_wall_seconds,
            "c3_ordinary_wall_seconds": c3_ordinary_wall_seconds,
            "c0_joint_wall_seconds": c0_joint_wall_seconds,
            "c3_joint_wall_seconds": c3_joint_wall_seconds,
            "c0_full_covariance_wall_seconds": c0_full_cov_wall_seconds,
            "c3_full_covariance_wall_seconds": c3_full_cov_wall_seconds,
            "total_wall_seconds": total_wall_seconds,
            "cpu_seconds": time.process_time() - cpu_start,
            "peak_rss_mib": peak_rss_mib,
        },
        "hard_criteria": hard_criteria,
        "diagnostic_outcomes": diagnostic_outcomes,
        "scorecard": scorecard,
        "outputs": {
            "periodogram": {
                "logical_path": logical_path(periodogram_path, data_root),
                "sha256": hash_file(periodogram_path, "sha256"),
            },
            "c0_ordinary_model": {
                "logical_path": logical_path(c0_ordinary_path, data_root),
                "sha256": hash_file(c0_ordinary_path, "sha256"),
            },
            "c3_ordinary_model": {
                "logical_path": logical_path(c3_ordinary_path, data_root),
                "sha256": hash_file(c3_ordinary_path, "sha256"),
            },
            "c0_joint_model": {
                "logical_path": logical_path(c0_joint_path, data_root),
                "sha256": hash_file(c0_joint_path, "sha256"),
            },
            "c3_joint_model": {
                "logical_path": logical_path(c3_joint_path, data_root),
                "sha256": hash_file(c3_joint_path, "sha256"),
            },
            "c0_full_covariance_model": {
                "logical_path": logical_path(c0_full_cov_path, data_root),
                "sha256": hash_file(c0_full_cov_path, "sha256"),
            },
            "c3_full_covariance_model": {
                "logical_path": logical_path(c3_full_cov_path, data_root),
                "sha256": hash_file(c3_full_cov_path, "sha256"),
            },
            "log": {
                "logical_path": logical_path(log_path, data_root),
                "sha256": hash_file(log_path, "sha256"),
            },
            "full_record": logical_path(record_path, data_root),
        },
        "claim_boundary": (
            "C3 is an annual identifiability stress test and is not a detection"
        ),
        "authorized_next_cases": [],
        "blocked_cases": [],
        "pilot0_injection_cases_complete": True,
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
