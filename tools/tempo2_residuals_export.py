"""Worker for tools/tempo2_compare.py: pre-fit residuals of a released par and tim file from native TEMPO2.

Runs inside the isolated TEMPO2 runtime (libstempo). No fit is performed.
"""
import argparse
import json
from pathlib import Path

import libstempo
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("par", type=Path)
    parser.add_argument("tim", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--maxobs", type=int, default=30000)
    a = parser.parse_args()
    if np.finfo(np.longdouble).nmant < 63:
        raise RuntimeError("Intel extended precision required")
    p = libstempo.tempopulsar(parfile=str(a.par), timfile=str(a.tim), dofit=False, warnings=True, maxobs=a.maxobs)
    residuals = p.residuals(removemean=True)
    np.savez_compressed(a.output, residuals=np.asarray(residuals, float), site_times=np.asarray(p.stoas, float),
                        barycentric_times=np.asarray(p.toas(), float), errors_us=np.asarray(p.toaerrs, float),
                        deleted=np.asarray(p.deleted, bool))
    a.output.with_suffix(".json").write_text(json.dumps({
        "target": p.name, "observations": int(p.nobs), "libstempo": libstempo.__version__, "clock": p.clock,
        "ephemeris": p.ephemeris, "binary_model": p.binarymodel if hasattr(p, "binarymodel") else None,
        "fit_performed": False}, indent=1) + "\n")
    print("TEMPO2_RESIDUALS_EXPORTED", p.name, p.nobs, flush=True)


if __name__ == "__main__":
    main()
