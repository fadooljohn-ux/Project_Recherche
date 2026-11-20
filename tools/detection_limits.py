"""Detection limits from second-stage sensitivity curves.

For each sensitivity.json: at every trial period, the amplitude the second-stage
test detects in 50% and in 95% of simulated injections, for the first-listed
generator and the largest over all declared generators, and the minimum
companion mass (m sin i, circular orbit) that amplitude corresponds to.

Reads sensitivity curves only (simulated data). A limit is conditional on the
declared noise generators and applies only where the observed run was below
threshold; it is not a posterior upper limit.
"""
import argparse
import json
from pathlib import Path

import numpy as np

G, C, SOLAR, EARTH, DAY = 6.6743e-11, 299792458.0, 1.98841e30, 5.9722e24, 86400.0


def crossing(ladder, fractions, level):
    """Ladder value where the detection fraction first reaches `level`, interpolated in log amplitude."""
    hit = next((i for i, f in enumerate(fractions) if f >= level), None)
    if hit is None:
        return None
    if hit == 0:
        return float(ladder[0])
    low, high = fractions[hit - 1], fractions[hit]
    return float(np.exp(np.log(ladder[hit - 1]) + (level - low) / (high - low) * np.log(ladder[hit] / ladder[hit - 1])))


def minimum_mass_earth(amplitude_us, period_days, pulsar_solar):
    """m sin i of a light circular companion giving this timing amplitude."""
    mass = pulsar_solar * SOLAR
    return float(amplitude_us * 1e-6 * C * mass ** (2 / 3)
                 * (4 * np.pi ** 2 / (G * (period_days * DAY) ** 2)) ** (1 / 3) / EARTH)


def limits(sensitivity, pulsar_solar):
    ladder, rows = sensitivity["ladder_times_ideal"], []
    for j, cell in enumerate(sensitivity["generators"][0]["cells"]):
        row = {"period_days": cell["period_days"]}
        for level, label in ((0.5, "50"), (0.95, "95")):
            each = []
            for g in sensitivity["generators"]:
                c = g["cells"][j]
                ratio = crossing(ladder, c["detection_fractions"], level)
                each.append(None if ratio is None else ratio * c["ideal_amplitude_us"])
            for name, value in (("reference", each[0]), ("largest", None if None in each else max(each))):
                row["%s_amplitude_%s_us" % (name, label)] = value
                row["%s_minimum_mass_%s_earth" % (name, label)] = (
                    None if value is None else minimum_mass_earth(value, cell["period_days"], pulsar_solar))
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pulsar-mass", type=float, default=1.4, help="solar masses (inner binary total for a binary)")
    parser.add_argument("curves", nargs="+", type=Path)
    args = parser.parse_args()
    out = {"pulsar_mass_solar": args.pulsar_mass, "targets": []}
    for path in args.curves:
        s = json.loads(path.read_text())
        out["targets"].append({"target": s["target"], "curve": str(path), "threshold": s["threshold"],
                               "injections_each_step": s["injections_each_step"], "retrospective": s["retrospective"],
                               "reference_generator": s["generators"][0]["generator"], "limits": limits(s, args.pulsar_mass)})
    out["limits"] = ("Detection probabilities from a finite ladder and a finite number of simulated injections; "
                     "conditional on the declared generators; circular orbits; not a posterior upper limit")
    args.out.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
