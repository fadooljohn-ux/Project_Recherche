"""Bind completed IPTA preparation/calibration and reuse the observed GLS runner."""
import argparse
from pathlib import Path
import shutil
import subprocess

import mpta_batch as observed
import target_calibration as cal

REPO = Path(__file__).resolve().parents[1]


def freeze(data, profile_path, cache, preparation):
    profile, _ = cal.load_profile(profile_path)
    receipt = cal.read(preparation / "receipt.json")
    if receipt["status"] != "TIMING_NOISE_COMPATIBLE":
        raise ValueError("Preparation is not timing/noise compatible")
    if profile["provenance"]["preparation_receipt_sha256"] != cal.digest(preparation / "receipt.json"):
        raise ValueError("Calibration uses another preparation")
    for name, expected in receipt["artifact_hashes"].items():
        if cal.digest(preparation / name) != expected:
            raise ValueError(f"Prepared artifact changed: {name}")
    implementation = cal.implementation()
    cached = cal.verify_cache(cache, {"profile": profile, "implementation": implementation})
    if profile["target"] != receipt["target"]:
        raise ValueError("This entry point binds one matching target")
    target = profile["target"]
    data.mkdir(parents=True, exist_ok=False)
    root = data / target
    shutil.copytree(profile_path.parent, root / "profile")
    (root / "prepared").mkdir()
    shutil.copy2(preparation / "observed.npz", root / "prepared/observed.npz")
    shutil.copy2(preparation / "receipt.json", root / "prepared/receipt.json")
    selection = {"selected": [target], "source": "IPTA", "dataset": "IPTA DR2 Version B TDB",
                 "policy": profile["policy"], "rows": [{"target": target, "selected": True}]}
    if "campaign_manifest" in profile["provenance"]:
        manifest = Path(profile["provenance"]["campaign_manifest"])
        campaign = cal.read(manifest)
        if cal.digest(manifest) != profile["provenance"]["campaign_manifest_sha256"]:
            raise ValueError("Campaign selection changed")
        if target not in campaign["selected"] or len(campaign["selected"]) != profile["policy"]["search_count"]:
            raise ValueError("Target or false-alarm count differs from campaign")
        selection["campaign_manifest"] = str(manifest)
        selection["campaign_manifest_sha256"] = cal.digest(manifest)
    cal.write(data / "selection.json", selection)
    calibration = {"cache_hit": True, "path": str(cache), **cached["summary"]}
    frozen = {
        "created_utc": observed.now(), "selection_sha256": cal.digest(data / "selection.json"),
        "code_sha256": cal.digest(observed.__file__), "implementation": implementation,
        "adapter_sha256": cal.digest(__file__),
        "targets": {target: {"profile_sha256": cal.digest(root / "profile/profile.json"),
                             "observed_sha256": cal.digest(root / "prepared/observed.npz"),
                             "calibration": calibration}},
        "search": "One circular grid; existing profile period bounds, threshold and eligible mask; fixed released noise",
        "batch_alpha_conditional": profile["policy"]["false_alarm_probability"],
        "max_targets": profile["policy"]["search_count"],
        "preparation_receipt_sha256": cal.digest(preparation / "receipt.json"),
        "cache_receipt_sha256": cal.digest(cache / "receipt.json"),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
    }
    cal.write(data / "execution-freeze.json", frozen)
    print("FROZEN " + cal.digest(data / "execution-freeze.json"), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--preparation", type=Path)
    args = parser.parse_args()
    data = args.data.resolve()
    if args.command == "freeze":
        if not all((args.profile, args.cache, args.preparation)):
            parser.error("freeze requires --profile, --cache and --preparation")
        freeze(data, args.profile.resolve(), args.cache.resolve(), args.preparation.resolve())
    else:
        frozen = cal.read(data / "execution-freeze.json")
        if frozen["adapter_sha256"] != cal.digest(__file__):
            raise ValueError("Frozen adapter changed")
        target, = frozen["targets"]
        observed.run(data, target)


if __name__ == "__main__":
    main()
