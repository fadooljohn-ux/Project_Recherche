"""Check the linearised-orbit joint-noise statistic against the nonlinear orbit fit.

The second-stage statistic (joint_noise_stage) treats a nonlinear orbit as its
derivative columns at the published values. This tool measures what that costs:

simulate  for simulated vectors from every generator, re-fit the orbit
          nonlinearly at the noise members the linearised fit selected and
          report the change in the statistic. Reads no observed residuals.
observed  after the frozen run, repeat the whole family with the nonlinear
          orbit fit on the observed residuals, once, and compare.

The frozen decision statistic stays the linearised one; this is a validity
check with a declared tolerance, not a second search.
"""
import argparse
from pathlib import Path

import numpy as np

import joint_noise_stage as stage
import nonlinear_statistic as ns
import target_calibration as cal

TOLERANCE = 0.5


def setup(data, root):
    scope, a, contrast, _, templates = stage.load(data, root)
    if scope["source_kind"] != "nonlinear_orbit":
        raise ValueError("This check applies to nonlinear-orbit sources only")
    with np.load(data / scope["source"] / "profile/arrays.npz", allow_pickle=False) as z:
        p = {k: z[k] for k in z.files}
    dimension = len(p["orbit_lower"])
    full = ns.PolynomialDelay(p["surrogate_coefficients"], p["surrogate_exponents"], p["orbit_lower"], p["orbit_upper"])
    linear = ns.PolynomialDelay(p["surrogate_coefficients"][:, :dimension], p["surrogate_exponents"][:dimension],
                                p["orbit_lower"], p["orbit_upper"])
    periodic = ns.periodic_templates(a["times"], 1 / a["periods"], scope["reference_epoch"], len(a["base_covariance"]))
    return scope, a, contrast, templates, p["nuisance"], full, linear, periodic


def member_covariance(a, scope, pars):
    n = len(a["times"])
    covariance = a["base_covariance"].copy()
    covariance[:n, :n] += stage.variable_covariance(a, scope["coverage"]["selected_modes"], pars)
    return covariance


def fits(covariance, nuisance, delay, periodic, y):
    """Null chi-square and per-cell improvement with one orbit model."""
    result = ns.NonlinearScan(covariance, nuisance, delay, periodic).scan(y)
    return result["null_chi2"], result["delta_chi2"], bool(result["unconverged"].any())


def simulate(data, root, count, seed):
    out = root / "nonlinear-check-simulated.json"
    if out.exists():
        raise FileExistsError("Simulated check exists")
    scope, a, contrast, templates, nuisance, full, linear, periodic = setup(data, root)
    rng = np.random.default_rng(seed)
    rows = []
    for generator in scope["generators"]:
        draws = generator.get("samples") or [[generator["log10_amplitude"], generator["gamma"]]]
        for k in range(count):
            amplitude, gamma = draws[k % len(draws)]
            truth = {"log10_amplitude": amplitude, "gamma": gamma, "white_scale": generator["white_scale"]}
            y = np.linalg.cholesky(member_covariance(a, scope, truth)) @ rng.standard_normal(len(a["base_covariance"]))
            best, per_member = stage.profile_family(scope, a, contrast, templates, contrast.data(y)[:, None], "SIM")
            null_member, signal_member, cell = (int(best[key][0]) for key in ("null_member", "signal_member", "peak"))
            change, unconverged = {}, False
            for label, member in (("null", null_member), ("signal", signal_member)):
                covariance = member_covariance(a, scope, scope["family"][member])
                nl_null, nl_delta, bad = fits(covariance, nuisance, full, periodic, y)
                lin_null, lin_delta, _ = fits(covariance, nuisance, linear, periodic, y)
                unconverged |= bad
                change[label] = (nl_null - lin_null) if label == "null" else (
                    (nl_null - nl_delta[cell]) - (lin_null - lin_delta[cell]))
                if label == "signal":
                    # The linear surrogate inside the scan must reproduce the stage's own linearised score.
                    change["engine"] = float(np.max(np.abs(lin_delta - per_member[member][1])))
                    change["cells"] = float(np.max(np.abs(nl_delta - lin_delta)))
            rows.append({"generator": generator["name"], "linearised_statistic": float(best["statistic"][0]),
                         "nonlinear_minus_linearised": float(change["null"] - change["signal"]),
                         "largest_cell_difference_at_signal_member": change["cells"],
                         "scan_minus_stage_linearised_score": change["engine"], "unconverged": unconverged})
            print("SIMULATED", generator["name"], k + 1, rows[-1]["nonlinear_minus_linearised"], flush=True)
    worst = max(abs(r["nonlinear_minus_linearised"]) for r in rows)
    cal.write(out, {"status": "WITHIN_TOLERANCE" if worst <= TOLERANCE and not any(r["unconverged"] for r in rows) else "HOLD",
                    "tolerance": TOLERANCE, "largest_statistic_change": worst,
                    "largest_cell_difference": max(r["largest_cell_difference_at_signal_member"] for r in rows),
                    "largest_scan_minus_stage_linearised_score": max(r["scan_minus_stage_linearised_score"] for r in rows),
                    "vectors": len(rows), "seed": seed, "scope_sha256": cal.digest(root / "scope.json"),
                    "observed_residuals_read": False, "rows": rows})
    print("SIMULATED CHECK", worst, flush=True)


