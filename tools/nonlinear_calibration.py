"""Prepare, calibrate, freeze and run one binary with the nonlinear orbit statistic.

prepare and calibrate use the timing design, covariance and simulated data;
the observed residual vector is read in prepare only for the null (no-companion)
orbit fit and is scanned over periods only by run, once, after freeze.
"""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import chi2
import binary_noise_coverage as coverage
import binary_wideband as binary
import nonlinear_statistic as ns
import nonlinear_verification as verification
import target_calibration as cal
from j1857_nonlinear import ProjectedFit
from recherche_common import require
from pulsar_pilot.pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner

CODE = [__file__, ns.__file__, verification.__file__, binary.__file__, coverage.__file__, cal.__file__,
        str(Path(__file__).with_name("j1857_nonlinear.py"))]


def code_hashes():
    return {Path(p).name: cal.digest(p) for p in CODE}


def now():
    return datetime.now(timezone.utc).isoformat()


def build(root):
    """Scan objects from a saved profile: nonlinear statistic, linearised scanner and baseline."""
    profile = cal.read(root / "profile/profile.json")
    require(cal.digest(root / "profile/arrays.npz") == profile["arrays_sha256"], "Profile arrays changed")
    with np.load(root / "profile/arrays.npz", allow_pickle=False) as z:
        a = {k: z[k] for k in z.files}
    delay = ns.PolynomialDelay(a["surrogate_coefficients"], a["surrogate_exponents"], a["orbit_lower"], a["orbit_upper"])
    templates = ns.periodic_templates(a["times"], a["frequencies"], profile["reference_epoch_mjd_tdb"], len(a["covariance"]))
    scan = ns.NonlinearScan(a["covariance"], a["nuisance"], delay, templates)
    dimension = len(a["orbit_lower"])
    design = np.column_stack([a["nuisance"], a["surrogate_coefficients"][:, :dimension]])
    args = (a["times"], a["frequencies"], profile["reference_epoch_mjd_tdb"])
    linear = prepare_covariance_gls_scanner(a["covariance"], design, *args)
    baseline = prepare_covariance_gls_scanner(a["covariance"], a["baseline"], *args)
    return profile, a, scan, linear, baseline


