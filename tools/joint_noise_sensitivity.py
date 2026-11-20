"""Period-by-period sensitivity of a calibrated second-stage joint-noise test.

For every declared null generator and a set of trial periods spread evenly in
log period, report

ideal   the amplitude a test told the generator's true noise would detect half
        the time (its own 1% threshold over the same cells; analytic), and
joint   the amplitude the second-stage test detects half the time against its
        calibrated threshold, from injections scaled to that period.

The ratio joint / ideal is what fitting the noise costs at that period; the
ideal amplitude is what the noise itself costs. Simulated data only: this
reads no observed residuals and changes no threshold or statistic.
"""
import argparse
from pathlib import Path

import numpy as np

import joint_noise
import joint_noise_stage as stage
import target_calibration as cal

LADDER = [2 ** (k / 3) for k in range(-1, 13)]   # 0.79 to 16 times the ideal amplitude
LOCATED = 0.05


def half_detection(ladder, fractions):
    """Ladder value at which the detection fraction first reaches one half, interpolated in log amplitude."""
    hit = next((i for i, f in enumerate(fractions) if f >= 0.5), None)
    if hit is None:
        return None
    if hit == 0:
        return float(ladder[0])
    low, high = fractions[hit - 1], fractions[hit]
    weight = (0.5 - low) / (high - low)
    return float(np.exp(np.log(ladder[hit - 1]) + weight * np.log(ladder[hit] / ladder[hit - 1])))


def ideal(contrast, covariances, templates, cells, rng, nulls, alpha):
    """Known-noise 1% threshold and half-detection amplitude at each chosen cell.

    covariances: one per chain draw (one for an ordinary generator). The
    amplitude is the median across draws.
    """
    scores, amplitudes = [], []
    share = int(np.ceil(nulls / len(covariances)))
    grams = []
    for covariance in covariances:
        factor = np.linalg.cholesky(covariance)
        result = joint_noise.evaluate(covariance, templates, factor @ rng.standard_normal((contrast.dimension, share)))
        scores.append(result["score"].max(axis=0))
        z = np.linalg.solve(factor, templates[:, cells].reshape(contrast.dimension, -1)).reshape(contrast.dimension, -1, 2)
        grams.append(np.einsum("nfi,nfi->f", z, z) / 2)   # phase-averaged noncentrality per unit amplitude squared
    threshold = joint_noise.order_threshold(np.concatenate(scores), alpha)
    # A noncentral chi-square with two degrees of freedom has median near its noncentrality plus two.
    for gram in grams:
        amplitudes.append(np.sqrt(max(threshold - 2, 1.0) / gram))
    return float(threshold), np.median(amplitudes, axis=0)


def curves(scope, a, contrast, templates, threshold, cells, ladder=LADDER, count=32, seed=0, nulls=2048):
    """Injection columns for every generator, cell and ladder step; one family profile; half-detection amplitudes."""
    modes, dimension = scope["coverage"]["selected_modes"], scope.get("outside_dimension", 0)
    periods = a["periods"]
    batches, outside, layout, ideals = [], [], [], {}
    for gi, pars in enumerate(scope["generators"]):
        rng = np.random.default_rng(seed + 100 * gi)
        factors = stage.generator_factors(contrast, a, modes, pars)
        ideals[pars["name"]] = ideal(contrast, [f @ f.T for f in factors], templates, cells, rng, nulls, scope["alpha"])
        for j, cell in enumerate(cells):
            # The same noise and phases at every amplitude step, so steps differ only by amplitude.
            noise = stage.coloured(factors, rng, contrast.dimension, count)
            phases = rng.uniform(0, 2 * np.pi, count)
            unit = templates[:, cell] @ np.array([np.cos(phases), np.sin(phases)])
            outer = pars["white_scale"] ** 2 * rng.chisquare(dimension, count) if dimension else np.zeros(count)
            for step in ladder:
                batches.append(noise + step * ideals[pars["name"]][1][j] * unit)
                outside.append(outer)
                layout.append((pars["name"], j))
    best, _ = stage.profile_family(scope, a, contrast, templates, np.column_stack(batches), "SENSITIVITY",
                                   np.concatenate(outside) if dimension else None)
    detected = (best["statistic"] > threshold) & (
        abs(periods[best["peak"]] / np.repeat([periods[cells[j]] for _, j in layout], count) - 1) < LOCATED)
    fractions = detected.reshape(len(layout), count).mean(axis=1)
    out, cursor = [], 0
    for pars in scope["generators"]:
        own_threshold, amplitude = ideals[pars["name"]]
        rows = []
        for j, cell in enumerate(cells):
            part = fractions[cursor:cursor + len(ladder)].tolist()
            cursor += len(ladder)
            ratio = half_detection(ladder, part)
            rows.append({"period_days": float(periods[cell]), "ideal_amplitude_us": float(amplitude[j] * 1e6),
                         "joint_over_ideal": ratio,
                         "joint_amplitude_us": None if ratio is None else float(ratio * amplitude[j] * 1e6),
                         "at_or_below_ladder_start": bool(part[0] >= 0.5), "detection_fractions": part})
        out.append({"generator": pars["name"], "ideal_threshold": own_threshold, "cells": rows})
    return out


