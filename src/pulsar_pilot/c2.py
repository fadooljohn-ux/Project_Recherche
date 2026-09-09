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
from .config import PilotConfig
from .g2 import classify_warning_lines, validate_free_parameters
from .paths import repository_root
from .provenance import hash_file, logical_path


def validate_c2_configuration(injections: dict[str, Any]) -> dict[str, Any]:
    cases = {str(case["id"]): case for case in injections.get("cases", [])}
    c2 = cases.get("C2")
    stage_c = injections.get("stage_c", {})
    method = stage_c.get("c2", {})
    problems: list[str] = []
    if stage_c.get("authorization") != "c2_only":
        problems.append("Stage C authorization is not limited to C2")
    if c2 is None or float(c2.get("period_days", -1)) != 100.0:
        problems.append("The frozen C2 period is not 100 days")
    if c2 is None or float(c2.get("amplitude_microseconds", -1)) != 5.0:
        problems.append("The frozen C2 amplitude is not 5 microseconds")
    if c2 is None or c2.get("hard_recovery_gate") is not False:
        problems.append("C2 is not marked as a boundary diagnostic")
    if method.get("joint_component") != "ProjectCircularSignal":
        problems.append("C2 joint component is not ProjectCircularSignal")
    if method.get("independent_crosscheck") != (
        "WidebandTOAFitter_explicit_full_covariance"
    ):
        problems.append("C2 full-covariance cross-check is not frozen")
    if method.get("recovery_classification_role") != "diagnostic_not_hard_gate":
        problems.append("C2 recovery classification is not diagnostic")
    if method.get("exact_frequency_c0_comparison_role") != "diagnostic_not_hard_gate":
        problems.append("C2 exact-frequency comparison is not diagnostic")
    if injections.get("trigger", {}).get("false_alarm_probability") != "prohibited":
        problems.append("False-alarm probability prohibition is missing")
    return {"status": "pass" if not problems else "fail", "problems": problems}


def verify_c2_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / "protocol" / "FREEZE_RECORD_v0.6.json"
    authorization_path = root / "protocol" / "STAGE_C_AUTHORIZATION_v0.4.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_first_c2_run":
        failures.append("C2 freeze status is invalid")
    if freeze.get("authorized_cases") != ["C2"]:
        failures.append("C2 is not the only authorized case")
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


def classify_boundary_recovery(
    recovery_fraction: float, absolute_phase_error: float, method: dict[str, Any]
) -> str:
    if (
        float(method["robust_recovery_fraction_minimum"])
        <= recovery_fraction
        <= float(method["robust_recovery_fraction_maximum"])
        and absolute_phase_error <= float(method["robust_phase_error_maximum_radians"])
    ):
        return "robust"
    if (
        float(method["partial_recovery_fraction_minimum"])
        <= recovery_fraction
        <= float(method["partial_recovery_fraction_maximum"])
        and absolute_phase_error <= float(method["partial_phase_error_maximum_radians"])
    ):
        return "partial"
    return "inconsistent"


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
            "configuration_frozen_and_c2_only",
            "release_red_noise_preserved_and_wavex_absent",
        ],
        "injection_integrity": [
            "injection_application_within_tolerance",
            "toa_count_unchanged",
        ],
        "ordinary_refit": ["unmodeled_refit_converged"],
        "joint_execution": ["c0_joint_fit_converged", "c2_joint_fit_converged"],
        "independent_crosscheck": [
            "full_covariance_fit_completed",
            "solver_amplitudes_agree",
            "solver_phases_agree",
            "solver_chi2_values_agree",
        ],
        "warning_hygiene": ["material_warnings_dispositioned"],
        "reproducibility": ["periodogram_finite"],
        "resource_envelope": ["runtime_under_60_minutes", "peak_memory_under_16_gib"],
        "scientific_authorization": ["c3_remains_blocked"],
    }
    rows: dict[str, Any] = {}
    for name, tests in groups.items():
        passed = all(hard_criteria[test] for test in tests)
        rows[name] = {
            "status": "PASS" if passed else "FAIL",
            "hard_gate": True,
            "tests": {test: hard_criteria[test] for test in tests},
        }
    rows["boundary_recovery"] = {
        "status": "DIAGNOSTIC",
        "hard_gate": False,
        "outcome": diagnostic_outcomes["recovery_classification"],
    }
    rows["exact_frequency_comparison"] = {
        "status": "DIAGNOSTIC",
        "hard_gate": False,
        "outcome": diagnostic_outcomes["exact_frequency_comparison"],
    }
    rows["global_strongest_peak"] = {
        "status": "DIAGNOSTIC",
        "hard_gate": False,
        "outcome": diagnostic_outcomes["global_peak_role"],
    }
    return {
        "overall": "PASS" if all(hard_criteria.values()) else "FAIL",
        "rows": rows,
    }


