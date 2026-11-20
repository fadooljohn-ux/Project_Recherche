"""New engine functions against September's saved per-member observed objectives (chromatic-free members)."""
import json, sys
from pathlib import Path
import numpy as np
import joint_noise, joint_noise_stage as stage, j1453_review as common
data = Path(sys.argv[1]); repo = Path(sys.argv[2]); out = {}
for target, src in [("J1012+5307", "binary-pilot03-20260909/J1012+5307"), ("J1752-2806", "utmost-batch04-20260909/J1752-2806")]:
    root = data / "joint-noise-development-20260910" / target
    scope = json.loads((root / "scope.json").read_text())
    saved = json.loads((repo / "results/research/joint-noise-development-20260910" / target / "result.json").read_text())
    z = np.load(root / "inputs.npz"); n = len(z["times"])
    a = {"times": z["times"], "base_toa": z["base_covariance"][:n, :n]}
    y = np.load(data / src / "prepared/observed.npz")["residuals"]
    contrast = joint_noise.Contrast(z["base_covariance"], z["design"], n)
    common.REFERENCE = scope["reference_epoch"]
    full = common.template(z["times"], z["periods"], len(y))
    h = (contrast.B @ full.reshape(len(y), -1)).reshape(contrast.dimension, -1, 2)
    worst = 0.0; count = 0
    for record in saved["models"]:
        if record["chromatic_rms_us"]:
            continue
        pars = {"log10_amplitude": record["log10_amplitude"], "gamma": record["gamma"], "white_scale": 1.0}
        r = joint_noise.evaluate(contrast.covariance(stage.variable_covariance(a, scope["coverage"]["selected_modes"], pars)), h, contrast.data(y)[:, None])
        worst = max(worst, abs(r["null"][0] - record["observed_null_objective"]), abs(r["signal"][0] - record["observed_signal_objective"])); count += 1
    out[target] = {"members_compared": count, "largest_objective_difference": float(worst)}
print(json.dumps(out, indent=1))