def spread(periods, count):
    """Indices of cells nearest to `count` periods evenly spaced in log period."""
    wanted = np.linspace(np.log(periods.min()), np.log(periods.max()), count)
    return np.unique(np.argmin(abs(np.log(periods)[:, None] - wanted[None]), axis=0))


def summary(generators):
    """Per period: the reference generator's amplitudes and the worst case over all generators."""
    reference, rows = generators[0], []
    for j, cell in enumerate(reference["cells"]):
        joint = [g["cells"][j]["joint_amplitude_us"] for g in generators]
        rows.append({"period_days": cell["period_days"], "reference_generator": reference["generator"],
                     "reference_ideal_amplitude_us": cell["ideal_amplitude_us"],
                     "reference_joint_amplitude_us": cell["joint_amplitude_us"],
                     "reference_joint_over_ideal": cell["joint_over_ideal"],
                     "largest_joint_amplitude_us": None if None in joint else max(joint),
                     "largest_joint_over_ideal": None if None in joint else max(
                         g["cells"][j]["joint_over_ideal"] for g in generators)})
    return rows


def run(data, root, periods, count, seed, retrospective):
    out = root / "sensitivity.json"
    if out.exists():
        raise FileExistsError("Sensitivity curve exists; do not repeat it")
    if (root / "execution-freeze.json").exists() and not retrospective:
        raise ValueError("Already frozen; a curve added afterwards must be declared with --retrospective")
    scope, a, contrast, _, templates = stage.load(data, root)
    calibration = cal.read(root / "calibration.json")
    if calibration["status"] != "JOINT_NOISE_CALIBRATED" or calibration["scope_sha256"] != cal.digest(root / "scope.json"):
        raise ValueError("Calibration is held or belongs to another scope")
    cells = spread(a["periods"], periods)
    generators = curves(scope, a, contrast, templates, calibration["threshold"], cells, count=count, seed=seed)
    cal.write(out, {
        "status": "SENSITIVITY_CURVE_COMPLETE", "target": scope["target"], "threshold": calibration["threshold"],
        "retrospective": retrospective, "detection_rule": "Joint statistic above the calibrated threshold with the "
        "highest cell within 5% of the injected period; half of the injections detected",
        "ideal_rule": "Known-noise test with the generator's own covariance and its own 1% threshold over the same cells",
        "ladder_times_ideal": LADDER, "injections_each_step": count, "seed": seed, "periods": len(cells),
        "summary": summary(generators), "generators": generators,
        "scope_sha256": cal.digest(root / "scope.json"), "calibration_sha256": cal.digest(root / "calibration.json"),
        "observed_residuals_read": False,
        "limits": "Half-detection amplitudes from a finite ladder and a finite number of injections; conditional on "
                  "the declared generators; not an upper limit on any companion"})
    for row in cal.read(out)["summary"]:
        print("SENSITIVITY %8.1f d  ideal %s us  joint %s us  ratio %s  worst generator %s us" % (
            row["period_days"], *(("%.3f" % v if v is not None else "above ladder") for v in (
                row["reference_ideal_amplitude_us"], row["reference_joint_amplitude_us"],
                row["reference_joint_over_ideal"], row["largest_joint_amplitude_us"]))), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--periods", type=int, default=12)
    parser.add_argument("--count", type=int, default=32, help="injections per amplitude step")
    parser.add_argument("--seed", type=int, default=2026111900)
    parser.add_argument("--retrospective", action="store_true", help="curve for an already frozen or consumed root")
    args = parser.parse_args()
    run(args.data.resolve(), args.root.resolve(), args.periods, args.count, args.seed, args.retrospective)


if __name__ == "__main__":
    main()