def prepare(data, scope_path, root):
    scope = cal.read(scope_path)
    out = root / "prepared"
    root.mkdir(parents=True, exist_ok=True)
    out.mkdir(exist_ok=False)
    cal.write(out / "scope.json", scope)
    try:
        from pint.residuals import WidebandTOAResiduals
        with ExitStack() as stack:
            state = verification.load(data, scope, out, stack)
            orbit, covariance, nuisance, times = state["orbit"], state["covariance"], state["nuisance"], state["times"]
            residuals = np.asarray(WidebandTOAResiduals(state["toas"], state["model"]).calc_wideband_resids(), float)
            require(len(residuals) == 2 * len(times), "Wideband layout mismatch")
            require(np.ptp(residuals[: len(times)]) * float(state["model"].F0.value) < 0.5, "Phase connection mismatch")
            s = scope["surrogate"]
            train = ns.sample_domain(orbit.lower, orbit.upper, s["training_points"], s["training_seed"])
            delay = ns.PolynomialDelay.fit(lambda x: np.asarray(orbit.delay(x), float), orbit.lower, orbit.upper, s["degree"], train,
                                           verification.surrogate_exponents(scope, orbit.parameters))
            frequencies, grid = build_search_frequency_grid(
                times, state["minimum_period"], min(2000.0, float(np.ptp(times)) / 2), scope["policy"]["oversampling"])
            templates = ns.periodic_templates(times, frequencies, state["epoch"], len(covariance))
            scan = ns.NonlinearScan(covariance, nuisance, delay, templates)
            test = np.random.default_rng(s["validation_seed"]).uniform(orbit.lower, orbit.upper, size=(s["validation_points"], len(orbit.lower)))
            errors = [float(np.linalg.norm(scan.project(np.asarray(orbit.delay(x), float) - delay(x)))) for x in test]
            # Null (no-companion) orbit fit of the observed residuals: native reference and fast statistic.
            fit = ProjectedFit(covariance, nuisance, residuals, orbit)
            starts = []
            for value in scope["optimizer_starts"]:
                start = np.zeros(len(orbit.lower))
                start[-1] = value
                starts.append(start)
            solutions = [least_squares(fit.residual, x, jac=fit.jacobian, bounds=(orbit.lower, orbit.upper),
                                       max_nfev=scope["maximum_function_evaluations"], ftol=1e-12, xtol=1e-12, gtol=1e-10)
                         for x in starts]
            best = min(solutions, key=lambda r: r.cost)
            native_chi2 = 2 * best.cost
            whitened = scan.project(residuals)
            c = scan.B.T @ whitened
            fast_x, fast_value, _, fast_active = scan._minimise(np.zeros((1, len(orbit.lower))), c)
            fast_chi2 = float(whitened @ whitened - c @ c + fast_value[0])
            joint = np.column_stack([fit.W, fit.white(orbit.jacobian(best.x))])
            rank = int(np.linalg.matrix_rank(joint / np.linalg.norm(joint, axis=0)))
            dof = len(residuals) - rank
            orbit.set(np.zeros(len(orbit.lower)))
            require(not state["deny"].attempts, "Scientific network access attempted")
        margin = float(np.minimum(best.x - orbit.lower, orbit.upper - best.x).min())
        checks = {
            "surrogate_validation_error_norm": {"maximum": max(errors), "median": float(np.median(errors))},
            "surrogate_monomials": int(len(delay.exponents)), "surrogate_retained_directions": int(scan.B.shape[1]),
            "null_fit": {"chi2": native_chi2, "dof": dof, "reduced_chi2": native_chi2 / dof,
                         "conditional_chi2_tail": float(chi2.sf(native_chi2, dof)),
                         "orbit_shifts_domain_units": dict(zip(orbit.parameters, map(float, best.x))),
                         "distance_to_domain_bound": margin, "optimizer_success": all(r.success for r in solutions),
                         "multistart_chi2_difference": float(abs(2 * solutions[0].cost - 2 * solutions[-1].cost)),
                         "fast_minus_native_chi2": fast_chi2 - native_chi2, "fast_unconverged": bool(fast_active[0]),
                         "fast_orbit_difference_maximum": float(np.max(np.abs(fast_x[0] - best.x)))},
            "joint_rank": rank, "joint_columns": int(joint.shape[1])}
        holds = [label for label, bad in [
            ("SURROGATE_ACCURACY", max(errors) > s["maximum_projected_whitened_error_norm"]),
            ("NULL_FIT_OPTIMIZER", not checks["null_fit"]["optimizer_success"] or checks["null_fit"]["fast_unconverged"]),
            ("NULL_FIT_MULTISTART", checks["null_fit"]["multistart_chi2_difference"] > scope["maximum_multistart_chi2_difference"]),
            ("NULL_FIT_ON_DOMAIN_BOUND", margin < scope["minimum_distance_to_domain_bound"]),
            ("FAST_NATIVE_NULL_DISAGREEMENT", abs(fast_chi2 - native_chi2) > scope["maximum_chi2_difference"]),
            ("RESIDUAL_SCATTER", checks["null_fit"]["conditional_chi2_tail"] < scope["adequacy_tail_cutoff"]),
            ("RANK", rank != joint.shape[1])] if bad]
        if holds:
            raise ValueError("Preparation holds: " + ", ".join(holds))
        names = state["nuisance_names"]
        baseline = nuisance[:, [i for i, n in enumerate(names) if n.lower().startswith(("offset", "dm", "jump"))]]
        policy = {**scope["policy"], "minimum_period_days": state["minimum_period"],
                  "maximum_period_days": min(2000.0, float(np.ptp(times)) / 2)}
        cal.validate_policy(policy)
        profile_dir = root / "profile"
        profile_dir.mkdir(exist_ok=False)
        np.savez_compressed(profile_dir / "arrays.npz", times=times, covariance=covariance, nuisance=nuisance, baseline=baseline,
                            frequencies=frequencies, surrogate_coefficients=delay.coefficients,
                            surrogate_exponents=delay.exponents, orbit_lower=orbit.lower, orbit_upper=orbit.upper)
        np.savez_compressed(out / "observed.npz", residuals=residuals)
        receipt = {"status": "NONLINEAR_PREPARATION_COMPATIBLE", "target": scope["target"], "toas": len(times),
                   "data_rows": len(residuals), "linear_nuisance_columns": int(nuisance.shape[1]),
                   "nonlinear_parameters": orbit.parameters, "parameter_domain_published_sigma": scope["parameter_domain_published_sigma"],
                   "orbit_lower": orbit.lower.tolist(), "orbit_upper": orbit.upper.tolist(), "frequency_grid": grid,
                   "noise_coverage": state["band"], "checks": checks, "inputs": state["inputs"],
                   "scope_sha256": cal.digest(out / "scope.json"), "observed_sha256": cal.digest(out / "observed.npz"),
                   "code": code_hashes(), "observed_outer_period_scan_executed": False, "created_utc": now()}
        cal.write(out / "receipt.json", receipt)
        cal.write(profile_dir / "profile.json", {
            "schema": "recherche-nonlinear-profile-v1", "target": scope["target"], "arrays": "arrays.npz",
            "arrays_sha256": cal.digest(profile_dir / "arrays.npz"), "reference_epoch_mjd_tdb": state["epoch"],
            "policy": policy, "injections": scope["injections"],
            "preparation_receipt_sha256": cal.digest(out / "receipt.json"),
            "statistic": "Orbit re-fitted under null and companion hypotheses at every period; linear nuisance profiled; fixed released noise",
            "observed_residuals_included": False})
        print(json.dumps({"status": receipt["status"], "checks": checks}), flush=True)
    except Exception as error:
        cal.write(out / "failure.json", {"status": "PREPARATION_FAILED", "error": str(error), "code": code_hashes()})
        raise


