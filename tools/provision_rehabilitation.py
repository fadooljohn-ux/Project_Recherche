"""Copy admitted Recherche inputs to a fresh root and verify a restored backup."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

from pulsar_pilot.paths import MARKER_PROJECT
from pulsar_pilot.pilot2_offline_resources import (
    build_environment_manifest,
    build_resource_manifest,
)


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-source", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    spec = json.loads((repo / "config/rehabilitation_inputs.json").read_text())
    sources = {
        "HIST": args.historical_source.resolve(strict=True),
        "REPO": repo,
        "ENV": Path(sys.prefix) / "lib/python3.11/site-packages/astropy_iers_data/data",
    }
    root = args.data_root.resolve()
    if root.exists() or root.is_relative_to(repo) or args.backup.exists():
        raise RuntimeError("Use a fresh external data root and backup path")
    # All source identities are checked before creating the destination.
    for item in spec["inputs"]:
        source = sources[item["source_class"]] / item["source_path"]
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"Input is not a regular file: {source}")
        if source.stat().st_size != item["bytes"] or sha(source) != item["sha256"]:
            raise RuntimeError(f"Input identity differs: {source}")
    root.mkdir(parents=True)
    for item in spec["inputs"]:
        source = sources[item["source_class"]] / item["source_path"]
        dest = root / item["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        if sha(source) != item["sha256"] or sha(dest) != item["sha256"]:
            raise RuntimeError(f"Copy or source-after identity differs: {source}")
    write(
        root / ".project-recherche-data-root.json",
        {
            "schema_version": 2,
            "project": MARKER_PROJECT,
            "data_root_id": "recherche-rehabilitation-20260907",
            "generation": "rehabilitation-20260907",
        },
    )
    meta = root / "metadata"
    meta.mkdir()
    resource = build_resource_manifest(
        root,
        manifest_id="recherche-rehabilitation-resources-20260907",
        local_repository_relative_path="derived/cache-v0.2.8",
        clock_override_relative_path="controlled/clock-overrides",
        entries=spec["resources"],
        required_resource_classes=sorted({r["resolution_role"] for r in spec["resources"]}),
    )
    write(meta / "resources.json", resource)
    environment = build_environment_manifest(
        repo,
        manifest_id="recherche-rehabilitation-environment-20260907",
        resource_manifest_sha256=sha(meta / "resources.json"),
        critical_modules=["pint", "pint.fitter", "astropy", "numpy", "scipy"],
        allowed_environment=["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"],
    )
    write(meta / "environment.json", environment)
    inventory = {str(p.relative_to(root)): sha(p) for p in root.rglob("*") if p.is_file()}
    args.backup.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.backup, "x") as archive:
        for relative in inventory:
            archive.add(root / relative, arcname=relative, recursive=False)
    with tempfile.TemporaryDirectory(prefix="recherche-input-restore-") as temp:
        with tarfile.open(args.backup) as archive:
            archive.extractall(temp, filter="data")
        restored = Path(temp)
        actual = {str(p.relative_to(restored)): sha(p) for p in restored.rglob("*") if p.is_file()}
        if actual != inventory:
            raise RuntimeError("Restored input inventory differs")
    receipt = {
        "status": "PASS",
        "data_root": str(root),
        "input_files": 21,
        "resource_files": 10,
        "files": inventory,
        "backup": str(args.backup),
        "backup_sha256": sha(args.backup),
        "restore_verified": True,
        "source_after_verified": True,
        "formal_science_executed": False,
    }
    write(meta / "provisioning-receipt.json", receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
