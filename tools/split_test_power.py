"""Power of a split (consistency) test of one periodic feature, on simulated data only.

A real companion moves the pulsar the same way at every radio frequency and
throughout the record. The split test fits the feature's sinusoid separately
in two parts of the data (two receivers, or the two halves of the record),
with the timing model shared, and asks whether the two parts agree:

    D = (bA - bB)' Cov(bA - bB)^-1 (bA - bB)        (chi-square, 2 d.o.f.)

A large D rejects "the same signal in both parts". This tool measures, for a
declared period, amplitude, split and noise models, how often D exceeds its
limit for

planet        the same sinusoid in both parts (should be the nominal rate),
fluke         noise only, drawn conditional on the whole-data fit showing the
              declared amplitude (what a noise fluctuation that produced the
              feature looks like), and
one part      a sinusoid present in one part only, scaled so the whole-data
              fit would show the declared amplitude.

It reads no observed residuals and runs no search.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.stats import chi2

LIMIT_PROBABILITY = 0.01


def estimator(covariance, design, signal):
    """(E, S): generalized-least-squares estimator of the signal coefficients (b = E y) and their covariance."""
    lower = cholesky(covariance, lower=True)
    columns = np.column_stack([design, signal])
    whitened = solve_triangular(lower, columns, lower=True)
    norm = np.linalg.norm(whitened, axis=0)
    q, r = np.linalg.qr(whitened / norm)
    if np.linalg.cond(r) > 1e10:
        raise ValueError("Split signal columns are not separable from the timing model")
    inverse = np.linalg.inv(r) / norm[:, None]
    rows = inverse[-signal.shape[1]:]
    return solve_triangular(lower, (rows @ q.T).T, lower=True, trans="T").T, rows @ rows.T


def evaluate(covariances, analysis, design, template, part, amplitude, count, seed, limit_probability=LIMIT_PROBABILITY):
    """covariances: name -> generating covariance; analysis: the covariance the test assumes.

    template: (rows, 2) cosine and sine columns of the feature; part: boolean per row, True for part A.
    """
    rows = len(template)
    split = np.column_stack([template * part[:, None], template * ~part[:, None]])
    e_split, s_split = estimator(analysis, design, split)
    e_common, s_common = estimator(analysis, design, template)
    contrast = np.hstack([np.eye(2), -np.eye(2)])
    weight = np.linalg.inv(contrast @ s_split @ contrast.T)
    limit = float(chi2.ppf(1 - limit_probability, 2))
    statistic = lambda y: np.einsum("in,ij,jn->n", contrast @ e_split @ y, weight, contrast @ e_split @ y)
    sigma = lambda s: float(np.sqrt(np.trace(s) / 2))
    out = {"limit": limit, "limit_probability": limit_probability, "amplitude_us": amplitude * 1e6,
           "amplitude_uncertainty_us": {"whole": sigma(s_common) * 1e6, "part_a": sigma(s_split[:2, :2]) * 1e6,
                                        "part_b": sigma(s_split[2:, 2:]) * 1e6}, "generators": {}}
    for index, (name, covariance) in enumerate(covariances.items()):
        rng = np.random.default_rng(seed + index)
        lower = cholesky(covariance, lower=True)
        noise = lower @ rng.standard_normal((rows, count))
        phase = rng.uniform(0, 2 * np.pi, count)
        unit = np.array([np.cos(phase), np.sin(phase)])                  # (2, count)
        wanted = amplitude * unit
        # Noise only, conditional on the whole-data coefficients equalling the declared amplitude.
        gain = covariance @ e_common.T @ np.linalg.inv(e_common @ covariance @ e_common.T)
        fluke = noise - gain @ (e_common @ noise - wanted)
        result = {"planet": noise + template @ wanted, "noise_fluke": fluke}
        for label, mask in (("part_a_only", part), ("part_b_only", ~part)):
            alone = template * mask[:, None]
            scale = np.linalg.inv(e_common @ alone)                      # so the whole-data fit shows `wanted`
            result[label] = noise + alone @ (scale @ wanted)
        row = {}
        for label, y in result.items():
            d = statistic(y)
            whole = e_common @ y
            row[label] = {"rejected_fraction": float(np.mean(d > limit)), "median_statistic": float(np.median(d)),
                          "whole_data_amplitude_us": float(np.median(np.hypot(*whole)) * 1e6)}
        d = statistic(noise)
        row["noise_unconditional"] = {"rejected_fraction": float(np.mean(d > limit)),
                                      "median_statistic": float(np.median(d))}
        out["generators"][name] = row
    return out


def main():
    import joint_noise_stage as stage
    import target_calibration as cal

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    data, config = args.data.resolve(), json.loads(args.config.read_text())
    source = data / config["source"]
    profile, a, _ = stage.nonlinear_source(source)
    times, n, rows = a["times"], len(a["times"]), len(a["covariance"])
    base = a["covariance"]
    backend = stage.tim_rows(data / config["tim"])[2]
    if len(backend) != n:
        raise ValueError("Tim file and prepared arrays differ in length")
    modes = stage.coverage.mode_plan(float(np.ptp(times)), profile["policy"]["minimum_period_days"], 1)["selected_modes"]
    stage.common.REFERENCE = profile["reference_epoch_mjd_tdb"]
    template = stage.common.template(times, np.array([config["period_days"]]), rows)[:, 0, :]

    def covariance(red):
        out = base.copy()
        if red is not None:
            out[:n, :n] += stage.mpta.red_covariance(times, red[0], red[1], modes)
        return out

    epochs = np.unique(np.round(times))
    middle = float(np.median(epochs))
    receiver = np.array([config["receiver_part_a"] in name for name in backend])
    splits = {"receiver": receiver, "time": np.round(times) <= middle}
    generators = {g["name"]: covariance(g["red"]) for g in config["generators"]}
    results = []
    for split, mask in splits.items():
        part = np.concatenate([mask, np.zeros(rows - n, bool)])
        for model in config["analysis_models"]:
            r = evaluate(generators, covariance(model["red"]), a["design"], template, part,
                         config["amplitude_us"] * 1e-6, config["count"], config["seed"])
            r.update({"split": split, "analysis_model": model["name"], "toas_part_a": int(mask.sum()),
                      "toas_part_b": int(n - mask.sum())})
            results.append(r)
            for name, row in r["generators"].items():
                print("%-8s analysis %-14s generator %-18s planet %.3f fluke %.3f A-only %.3f B-only %.3f" % (
                    split, model["name"], name, *(row[k]["rejected_fraction"] for k in (
                        "planet", "noise_fluke", "part_a_only", "part_b_only"))), flush=True)
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    args.out.write_text(json.dumps({
        "status": "SPLIT_TEST_POWER_COMPLETE", "target": config["target"], "observed_residuals_read": False,
        "config": config, "config_sha256": digest(args.config), "code_sha256": digest(__file__),
        "inputs": {"arrays": profile["arrays_sha256"], "tim": digest(data / config["tim"])},
        "time_split_last_epoch_of_part_a_mjd": middle, "red_modes": modes,
        "rule": "Shared timing model; cosine and sine of the declared period fitted separately in the two parts; "
                "D is the chi-square (2 d.o.f.) of the difference; rejected when above its %g quantile" % (
                    1 - LIMIT_PROBABILITY),
        "results": results}, indent=1) + "\n")


if __name__ == "__main__":
    main()
