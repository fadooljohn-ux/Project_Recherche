import sys, json, copy, numpy as np
from pathlib import Path
sys.path.insert(0, "tools")
import joint_noise_stage as stage, joint_noise_sensitivity as sens
data = Path("../Project Recherche Data").resolve(); root = data / "joint-noise-chain-grid-20261118/j1453"
scope, a, contrast, _, templates = stage.load(data, root)
cells = sens.spread(a["periods"], 12)[:5]
out = {}
white = copy.deepcopy(scope); white["generators"] = [g for g in scope["generators"] if g["name"] == "released_white_only"]
variants = {"chain_bound_threshold_23.94": (white, 23.94)}
none = copy.deepcopy(white); none["family"] = [m for m in scope["family"] if m["log10_amplitude"] is None]
variants["white_only_family_threshold_21.45"] = (none, 21.45)
for name, (sc, thr) in variants.items():
    g = sens.curves(sc, a, contrast, templates, thr, cells, count=32, seed=5)
    out[name] = [(round(c["period_days"]), c["joint_over_ideal"]) for c in g[0]["cells"]]
    print(name, out[name], flush=True)
json.dump(out, open(sys.argv[1], "w"))