def calibrate(root):
    require(not (root / "calibration").exists(), "Calibration already exists; it is not repeated")
    profile, a, scan, linear, baseline = build(root)
    policy = profile["policy"]
    eligible, retained = cal.projection_map(linear, baseline, policy)
    require(eligible.any(), "No eligible period cell")
    out = root / "calibration"
    out.mkdir()
    cholesky = scan.L
    rows = len(cholesky)
    generator = np.random.default_rng(policy["seed"])
    maxima, linear_maxima = [], []
    unconverged = boundary = 0
    for index in range(policy["null_count"]):
        white = generator.standard_normal(rows)
        result = scan.scan(cholesky @ white)
        rhs = np.einsum("nfi,n->fi", linear.projected_whitened_templates, white)
        reference = np.einsum("fi,fij,fj->f", rhs, linear.template_gram_pseudoinverse, rhs)
        maxima.append(float(result["delta_chi2"][eligible].max()))
        linear_maxima.append(float(reference[eligible].max()))
        unconverged += int(result["unconverged"][eligible].sum())
        boundary += int(result["null_on_boundary"])
        if (index + 1) % 256 == 0:
            print(json.dumps({"nulls": index + 1, "running_maximum": max(maxima)}), flush=True)
    require(unconverged == 0, "Unconverged cells in the null calibration")
    alpha = policy["false_alarm_probability"]
    empirical = float(np.quantile(maxima, 1 - alpha, method="higher"))
    bound = float(2 * np.log(policy["search_count"] * len(eligible) / alpha))
    threshold = max(empirical, bound)
    best, worst = cal.sensitivity(linear, eligible, threshold, policy["detection_probability"])
    # Bounded injections at the linearised worst-phase amplitude, scored with the nonlinear statistic.
    inject = profile["injections"]
    indices = np.flatnonzero(eligible)
    chosen = indices[np.linspace(0, len(indices) - 1, inject["periods"]).astype(int)]
    generator = np.random.default_rng(policy["seed"] + 10000)
    times, epoch = a["times"], profile["reference_epoch_mjd_tdb"]
    recovered = trials = 0
    cases = []
    for cell in chosen:
        for phase in inject["phases_radians"]:
            signal = np.zeros(rows)
            signal[: len(times)] = worst[cell] * 1e-6 * np.sin(2 * np.pi * a["frequencies"][cell] * (times - epoch) + phase)
            hits = 0
            for _ in range(inject["realizations"]):
                result = scan.scan(signal + cholesky @ generator.standard_normal(rows))
                require(not result["unconverged"][cell], "Unconverged injection cell")
                hits += bool(result["delta_chi2"][cell] > threshold)
            cases.append({"period_days": float(1 / a["frequencies"][cell]), "phase_radians": phase,
                          "amplitude_us": float(worst[cell]), "recovered": hits, "trials": inject["realizations"]})
            recovered += hits
            trials += inject["realizations"]
    np.savez_compressed(out / "arrays.npz", frequencies=a["frequencies"], eligible=eligible, retained_power=retained,
                        null_maxima=maxima, linearised_null_maxima=linear_maxima,
                        best_phase_amplitude_us=best, worst_phase_amplitude_us=worst)
    result = {
        "status": "CALIBRATED", "target": profile["target"], "threshold": threshold, "empirical_quantile": empirical,
        "analytical_bound": bound, "threshold_rule": "max(empirical null quantile, union bound)",
        "linearised_empirical_quantile": float(np.quantile(linear_maxima, 1 - alpha, method="higher")),
        "false_alarm_probability": alpha, "search_count": policy["search_count"], "null_count": len(maxima), "seed": policy["seed"],
        "frequency_count": int(len(eligible)), "eligible_cells": int(eligible.sum()),
        "excluded_periods_days": [float(1 / f) for f in a["frequencies"][~eligible]],
        "null_fits_on_domain_bound": boundary,
        "median_worst_phase_amplitude_us": float(np.nanmedian(worst)),
        "median_best_phase_amplitude_us": float(np.nanmedian(best)),
        "sensitivity_scope": "Linearised-orbit amplitude for the requested detection probability at the nonlinear threshold",
        "injection_recovered": recovered, "injection_trials": trials, "injection_cases": cases,
        "injection_scope": "Bounded fixed-noise diagnostic at eligible periods; not occurrence completeness",
        "noise_assumption": "Gaussian with the fixed released covariance; orbit simulated at its published value",
        "profile_sha256": cal.digest(root / "profile/profile.json"), "arrays_sha256": cal.digest(out / "arrays.npz"),
        "code": code_hashes(), "observed_residuals_read": False, "created_utc": now()}
    cal.write(out / "calibration.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("code", "injection_cases", "excluded_periods_days")}), flush=True)


def freeze(root):
    require(not (root / "run01").exists(), "Consumed observed destination")
    path = root / "execution-freeze.json"
    require(not path.exists(), "Execution already frozen")
    calibration = cal.read(root / "calibration/calibration.json")
    require(calibration["status"] == "CALIBRATED" and calibration["code"] == code_hashes(), "Calibration or code differs")
    require(calibration["profile_sha256"] == cal.digest(root / "profile/profile.json"), "Profile differs")
    receipt = cal.read(root / "prepared/receipt.json")
    require(receipt["observed_sha256"] == cal.digest(root / "prepared/observed.npz"), "Observed residuals differ")
    cal.write(path, {"created_utc": now(), "target": calibration["target"], "threshold": calibration["threshold"],
                     "profile_sha256": calibration["profile_sha256"], "observed_sha256": receipt["observed_sha256"],
                     "calibration_sha256": cal.digest(root / "calibration/calibration.json"),
                     "calibration_arrays_sha256": calibration["arrays_sha256"], "code": code_hashes(),
                     "search": "One nonlinear-orbit circular outer-companion scan over eligible cells; single execution"})


def run(root):
    frozen = cal.read(root / "execution-freeze.json")
    require(frozen["code"] == code_hashes(), "Frozen code changed")
    require(frozen["profile_sha256"] == cal.digest(root / "profile/profile.json"), "Frozen profile changed")
    require(frozen["calibration_sha256"] == cal.digest(root / "calibration/calibration.json"), "Frozen calibration changed")
    require(frozen["observed_sha256"] == cal.digest(root / "prepared/observed.npz"), "Frozen observed residuals changed")
    out = root / "run01"
    out.mkdir(exist_ok=False)
    try:
        profile, a, scan, _, _ = build(root)
        with np.load(root / "calibration/arrays.npz") as z:
            eligible = z["eligible"]
        with np.load(root / "prepared/observed.npz") as z:
            residuals = z["residuals"]
        result = scan.scan(residuals)
        require(not result["unconverged"][eligible].any(), "Unconverged eligible cell")
        statistic = np.where(eligible, result["delta_chi2"], -np.inf)
        peak = int(np.argmax(statistic))
        np.savez_compressed(out / "periodogram.npz", frequencies=a["frequencies"], delta_chi2=result["delta_chi2"],
                            eligible=eligible, orbit=result["orbit"], template_coefficients=result["template_coefficients"])
        crossed = bool(statistic[peak] > frozen["threshold"])
        cal.write(out / "result.json", {
            "status": "PERIODIC_SIGNAL_CANDIDATE" if crossed else "NO_TRIGGER", "target": profile["target"],
            "peak_statistic": float(statistic[peak]), "peak_period_days": float(1 / a["frequencies"][peak]),
            "peak_amplitude_us": float(np.hypot(*result["template_coefficients"][peak]) * 1e6),
            "threshold": frozen["threshold"], "eligible_cells": int(eligible.sum()), "frequency_count": int(len(eligible)),
            "null_chi2": result["null_chi2"], "null_orbit_on_domain_bound": result["null_on_boundary"],
            "peak_orbit_on_domain_bound": bool(result["on_boundary"][peak]),
            "execution_freeze_sha256": cal.digest(root / "execution-freeze.json"),
            "periodogram_sha256": cal.digest(out / "periodogram.npz"), "completed_utc": now(),
            "interpretation": "A crossing is a candidate for review under fixed released noise, not a detection"})
        print((out / "result.json").read_text(), flush=True)
    except Exception as error:
        cal.write(out / "failure.json", {"status": "OBSERVED_EXECUTION_FAILED", "error": str(error)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "calibrate", "freeze", "run"])
    parser.add_argument("--root", type=Path, required=True, help="Target working folder inside the data root")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--scope", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "prepare":
        if not (args.data and args.scope):
            parser.error("prepare needs --data and --scope")
        prepare(args.data.resolve(), args.scope.resolve(), root)
    else:
        globals()[args.command](root)


if __name__ == "__main__":
    main()
