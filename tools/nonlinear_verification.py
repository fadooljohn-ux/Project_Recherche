"""Synthetic verification and cost benchmark of the nonlinear statistic. Never a planet search.

Simulated data only: the observed residual vector is not scanned, no threshold
is calibrated and no operational profile is written.
"""

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import least_squares
import binary_noise_coverage as coverage
import binary_wideband as binary
import nonlinear_statistic as ns
import target_calibration as cal
from j1857_nonlinear import NativeOrbit, ProjectedFit
from recherche_common import require
from pulsar_pilot.pilot1_runtime import build_search_frequency_grid
from pulsar_pilot.pilot2_offline_resources import NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase


class BoundedOrbit(NativeOrbit):
    """NativeOrbit whose box is cut at declared physical floors instead of being refused.

    floors may give a smallest companion mass "M2" (solar masses) and a smallest "COSI".
    Without floors the behaviour is NativeOrbit's.
    """

    def __init__(self, model, toas, parameters, extent, floors=None):
        floors = floors or {}
        mass, sigma = float(model.M2.value), float(model.M2.uncertainty_value)
        shrink = "M2" in floors and mass - extent * sigma < floors["M2"]
        if shrink:
            # Let the parent accept the box, then restore the published scale and cut the lower bound.
            model.M2.uncertainty_value = (mass - floors["M2"]) / extent * (1 - 1e-12)
        try:
            super().__init__(model, toas, parameters, extent)
        finally:
            model.M2.uncertainty_value = sigma
        if shrink:
            k = parameters.index("M2")
            self.scales["M2"] = np.longdouble(sigma)
            self.lower[k] = (floors["M2"] - mass) / sigma
        if "COSI" in floors:
            k = parameters.index("SINI")
            self.lower[k] = max(self.lower[k], float((floors["COSI"] - self.cos0) / self.cos_scale))
        require(np.all(self.lower < 0) and np.all(self.upper > 0), "Published orbit outside the declared domain")


def load(data, scope, out, stack):
    """Native model, linear nuisance design, covariance and orbit, as in the compatibility prototype."""
    import pint.logging
    from pint.fitter import WidebandTOAFitter
    from pint.models import get_model_and_toas
    target = scope["target"]
    source = data / scope["source_batch"]
    row, = [r for r in cal.read(source / "selection.json")["rows"] if r["target"] == target]
    par, tim = [source / target / "original" / f"{target}.{s}" for s in ("par", "tim")]
    for suffix, path in (("par", par), ("tim", tim)):
        require(cal.digest(path) == row[suffix + "_sha256"], "Original input binding differs")
    pint.logging.setup(level="WARNING", sink=out / "pint.log", removeprior=True)
    deny = stack.enter_context(NetworkDeny())
    stack.enter_context(binary.BinaryResources(source)).bind_science_resources()
    model, toas = get_model_and_toas(par, tim, ephem="DE440", include_bipm=True, bipm_version="BIPM2019",
                                     planets=True, usepickle=False, limits="error")
    bind_precise_spin_phase(model)
    binary.bind_ell1_derivative(model)
    require(model.BINARY.value == "ELL1", "Native ELL1 model required")
    minimum = max(30.0, 10 * float(model.PB.value))
    band = coverage.configure(model, toas, minimum)
    fitter = WidebandTOAFitter(toas, model)
    matrix = fitter.get_designmatrix()
    names = matrix.get_label_names(axis=1)
    require(set(scope["orbital_parameters"]).issubset(names), "Orbital terms missing from native timing design")
    keep = [i for i, p in enumerate(names) if p not in scope["orbital_parameters"]]
    nuisance = matrix.matrix[:, keep]
    covariance = fitter.get_noise_covariancematrix().matrix
    orbit = BoundedOrbit(model, toas, scope["orbital_parameters"], scope["parameter_domain_published_sigma"],
                         scope.get("physical_floors"))
    times = np.asarray(toas.table["tdbld"].data, float)
    return {"deny": deny, "model": model, "toas": toas, "nuisance_names": [names[i] for i in keep], "nuisance": nuisance, "covariance": covariance, "orbit": orbit,
            "times": times, "epoch": float(model.PEPOCH.value), "minimum_period": minimum, "band": band,
            "inputs": {"par_sha256": cal.digest(par), "tim_sha256": cal.digest(tim),
                       "selection_sha256": cal.digest(source / "selection.json")}}