def run_c2(config: PilotConfig, injections: dict[str, Any], data_root: Path) -> dict[str, Any]:
    configuration = validate_c2_configuration(injections)
    freeze = verify_c2_freeze()
    if configuration["status"] != "pass" or freeze["status"] != "pass":
        raise RuntimeError(
            f"Frozen C2 controls are invalid: configuration={configuration}, freeze={freeze}"
        )

    c2_case = next(case for case in injections["cases"] if case["id"] == "C2")
    stage_c = injections["stage_c"]
    method = stage_c["c2"]
    trigger_config = injections["trigger"]
    period_days = float(c2_case["period_days"])
    injected_frequency = 1.0 / period_days
    requested_amplitude_us = float(c2_case["amplitude_microseconds"])
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
    derived_dir = data_root / "derived" / "g3" / "c2"
    cache_root = data_root / "derived" / "cache"
    for directory in (run_dir, derived_dir, cache_root):
        directory.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"c2_boundary_control_{run_id}.log"
    record_path = run_dir / f"c2_boundary_control_{run_id}.json"
    periodogram_path = derived_dir / f"J1744-1134_C2_{run_id}.periodogram.npz"
    unmodeled_path = derived_dir / f"J1744-1134_C2_{run_id}.unmodeled.postfit.par"
    joint_path = derived_dir / f"J1744-1134_C2_{run_id}.joint-circular.postfit.par"
    c0_joint_path = derived_dir / f"J1744-1134_C0_{run_id}.joint-circular.postfit.par"
    full_cov_path = derived_dir / f"J1744-1134_C2_{run_id}.full-cov.postfit.par"

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

    c2_toas = copy.deepcopy(release_toas)
    original_mjds = release_toas.get_mjds(high_precision=True).copy()
    c2_toas.adjust_TOAs(requested_delays_us * u.us)
    adjusted_mjds = c2_toas.get_mjds(high_precision=True).copy()
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
    unmodeled_fitter = WidebandDownhillFitter(c2_toas, copy.deepcopy(release_model))
    unmodeled_returned_converged = bool(
        unmodeled_fitter.fit_toas(maxiter=config.max_fit_iterations)
    )
    unmodeled_wall_seconds = time.perf_counter() - unmodeled_start
    unmodeled_residuals = WidebandTOAResiduals(c2_toas, unmodeled_fitter.model)
    unmodeled_chi2 = float(unmodeled_residuals.chi2)

    toa_residuals_us = unmodeled_residuals.toa.calc_time_resids().to_value(u.us).astype(float)
    toa_uncertainties_us = unmodeled_fitter.model.scaled_toa_uncertainty(c2_toas).to_value(u.us)
    mjds = np.asarray(c2_toas.get_mjds().value, dtype=float)
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
    c2_joint = _joint_downhill_fit(
        c2_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        config.max_fit_iterations,
    )
    joint_wall_seconds = time.perf_counter() - joint_start
    c2_joint_improvement = unmodeled_chi2 - float(c2_joint["chi2"])
    joint_matched_null = complex_amplitude_difference(
        float(c2_joint["sine_us"]),
        float(c2_joint["cosine_us"]),
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

    full_cov_start = time.perf_counter()
    full_cov = _joint_full_covariance_fit(
        c2_toas,
        release_model,
        injected_frequency,
        epoch_mjd_tdb,
        int(method["independent_crosscheck_max_iterations"]),
    )
    full_cov_wall_seconds = time.perf_counter() - full_cov_start
    solver_amplitude_difference_us = abs(
        float(c2_joint["amplitude_us"]) - float(full_cov["amplitude_us"])
    )
    solver_phase_difference_radians = abs(
        wrapped_phase_difference(
            float(c2_joint["phase_radians"]), float(full_cov["phase_radians"])
        )
    )
    solver_chi2_difference = abs(float(c2_joint["chi2"]) - float(full_cov["chi2"]))

    np.savez_compressed(
        periodogram_path,
        frequency_per_day=frequencies,
        period_days=1.0 / frequencies,
        power=powers,
    )
    model_outputs = [
        (unmodeled_path, unmodeled_fitter.model, "C2 ordinary refit"),
        (joint_path, c2_joint["model"], "C2 joint deterministic circular-signal refit"),
        (c0_joint_path, c0_joint["model"], "same-run C0 joint circular-signal refit"),
        (full_cov_path, full_cov["model"], "C2 explicit full-covariance refit"),
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
    hard_criteria = {
        "configuration_frozen_and_c2_only": configuration["status"] == "pass"
        and freeze["status"] == "pass",
        "release_red_noise_preserved_and_wavex_absent": bool(
            c0_joint["release_red_noise_preserved"]
            and c0_joint["wavex_absent"]
            and c2_joint["release_red_noise_preserved"]
            and c2_joint["wavex_absent"]
            and full_cov["release_red_noise_preserved"]
            and full_cov["wavex_absent"]
        ),
        "injection_application_within_tolerance": maximum_application_error_us
        <= float(method["maximum_application_error_microseconds"]),
        "toa_count_unchanged": len(c2_toas) == len(release_toas) == 433,
        "unmodeled_refit_converged": unmodeled_returned_converged
        and bool(unmodeled_fitter.converged),
        "c0_joint_fit_converged": bool(c0_joint["returned_converged"])
        and bool(c0_joint["fitter_converged"]),
        "c2_joint_fit_converged": bool(c2_joint["returned_converged"])
        and bool(c2_joint["fitter_converged"]),
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
        "c3_remains_blocked": True,
    }
    exact_frequency_comparison = (
        "exceeds_c0"
        if exact_power > float(c0_probe["power_at_exact_frequency"])
        and exact_sinusoid["amplitude"] > float(c0_probe["recovered_amplitude_us"])
        else "at_or_below_c0"
    )
    diagnostic_outcomes = {
        "recovery_classification": recovery_classification,
        "exact_frequency_comparison": exact_frequency_comparison,
        "global_peak_role": method["blind_global_peak_role"],
        "joint_chi2_improvement_exceeds_c0": c2_joint_improvement > c0_joint_improvement,
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
        "case": "C2",
        "case_purpose": "lower_amplitude_boundary_diagnostic",
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
            "false_alarm_probability": None,
            "correlated_noise_in_periodogram": "not_modeled",
        },
        "compatible_joint_recovery": {
            "component": "ProjectCircularSignal",
            "c0": clean_fit(c0_joint),
            "c2": clean_fit(c2_joint),
            "matched_null_subtracted": joint_matched_null,
            "matched_null_recovery_fraction": joint_recovery_fraction,
            "matched_null_phase_error_radians": injection_phase_error,
            "recovery_classification": recovery_classification,
            "c0_chi2_improvement": c0_joint_improvement,
            "c2_chi2_improvement": c2_joint_improvement,
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
            "c2_unmodeled_wall_seconds": unmodeled_wall_seconds,
            "c2_joint_wall_seconds": joint_wall_seconds,
            "full_covariance_wall_seconds": full_cov_wall_seconds,
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
        "claim_boundary": "C2 is a boundary diagnostic and is not a detection",
        "authorized_next_cases": [],
        "blocked_cases": ["C3"],
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