def observed(data, root):
    result = cal.read(root / "run01/result.json")
    out = root / "run01/nonlinear-check.json"
    if out.exists():
        raise FileExistsError("Observed nonlinear check exists; it runs once")
    scope, a, contrast, templates, nuisance, full, _, periodic = setup(data, root)
    y = np.load(data / scope["source"] / "prepared/observed.npz")["residuals"]
    nulls, signals, unconverged = [], [], 0
    for i, pars in enumerate(scope["family"]):
        extra = stage.variable_covariance(a, scope["coverage"]["selected_modes"], pars)
        determinant = 2 * np.log(np.diag(np.linalg.cholesky(contrast.covariance(extra)))).sum()
        null, delta, bad = fits(member_covariance(a, scope, pars), nuisance, full, periodic, y)
        nulls.append(determinant + null)
        signals.append(determinant + null - delta)
        unconverged += bad
        if (i + 1) % 10 == 0:
            print("OBSERVED member", i + 1, "/", len(scope["family"]), flush=True)
    signals = np.array(signals)
    member, cell = np.unravel_index(np.argmin(signals), signals.shape)
    statistic = float(min(nulls) - signals[member, cell])
    profile = min(nulls) - signals.min(axis=0)
    np.savez_compressed(root / "run01/nonlinear-periodogram.npz", periods=a["periods"], joint_statistic=profile)
    difference = statistic - result["peak_statistic"]
    cal.write(out, {
        "status": "CONSISTENT" if abs(difference) <= TOLERANCE and not unconverged else "INCONSISTENT",
        "tolerance": TOLERANCE, "nonlinear_joint_statistic": statistic, "linearised_joint_statistic": result["peak_statistic"],
        "nonlinear_minus_linearised": difference, "nonlinear_peak_period_days": float(a["periods"][cell]),
        "linearised_peak_period_days": result["peak_period_days"],
        "largest_cell_difference": float(np.max(np.abs(profile - np.load(root / "run01/periodogram.npz")["joint_statistic"]))),
        "null_noise": scope["family"][int(np.argmin(nulls))], "signal_noise": scope["family"][int(member)],
        "members_with_unconverged_cells": int(unconverged), "threshold": result["threshold"],
        "result_sha256": cal.digest(root / "run01/result.json"),
        "periodogram_sha256": cal.digest(root / "run01/nonlinear-periodogram.npz"),
        "scope": "Validity check of the linearised orbit; the frozen decision statistic is the linearised one"})
    print("OBSERVED CHECK", statistic, "linearised", result["peak_statistic"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["simulate", "observed"])
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--count", type=int, default=6, help="simulated vectors per generator")
    parser.add_argument("--seed", type=int, default=2026111850)
    args = parser.parse_args()
    if args.action == "simulate":
        simulate(args.data.resolve(), args.root.resolve(), args.count, args.seed)
    else:
        observed(args.data.resolve(), args.root.resolve())


if __name__ == "__main__":
    main()