def surrogate_exponents(scope, parameters):
    """Monomials named by a surrogate scope; an optional pair of parameters gets higher-order terms."""
    surrogate = scope["surrogate"]
    if "pair" not in surrogate:
        return ns.monomial_exponents(len(parameters), surrogate["degree"])
    pair = [parameters.index(p) for p in surrogate["pair"]]
    return ns.extended_exponents(len(parameters), surrogate["degree"], pair, surrogate["pair_degree"])


def native_chi2(covariance, design, data, orbit, starts, limit):
    """Reference: profile the native delay with a bounded least-squares fit from each declared start."""
    fit = ProjectedFit(covariance, design, data, orbit)
    solutions = [least_squares(fit.residual, start, jac=fit.jacobian, bounds=(orbit.lower, orbit.upper),
                               max_nfev=limit, ftol=1e-12, xtol=1e-12, gtol=1e-10) for start in starts]
    best = min(solutions, key=lambda s: s.cost)
    return 2 * best.cost, best.x, sum(s.nfev for s in solutions)


def execute(args, out, scope):
    holds, started = [], time.monotonic()
    with ExitStack() as stack:
        state = load(args.data, scope, out, stack)
        orbit, covariance, nuisance, times = state["orbit"], state["covariance"], state["nuisance"], state["times"]
        rows, toa_count, dimension = len(covariance), len(times), len(orbit.parameters)

        # A. Polynomial surrogate of the native delay, checked on points it was not fitted to.
        surrogate_scope = scope["surrogate"]
        clock = time.monotonic()
        train = ns.sample_domain(orbit.lower, orbit.upper, surrogate_scope["training_points"], surrogate_scope["training_seed"])
        delay = ns.PolynomialDelay.fit(lambda x: np.asarray(orbit.delay(x), float), orbit.lower, orbit.upper,
                                       surrogate_scope["degree"], train, surrogate_exponents(scope, orbit.parameters))
        native_seconds = (time.monotonic() - clock) / len(train)
        frequencies, grid = build_search_frequency_grid(
            times, state["minimum_period"], min(2000.0, float(np.ptp(times)) / 2), scope["oversampling"])
        templates = ns.periodic_templates(times, frequencies, state["epoch"], rows)
        clock = time.monotonic()
        scan = ns.NonlinearScan(covariance, nuisance, delay, templates)
        setup_seconds = time.monotonic() - clock
        test = np.random.default_rng(surrogate_scope["validation_seed"]).uniform(
            orbit.lower, orbit.upper, size=(surrogate_scope["validation_points"], dimension))
        errors = [float(np.linalg.norm(scan.project(np.asarray(orbit.delay(x), float) - delay(x)))) for x in test]
        fitted = [float(np.linalg.norm(scan.project(np.asarray(orbit.delay(x), float) - delay(x)))) for x in train[:20]]
        surrogate = {**surrogate_scope, "monomials": int(len(delay.exponents)), "retained_directions": int(scan.B.shape[1]),
                     "discarded_surrogate_norm": scan.discarded_surrogate_norm,
                     "validation_projected_whitened_error_norm": {"maximum": max(errors), "median": float(np.median(errors))},
                     "training_projected_whitened_error_norm_maximum": max(fitted),
                     "native_delay_seconds_per_evaluation": native_seconds}
        if max(errors) > surrogate_scope["maximum_projected_whitened_error_norm"]:
            holds.append("SURROGATE_ACCURACY")
        print(json.dumps({"stage": "surrogate", **surrogate}), flush=True)

        linear = ns.NonlinearScan(
            covariance, nuisance,
            ns.PolynomialDelay(delay.coefficients[:, :dimension], delay.exponents[:dimension],
                               np.full(dimension, -1e9), np.full(dimension, 1e9)), templates)
        cholesky = scan.L
        sine = lambda period, phase: np.concatenate(  # noqa: E731 - a two-line waveform helper
            [np.sin(2 * np.pi * (times - state["epoch"]) / period + phase), np.zeros(rows - toa_count)])

        # B. The fast statistic against the native reference on a few simulated vectors and periods.
        reference_scope = scope["reference"]
        generator = np.random.default_rng(reference_scope["seed"])
        starts = []
        for value in reference_scope["optimizer_starts"]:
            start = np.zeros(dimension)
            start[-1] = value
            starts.append(start)
        cells = [int(np.argmin(np.abs(1 / frequencies - p))) for p in reference_scope["periods_days"]]
        comparisons, reference_evaluations = [], 0
        for index in range(reference_scope["vectors"]):
            amplitude = reference_scope["amplitudes_us"][index % len(reference_scope["amplitudes_us"])]
            period = reference_scope["periods_days"][index % len(reference_scope["periods_days"])]
            data = cholesky @ generator.standard_normal(rows) + amplitude * 1e-6 * sine(period, generator.uniform(0, 2 * np.pi))
            fast = scan.scan(data)
            null, _, count = native_chi2(covariance, nuisance, data, orbit, starts, reference_scope["maximum_function_evaluations"])
            reference_evaluations += count
            for cell in cells:
                design = np.column_stack([nuisance, templates[:, cell]])
                alternative, _, count = native_chi2(covariance, design, data, orbit, starts,
                                                    reference_scope["maximum_function_evaluations"])
                reference_evaluations += count
                comparisons.append({"vector": index, "injected_amplitude_us": amplitude, "period_days": float(1 / frequencies[cell]),
                                    "native_delta_chi2": null - alternative, "fast_delta_chi2": float(fast["delta_chi2"][cell]),
                                    "null_chi2_difference": float(fast["null_chi2"] - null)})
        worst = max(abs(c["native_delta_chi2"] - c["fast_delta_chi2"]) for c in comparisons)
        worst_null = max(abs(c["null_chi2_difference"]) for c in comparisons)
        reference = {**reference_scope, "comparisons": comparisons, "maximum_delta_chi2_difference": worst,
                     "maximum_null_chi2_difference": worst_null, "native_function_evaluations": reference_evaluations}
        if max(worst, worst_null) > reference_scope["maximum_chi2_difference"]:
            holds.append("NATIVE_REFERENCE_DISAGREEMENT")
        print(json.dumps({"stage": "reference", "maximum_delta_chi2_difference": worst,
                          "maximum_null_chi2_difference": worst_null}), flush=True)

        # C. Simulated nulls over the full grid, with the linearised statistic alongside.
        null_scope = scope["nulls"]
        generator = np.random.default_rng(null_scope["seed"])
        maxima, linear_maxima, means, differences = [], [], [], []
        unconverged = boundary = null_boundary = 0
        iterations = []
        bound_hits = np.zeros(dimension, int)
        scan_seconds = 0.0
        for _ in range(null_scope["count"]):
            data = cholesky @ generator.standard_normal(rows)
            tick = time.monotonic()
            result = scan.scan(data)
            scan_seconds += time.monotonic() - tick
            reference_linear = linear.scan(data)["delta_chi2"]
            maxima.append(float(result["delta_chi2"].max()))
            linear_maxima.append(float(reference_linear.max()))
            means.append(float(result["delta_chi2"].mean()))
            differences.append(float(np.max(np.abs(result["delta_chi2"] - reference_linear))))
            unconverged += int(result["unconverged"].sum())
            boundary += int(result["on_boundary"].sum())
            null_boundary += int(result["null_on_boundary"])
            bound_hits += np.minimum(result["null_orbit"] - orbit.lower, orbit.upper - result["null_orbit"]) < 1e-6
            iterations.append(int(result["iterations"].max()))
            require(result["delta_chi2"].min() > -1e-6, "Negative statistic")
        cells_total = null_scope["count"] * len(frequencies)
        nulls = {**null_scope, "frequency_count": int(len(frequencies)),
                 "mean_cell_statistic": float(np.mean(means)),
                 "maximum_statistic_quantiles": {str(q): float(np.quantile(maxima, q)) for q in (0.5, 0.9, 0.99)},
                 "linearised_maximum_statistic_quantiles": {str(q): float(np.quantile(linear_maxima, q)) for q in (0.5, 0.9, 0.99)},
                 "maximum_difference_from_linearised": {"median": float(np.median(differences)), "maximum": float(np.max(differences))},
                 "unconverged_cells": unconverged, "boundary_cell_fraction": boundary / cells_total,
                 "null_fit_boundary_fraction": null_boundary / null_scope["count"],
                 "null_fit_boundary_hits_by_parameter": dict(zip(orbit.parameters, bound_hits.tolist())),
                 "maximum_iterations_used": int(max(iterations)),
                 "seconds_per_vector": scan_seconds / null_scope["count"],
                 "statistical_meaning": "Simulation diagnostics only; no threshold or false-alarm probability is set"}
        if unconverged:
            holds.append("UNCONVERGED_CELLS")
        low, high = null_scope["mean_cell_statistic_range"]
        if not low <= nulls["mean_cell_statistic"] <= high:
            holds.append("NULL_CELL_MEAN_OUTSIDE_RANGE")
        if nulls["boundary_cell_fraction"] > null_scope["maximum_boundary_cell_fraction"]:
            holds.append("ORBIT_DOMAIN_BOUNDARY")
        print(json.dumps({"stage": "nulls", **{k: nulls[k] for k in (
            "mean_cell_statistic", "maximum_statistic_quantiles", "maximum_difference_from_linearised",
            "unconverged_cells", "boundary_cell_fraction", "seconds_per_vector")}}), flush=True)

        # D. Injected sinusoids: is the period found and the amplitude recovered?
        injection_scope = scope["injections"]
        generator = np.random.default_rng(injection_scope["seed"])
        orbital = linear.project(delay.coefficients[:, :dimension])
        orbital_basis, _ = np.linalg.qr(orbital)
        injections = []
        for period in injection_scope["periods_days"]:
            for noncentrality in injection_scope["noncentralities"]:
                for _ in range(injection_scope["phases_per_case"]):
                    phase = generator.uniform(0, 2 * np.pi)
                    unit = scan.project(1e-6 * sine(period, phase))
                    unit = unit - orbital_basis @ (orbital_basis.T @ unit)
                    # Amplitude chosen so the linearised expected noncentrality equals the declared value.
                    amplitude = float(np.sqrt(noncentrality / (unit @ unit)))
                    signal = amplitude * 1e-6 * sine(period, phase)
                    result = scan.scan(cholesky @ generator.standard_normal(rows) + signal)
                    peak = int(np.argmax(result["delta_chi2"]))
                    injections.append({
                        "period_days": period, "amplitude_us": amplitude, "phase_radians": float(phase),
                        "expected_noncentrality": noncentrality,
                        "peak_period_days": float(1 / frequencies[peak]), "peak_statistic": float(result["delta_chi2"][peak]),
                        "peak_frequency_offset_cells": float(abs(frequencies[peak] - 1 / period) / grid["frequency_step_per_day"]),
                        "recovered_amplitude_us": float(np.hypot(*result["template_coefficients"][peak]) * 1e6),
                        "unconverged_cells": int(result["unconverged"].sum())})
        strong = [r for r in injections if r["expected_noncentrality"] >= injection_scope["strong_noncentrality"]]
        excess = [r["peak_statistic"] - r["expected_noncentrality"] for r in injections]
        located = [r for r in strong if r["peak_frequency_offset_cells"] <= injection_scope["maximum_peak_offset_cells"]]
        bias = [r["recovered_amplitude_us"] / r["amplitude_us"] - 1 for r in located]
        injection = {**injection_scope, "cases": injections, "strong_cases": len(strong), "strong_cases_located": len(located),
                     "median_amplitude_bias_of_located": float(np.median(bias)) if bias else None,
                     "mean_peak_statistic_minus_noncentrality": float(np.mean(excess)),
                     "statistical_meaning": "Bounded numerical check, not a detection probability or sensitivity curve"}
        if len(strong) < injection_scope["minimum_strong_cases"]:
            holds.append("TOO_FEW_STRONG_INJECTIONS")
        elif len(located) / len(strong) < injection_scope["minimum_located_fraction"]:
            holds.append("INJECTION_PERIOD_RECOVERY")
        if bias and abs(injection["median_amplitude_bias_of_located"]) > injection_scope["maximum_median_amplitude_bias"]:
            holds.append("INJECTION_AMPLITUDE_BIAS")
        if any(r["unconverged_cells"] for r in injections):
            holds.append("UNCONVERGED_INJECTION_CELLS")
        print(json.dumps({"stage": "injections", "strong": len(strong), "located": len(located),
                          "median_amplitude_bias": injection["median_amplitude_bias_of_located"]}), flush=True)
        require(not state["deny"].attempts, "Scientific network access attempted")

    # E. Cost of a later calibration with this statistic, extrapolated from the measured rate.
    cost_scope = scope["cost_projection"]
    per_vector = nulls["seconds_per_vector"]
    cost = {"native_delay_seconds_per_evaluation": native_seconds, "surrogate_setup_seconds": setup_seconds,
            "seconds_per_simulated_vector": per_vector,
            "projected_seconds_for_null_calibration": per_vector * cost_scope["null_count"],
            "projected_seconds_for_injection_set": per_vector * cost_scope["injection_count"],
            "native_seconds_for_same_null_calibration_estimate":
                native_seconds * reference["native_function_evaluations"] / max(1, len(comparisons)) * len(frequencies) * cost_scope["null_count"],
            **cost_scope, "elapsed_seconds_this_run": time.monotonic() - started}
    np.savez_compressed(out / "arrays.npz", frequencies=frequencies, null_maxima=maxima, linearised_null_maxima=linear_maxima,
                        surrogate_coefficients=delay.coefficients, surrogate_exponents=delay.exponents,
                        orbit_lower=orbit.lower, orbit_upper=orbit.upper)
    result = {"target": scope["target"], "status": "NONLINEAR_STATISTIC_HOLD" if holds else "NONLINEAR_STATISTIC_VERIFIED",
              "holds": holds, "toas": toa_count, "data_rows": rows, "linear_nuisance_columns": int(nuisance.shape[1]),
              "nonlinear_parameters": orbit.parameters, "frequency_grid": grid, "noise_coverage": state["band"],
              "surrogate": surrogate, "reference": reference, "nulls": nulls, "injections": injection, "cost": cost,
              "scope_sha256": cal.digest(args.scope), "inputs": state["inputs"],
              "code": {Path(p).name: cal.digest(p) for p in (__file__, ns.__file__, binary.__file__, coverage.__file__,
                                                             str(Path(__file__).with_name("j1857_nonlinear.py")))},
              "observed_residual_vector_scanned": False, "calibration_executed": False,
              "observed_outer_period_scan_executed": False, "operational_profile_created": False,
              "limits": "Simulated Gaussian data under the fixed released covariance, generated at the published orbit. "
                        "Verifies the numerical statistic and its cost only; it sets no threshold, mask or sensitivity "
                        "and is not general nonlinear-binary qualification."}
    cal.write(out / "receipt.json", result)
    print(json.dumps({"status": result["status"], "holds": holds, "cost": cost}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    scope = cal.read(args.scope)
    cal.write(args.output / "scope.json", scope)
    try:
        execute(args, args.output, scope)
    except Exception as error:
        cal.write(args.output / "failure.json", {"status": "VERIFICATION_EXECUTION_FAILED", "error": str(error),
                                                  "script_sha256": cal.digest(__file__)})
        raise


if __name__ == "__main__":
    main()
