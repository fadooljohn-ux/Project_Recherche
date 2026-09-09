from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .paths import configured_data_root, repository_root, require_initialized_data_root
from .provenance import hash_file

INITIAL_V01_FREEZE = "protocol/INITIAL_V0.1_RELEASE_FREEZE.json"


def verify_initial_v01_release(data_root: Path | None = None) -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / INITIAL_V01_FREEZE
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "initial_v0.1_promoted":
        failures.append("release status is invalid")
    if freeze.get("promotion_score") != "22_of_22":
        failures.append("promotion score is invalid")
    if freeze.get("observed_residual_periodic_search_authorized") is not False:
        failures.append("observed-residual periodic search must remain unauthorized")
    for relative, expected in freeze.get("repository_sha256", {}).items():
        path = root / relative
        if not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"repository hash mismatch: {relative}")
    external_checked = data_root is not None
    if data_root is not None:
        for relative, expected in freeze.get("external_records", {}).items():
            path = data_root / relative
            if not path.is_file() or path.stat().st_size != int(expected["bytes"]):
                failures.append(f"external record missing or wrong size: {relative}")
            elif hash_file(path, "sha256") != expected["sha256"]:
                failures.append(f"external record hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "milestone": "initial-v0.1",
        "promotion_score": freeze.get("promotion_score"),
        "external_records_checked": external_checked,
        "observed_residual_periodic_search_authorized": False,
        "next_gate": freeze.get("next_gate"),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m pulsar_pilot.release")
    parser.add_argument("--check-external", action="store_true")
    parser.add_argument("--data-root")
    args = parser.parse_args()
    data_root = configured_data_root(args.data_root) if args.check_external else None
    if data_root is not None:
        require_initialized_data_root(data_root)
    result = verify_initial_v01_release(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
