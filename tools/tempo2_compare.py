"""Compare the search's prepared residuals with native TEMPO2 for released binary models.

The Parkes and European releases write most orbits in tempo2's general `T2`
model. The search loads them through a translation (and, where applicable,
a Shapiro re-centring, a re-expression and a refinement) into the timing
library it uses. This tool checks that chain against tempo2 itself: for
each prepared target it obtains tempo2's pre-fit residuals from the
ORIGINAL released par and tim files, subtracts them from the residuals the
preparation produced, and measures what is left after the projection the
search applies (every timing, dispersion, instrumental and orbital column,
under the search covariance).

    pass: the largest remaining difference is at most 0.1 TOA sigma
          (the bound used for the re-expression and local-linearity checks)

It uses preparation products and tempo2 residuals only: no periodogram is
computed and nothing is calibrated or searched.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np

import orbit_reexpress as reexpress
import target_calibration as cal

REPO = Path(__file__).resolve().parents[1]
LIMIT = reexpress.EQUIVALENCE_LIMIT
RUNTIME = "ipta-adapter01-20260909/runtime"
# Site arrival times are UTC; prepared times are TDB at the observatory. Their difference is TT-UTC plus
# periodic terms: between 60 and 75 seconds for data after 1999.
OFFSET_SECONDS = (60.0, 75.0)


def bound_runtime(data, out, source):
    """A tempo2 data directory with the release's clock files, reached through a path without spaces."""
    rt = data / RUNTIME / ".pixi/envs/default"
    if not (rt / "bin/tempo2").exists():
        raise FileNotFoundError("Isolated TEMPO2 runtime missing: " + str(rt))
    bound = out / "bound-runtime"
    clock = bound / "clock"
    bound.mkdir()
    shutil.copytree(rt / "share/tempo2/clock", clock)
    intake = data / "source-compatibility-20260908"
    directories = [intake / "clocks"] + ([intake / "epta-noise/EPTA-DR2/clockfiles"] if source == "epta" else [])
    for directory in directories:
        for p in sorted(directory.glob("*.clk")):
            shutil.copy2(p, clock / p.name)
    if source == "ppta":
        shutil.copy2(intake / "clocks/pks2gps-ppta-dr3.clk", clock / "pks2gps.clk")
    for p in (rt / "share/tempo2").iterdir():
        if p.name != "clock":
            (bound / p.name).symlink_to(p, target_is_directory=p.is_dir())
    alias = Path.home() / ".cache/recherche-tempo2" / out.name
    if alias.exists() or alias.is_symlink():
        raise FileExistsError("Runtime alias exists: " + str(alias))
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.symlink_to(bound, target_is_directory=True)
    if " " in str(alias):
        raise ValueError("TEMPO2 needs a path without spaces")
    env = {**os.environ, "TEMPO2": str(alias), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    return rt, env, {p.name: cal.digest(p) for p in sorted(clock.glob("*")) if p.is_file()}


def compare(prepared, tempo2, design, covariance, times, limit=LIMIT):
    """Statistics of prepared minus tempo2 residuals, before and after the search's projection."""
    if len(prepared) != len(tempo2["residuals"]) or tempo2["deleted"].any():
        raise ValueError("Arrival-time count differs: %d prepared, %d tempo2, %d deleted" % (
            len(prepared), len(tempo2["residuals"]), int(tempo2["deleted"].sum())))
    offset = (times - tempo2["site_times"]) * 86400.0
    if offset.min() < OFFSET_SECONDS[0] or offset.max() > OFFSET_SECONDS[1]:
        raise ValueError("Arrival times are not in the same order: offsets %.1f to %.1f s" % (offset.min(), offset.max()))
    result = reexpress.equivalence(np.asarray(tempo2["residuals"], np.longdouble), np.asarray(prepared, np.longdouble),
                                   design, covariance)
    difference = prepared - tempo2["residuals"]
    result["rms_difference_seconds_before_projection"] = float(np.std(difference))
    result["limit_in_TOA_sigma"] = limit
    result["status"] = "AGREES_WITH_TEMPO2" if result["maximum_difference_in_TOA_sigma"] <= limit else "DIFFERS_FROM_TEMPO2"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True, help="the Project Recherche Data directory")
    parser.add_argument("--root", required=True, help="a prepared pta-binary root inside it")
    parser.add_argument("--targets", nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True, help="new working directory (inside the data directory)")
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    data, out = args.data.resolve(), args.out.resolve()
    if args.result.exists():
        raise FileExistsError(args.result)
    root = data / args.root
    selection = cal.read(root / "selection.json")
    out.mkdir(parents=True, exist_ok=False)
    rt, env, clocks = bound_runtime(data, out, selection["source"])
    rows = []
    for target in args.targets:
        folder = root / target
        work = out / target
        work.mkdir()
        try:
            receipt = cal.read(folder / "prepared/receipt.json")
            profile, arrays = cal.load_profile(folder / "profile/profile.json")
            if profile["provenance"]["preparation_receipt_sha256"] != cal.digest(folder / "prepared/receipt.json"):
                raise ValueError("Receipt binding differs")
            par, tim = folder / "original" / (target + ".par"), folder / "original" / (target + ".tim")
            with (work / "worker.log").open("w") as log:
                done = subprocess.run([str(rt / "bin/python"), "-u", str(REPO / "tools/tempo2_residuals_export.py"),
                                       str(par), str(tim), str(work / "tempo2.npz")], env=env, cwd=tim.parent,
                                      stdout=log, stderr=subprocess.STDOUT, timeout=3600)
            if done.returncode:
                raise RuntimeError("tempo2 worker failed; see " + str(work / "worker.log"))
            if any(code in (work / "worker.log").read_text() for code in ("[CLK4]", "[CLK7]", "[CLK9]", "Could not open")):
                raise ValueError("tempo2 reported a missing clock or resource")
            with np.load(work / "tempo2.npz") as z:
                tempo2 = {k: z[k] for k in z.files}
            with np.load(folder / "prepared/observed.npz") as z:
                prepared = z["residuals"]
            result = compare(prepared, tempo2, arrays["design"], arrays["covariance"], arrays["times"])
            rows.append({"target": target, "released_binary_model": receipt["binary_model"],
                         "searched_binary_model": receipt["searched_binary_model"],
                         "model_steps": sorted(receipt["checks"].get("model_steps", {})), "toas": len(prepared),
                         "tempo2": cal.read(work / "tempo2.json"), "receipt_sha256": cal.digest(folder / "prepared/receipt.json"),
                         **result})
        except Exception as error:
            rows.append({"target": target, "status": "COMPARISON_FAILED", "error": str(error)})
        r = rows[-1]
        print("%-11s %-20s %s" % (target, r["status"], "after projection %.4f TOA sigma; before %.3g us rms" % (
            r["maximum_difference_in_TOA_sigma"], r["rms_difference_seconds_before_projection"] * 1e6)
            if "maximum_difference_in_TOA_sigma" in r else r["error"][:200]), flush=True)
    cal.write(args.result, {
        "status": "TEMPO2_COMPARISON_COMPLETE", "root": args.root, "source": selection["source"],
        "selection_sha256": cal.digest(root / "selection.json"), "limit_in_TOA_sigma": LIMIT,
        "code_sha256": {p.name: cal.digest(p) for p in (Path(__file__), REPO / "tools/tempo2_residuals_export.py")},
        "runtime_lock_sha256": cal.digest(data / RUNTIME / "pixi.lock"), "clock_hashes": clocks,
        "rule": "tempo2 pre-fit residuals of the original released files against the prepared residuals; difference "
                "projected with the search's design under the search covariance; agreement when at most the limit",
        "observed_periodogram_computed": False, "calibration_executed": False, "observed_search_executed": False,
        "results": rows})


if __name__ == "__main__":
    main()
