"""Combined limit on companions across the saved isolated-pulsar searches.

Reads the saved sensitivity atlas (per-dataset 95% detection curves from the
fixed-noise searches) and reports, for a grid of period bins and minimum
masses,

covered     the effective number of pulsars in which such a companion would
            have been detected (sum over pulsars of the fraction of the bin
            where the pulsar's 95% curve is at or below the mass), and
upper limit the largest fraction of pulsars that could host such a companion
            and still give no detection in 95% of repetitions.

A `margin` multiplies every curve before the comparison: 1 takes the saved
fixed-noise curves as they stand; a larger value allows for the amplitude a
noise-fitting second stage needs. Datasets whose fixed-noise search crossed
its threshold are left out. Reads no observations and runs no search.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

BINS = [30, 60, 120, 240, 400, 1000, 2000]
MASSES = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000]
POINTS = 24          # log-spaced sample periods inside a bin
DETECTION = 0.95     # detection probability the saved curves are defined at
CONFIDENCE = 0.95


def pulsar_curves(curves, excluded_dispositions=("PERIODIC_SIGNAL_CANDIDATE",)):
    """Per pulsar: list of (period, minimum mass) arrays, eligible cells only, one per kept dataset."""
    out, dropped = {}, []
    for c in curves:
        if c["disposition"] in excluded_dispositions:
            dropped.append(c["record_id"])
            continue
        period = np.array(c["period_days"], float)
        mass = np.array([np.nan if v is None else v for v in c["worst_minimum_mass_earth"]], float)
        keep = np.array(c["eligible"], bool) & np.isfinite(mass)
        order = np.argsort(period[keep])
        out.setdefault(c["target"], []).append((period[keep][order], mass[keep][order]))
    return out, dropped


def best_mass(datasets, periods):
    """Smallest detectable minimum mass over a pulsar's datasets at each period; inf where none covers it."""
    best = np.full(len(periods), np.inf)
    for period, mass in datasets:
        if len(period) < 2:
            continue
        inside = (periods >= period[0]) & (periods <= period[-1])
        # Do not bridge a masked stretch wider than three grid steps (grids are even in frequency).
        step = np.median(-np.diff(1 / period))
        right = np.clip(np.searchsorted(period, periods), 1, len(period) - 1)
        inside &= 1 / period[right - 1] - 1 / period[right] <= 3 * step
        value = np.exp(np.interp(np.log(periods), np.log(period), np.log(mass)))
        best = np.where(inside, np.minimum(best, value), best)
    return best


def upper_limit(completeness, detection=DETECTION, confidence=CONFIDENCE):
    """Largest hosting fraction f with prod(1 - f * detection * c_i) >= 1 - confidence; None if above one."""
    p = detection * np.asarray(completeness, float)
    survive = lambda f: np.prod(1 - f * p)
    if survive(1.0) > 1 - confidence:
        return None
    low, high = 0.0, 1.0
    for _ in range(60):
        mid = (low + high) / 2
        low, high = (mid, high) if survive(mid) > 1 - confidence else (low, mid)
    return float(high)


def table(curves, margin, bins=BINS, masses=MASSES):
    pulsars, dropped = pulsar_curves(curves)
    rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        periods = np.exp(np.linspace(np.log(lo), np.log(hi), POINTS + 1))
        periods = np.sqrt(periods[:-1] * periods[1:])
        best = np.array([best_mass(d, periods) for d in pulsars.values()]) * margin
        for mass in masses:
            completeness = (best <= mass).mean(axis=1)
            rows.append({"period_min_days": lo, "period_max_days": hi, "minimum_mass_earth": mass,
                         "pulsars_with_any_coverage": int((completeness > 0).sum()),
                         "effective_pulsars": float(completeness.sum()),
                         "hosting_fraction_upper_limit_95": upper_limit(completeness)})
    return {"margin": margin, "pulsars": len(pulsars), "datasets_left_out": dropped, "cells": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas", type=Path, required=True, help="saved atlas.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--margins", type=float, nargs="+", default=[1.0, 3.0])
    parser.add_argument("--extra", type=Path, nargs="*", default=[],
                        help="further curve files in the atlas curve format (for example the binary searches)")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    atlas = json.loads(args.atlas.read_text())
    out = {
        "status": "POPULATION_LIMITS_COMPLETE", "atlas": str(args.atlas),
        "atlas_sha256": hashlib.sha256(args.atlas.read_bytes()).hexdigest(),
        "host_mass_solar": atlas["host_mass_solar"], "curve_definition": atlas["definition"],
        "rule": "Pulsar counted over the fraction of a period bin where margin times its 95% worst-phase curve is at "
                "or below the mass; hosting fraction f excluded when prod(1 - 0.95 f c_i) < 0.05",
        "observations_read": False,
        "limits": ["Minimum mass (m sin i) for a 1.4 solar-mass pulsar; true masses are larger",
                   "Circular orbits on the searched grids only",
                   "Margin 1 assumes each supplied noise model is correct",
                   "Pulsars were selected as isolated and by data quality, not at random",
                   "Datasets with a fixed-noise crossing are left out, not counted as detections or as clean"],
        "tables": [table(atlas["curves"], m) for m in args.margins]}
    if args.extra:
        files = [json.loads(path.read_text()) for path in args.extra]
        extra = [c for f in files for c in f["curves"]]
        out["extra"] = [{"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "host_mass_solar": f["host_mass_solar"], "curve_definition": f["definition"],
                         "curves": len(f["curves"])} for path, f in zip(args.extra, files)]
        out["tables_atlas_only"] = out["tables"]
        out["tables_extra_only"] = [table(extra, m) for m in args.margins]
        out["tables"] = [table(atlas["curves"] + extra, m) for m in args.margins]
        out["limits"][0] = ("Minimum mass (m sin i) for a 1.4 solar-mass pulsar (atlas) or the stated total inner "
                            "mass (extra files); true masses are larger")
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    for t in out.get("tables_extra_only", []) + out["tables"]:
        print("MARGIN", t["margin"], "pulsars", t["pulsars"], "left out", len(t["datasets_left_out"]))
        for c in t["cells"]:
            if c["minimum_mass_earth"] in (0.1, 1, 10, 100):
                limit = c["hosting_fraction_upper_limit_95"]
                print("  %5d-%-5d d  %6g Me  effective %6.1f  limit %s" % (
                    c["period_min_days"], c["period_max_days"], c["minimum_mass_earth"], c["effective_pulsars"],
                    "none" if limit is None else "%.1f%%" % (100 * limit)))


if __name__ == "__main__":
    main()
