"""Load the native model through the repository loader (network denied) and save per-TOA metadata. Read-only on inputs."""
from contextlib import ExitStack
import json, sys
from pathlib import Path
import numpy as np
from common import *
import nonlinear_verification as verification
import target_calibration as cal

REPO = Path(".")
scope = cal.read(REPO / "config/j2043-nonlinear-calibration.json")
out = HERE / "loadout"; out.mkdir(exist_ok=True)
with ExitStack() as stack:
    s = verification.load(HERE.parent, scope, out, stack)
    toas, model = s["toas"], s["model"]
    from pint.residuals import WidebandTOAResiduals
    res = np.asarray(WidebandTOAResiduals(toas, model).calc_wideband_resids(), float)
    flags = {k: np.array([str(f.get(k, "")) for f in toas.table["flags"]]) for k in ("fe", "be", "f", "pp_dm", "pp_dme", "snr", "tobs", "name")}
    orb = np.asarray(model.orbital_phase(toas, anom="mean", radians=False), float) if hasattr(model, "orbital_phase") else np.zeros(len(res)//2)
    dmx = {}
    for p in model.params:
        if p.startswith("DMXR1_"):
            i = p.split("_")[1]
            dmx[i] = [float(getattr(model, "DMXR1_" + i).value), float(getattr(model, "DMXR2_" + i).value),
                      float(getattr(model, "DMX_" + i).value), float(getattr(model, "DMX_" + i).uncertainty_value)]
    np.savez(HERE / "meta.npz", names=np.array(s["nuisance_names"]), tdb=s["times"],
             mjd=np.asarray(toas.get_mjds().value, float), freq=np.asarray(toas.table["freq"].data, float),
             err_us=np.asarray(toas.table["error"].data, float), obs=np.array([str(o) for o in toas.table["obs"]]),
             orbphase=orb, residuals=res, cov_check=s["covariance"],
             dmx=np.array([[int(k)] + v for k, v in sorted(dmx.items())]), **{"flag_" + k: v for k, v in flags.items()})
    a = arrays()
    print(json.dumps({"n": len(s["times"]), "resid_max_abs_diff_vs_saved": float(np.max(np.abs(res - a["residuals"]))),
                      "cov_max_abs_diff": float(np.max(np.abs(s["covariance"] - a["covariance"]))),
                      "nuis_max_rel_diff": float(np.max(np.abs(s["nuisance"] - a["nuisance"]) / (np.abs(a["nuisance"]).max(axis=0)))),
                      "network_attempts": len(s["deny"].attempts), "names": s["nuisance_names"][:14], "n_dmx": len(dmx),
                      "components": list(model.components)}, indent=1))
