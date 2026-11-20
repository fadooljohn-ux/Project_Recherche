"""Sensitivity curves of the MeerKAT binary searches, in the sensitivity-atlas curve format.

Reads the saved result.json and periodogram.npz of each searched target under
the given results/observed batch directories (MeerKAT, NANOGrav, Parkes or European binary batches) (95% worst-phase amplitude per
grid cell, from calibration) and converts amplitude to minimum mass for the
stated inner-system mass. Reads no timing data and runs no search.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import detection_limits

INNER_MASS_SOLAR = 1.6
DATASETS = {"mpta": "MPTA 4.5 yr", "ng15": "NANOGrav 15 yr wideband", "ppta": "PPTA DR3", "epta": "EPTA DR2full"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def curve(directory, inner_mass=INNER_MASS_SOLAR):
    directory = Path(directory)
    result = json.loads((directory / "result.json").read_text())
    if result["periodogram_sha256"] != digest(directory / "periodogram.npz"):
        raise ValueError("Periodogram does not match its result: " + str(directory))
    with np.load(directory / "periodogram.npz") as saved:
        period = 1 / np.asarray(saved["frequencies"], float)
        eligible = np.asarray(saved["eligible"], bool)
        amplitude = np.asarray(saved["worst_phase_amplitude_us"], float)
    mass = [detection_limits.minimum_mass_earth(a, p, inner_mass) if e and np.isfinite(a) else None
            for a, p, e in zip(amplitude, period, eligible)]
    return {"record_id": f"{directory.parent.name}-{result['target']}-run01", "target": result["target"],
            "dataset": DATASETS[directory.parent.name.split("-")[0]] + "; binary, outer-period search",
            "disposition": result["status"],
            "threshold": result["threshold"], "result_sha256": digest(directory / "result.json"),
            "periodogram_sha256": result["periodogram_sha256"], "host_mass_solar": inner_mass,
            "period_days": period.tolist(), "eligible": eligible.tolist(),
            "worst_amplitude_us": [None if not np.isfinite(a) else float(a) for a in amplitude],
            "worst_minimum_mass_earth": mass}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", type=Path, nargs="+", help="results/observed/mpta-binaryNN-… directories")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    curves = [curve(d.parent) for batch in args.batches for d in sorted(batch.glob("*/result.json"))]
    if len({c["record_id"] for c in curves}) != len(curves):
        raise ValueError("A search record appears twice")
    out = {"schema": "recherche-binary-curves-v1", "host_mass_solar": INNER_MASS_SOLAR,
           "definition": "95% detection probability on the search grid, circular outer orbit, worst phase, fixed "
                         "published noise, inner orbit and Shapiro freedom projected; minimum mass for the stated "
                         "total inner mass", "batches": [str(b) for b in args.batches], "curves": curves,
           "pulsars": len({c["target"] for c in curves}),
           "scientific_runs_executed": 0}
    args.out.write_text(json.dumps(out) + "\n")
    print("CURVES", len(curves), "pulsars", out["pulsars"])


if __name__ == "__main__":
    main()
