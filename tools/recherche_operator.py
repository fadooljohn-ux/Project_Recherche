"""Local installation, admitted input setup and verified backups; no scientific fits."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from pulsar_pilot.pilot2_offline_resources import (
    load_resource_manifest,
    validate_environment_manifest,
)
from pulsar_pilot.pilot2_release_contract import (
    load_science_controls,
    verify_ioc_science_execution_authorization,
)

REPO = Path(__file__).resolve().parents[1]
BINDING = REPO / "protocol/RUNTIME_ENVIRONMENT_BINDING_20261116.json"
# Source lock of the current formal qualification (qualification 03, 16 November 2026).
SOURCE_LOCK = "results/qualification/qualification03-readiness.json"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def validate_bound_environment(manifest, resource_manifest_sha256):
    """Verify the live environment, applying the owner-authorized host binding.

    A manifest generated on this host is verified directly. The 16 November 2026
    binding applies only to a manifest that still holds the qualification 02
    values: then just the Python executable hash and macOS version are replaced,
    and only in this checkout. Frozen manifests are never edited. Packages,
    critical modules, precision and environment variables stay exact.
    """
    binding = read(BINDING) if BINDING.exists() else None
    old = binding["supersedes"] if binding else None
    validate_environment_manifest(
        manifest,
        repository_root=REPO,
        resource_manifest_sha256=resource_manifest_sha256,
        verify_live=False,
    )
    if (
        binding is None
        or manifest["python"]["executable_sha256"] != old["python_executable_sha256"]
        or manifest["platform"]["macos"] != old["macos"]
    ):
        validate_environment_manifest(
            manifest, repository_root=REPO, resource_manifest_sha256=resource_manifest_sha256
        )
        return "native"
    if binding["checkout"] != str(REPO):
        raise RuntimeError(
            f"Environment binding is for {binding['checkout']}; another location needs a new binding"
        )
    new = binding["bound"]
    rebound = json.loads(json.dumps(manifest))
    rebound["python"]["executable_sha256"] = new["python_executable_sha256"]
    rebound["platform"]["macos"] = new["macos"]
    validate_environment_manifest(
        rebound, repository_root=REPO, resource_manifest_sha256=resource_manifest_sha256
    )
    return binding["binding_id"]


def verify_inputs(root):
    marker = read(root / ".project-recherche-data-root.json")
    if marker.get("project") != "project-recherche-pulsar-pilot":
        raise RuntimeError("Data root does not belong to Recherche")
    if marker.get("data_root_id") == "recherche-rehabilitation-20260907":
        receipt = read(root / "metadata/provisioning-receipt.json")
        if receipt.get("status") != "PASS":
            raise RuntimeError("Development provisioning receipt is not PASS")
    inputs = read(REPO / "config/rehabilitation_inputs.json")["inputs"]
    for item in inputs:
        path = root / item["path"]
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(root)
            or path.stat().st_size != item["bytes"]
            or sha(path) != item["sha256"]
        ):
            raise RuntimeError(f"Input differs: {item['path']}")
    resources = load_resource_manifest(root / "metadata/resources.json", data_root=root)
    validate_bound_environment(
        read(root / "metadata/development-environment.json"),
        sha(root / "metadata/resources.json"),
    )
    return {"inputs_verified": len(inputs), "resources_verified": len(resources["entries"])}


def doctor(root=None):
    frozen = verify_ioc_science_execution_authorization(root=REPO)
    if frozen["status"] != "pass":
        raise RuntimeError(f"Qualified implementation differs: {frozen['failures']}")
    expected = read(REPO / SOURCE_LOCK)["source_sha256"]
    actual = {p.relative_to(REPO).as_posix(): sha(p) for p in (REPO / "src").rglob("*.py")}
    if actual != expected:
        raise RuntimeError("Python source differs from the qualified release")
    # The runner configuration names the manifests the formal qualification binds.
    manifests = load_science_controls(REPO)[2]["manifests"]
    environment = read(REPO / manifests["environment"])
    environment_binding = validate_bound_environment(
        environment, sha(REPO / manifests["resource"])
    )
    result = {
        "status": "PASS",
        "environment_binding": environment_binding,
        "project_root": str(REPO),
        "python": sys.executable,
        "packages_verified": len(environment["packages"]),
        "precision": environment["precision"],
        "qualified_source_verified": True,
        "scientific_fits_executed": 0,
    }
    if root is not None:
        result.update(data_root=str(root), **verify_inputs(root))
    return result


def init_data(source, destination):
    doctor(source)
    if destination.exists() or destination.is_relative_to(REPO):
        raise RuntimeError("Use a fresh external data root")
    inputs = read(REPO / "config/rehabilitation_inputs.json")["inputs"]
    destination.mkdir(parents=True)
    for relative in [x["path"] for x in inputs] + [
        "metadata/resources.json",
        "metadata/development-environment.json",
    ]:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    write(
        destination / ".project-recherche-data-root.json",
        {
            "schema_version": 2,
            "project": "project-recherche-pulsar-pilot",
            "data_root_id": "recherche-rehabilitation-20260907",
            "generation": "operational-development-" + datetime.now(UTC).isoformat(),
        },
    )
    verify_inputs(source)
    write_input_receipt(destination, source)
    return doctor(destination)


def write_input_receipt(destination, source):
    """Record this input copy for the existing development launch contract."""
    write(
        destination / "metadata/provisioning-receipt.json",
        {
            "status": "PASS",
            "data_root": str(destination),
            "source_data_root": str(source),
            "input_files": 21,
            "resource_files": 10,
            "source_after_verified": True,
            "formal_science_executed": False,
            "files": {
                p.relative_to(destination).as_posix(): sha(p)
                for p in destination.rglob("*")
                if p.is_file() and p.name != "provisioning-receipt.json"
            },
        },
    )


def backup(root, output):
    doctor(root)
    # A backup must not race an active development or formal ledger.
    for path in root.rglob("*ledger.json"):
        state = read(path)
        if state.get("runtime_active") or state.get("active_attempt"):
            raise RuntimeError(f"Run still active: {path}")
    for path in (root / "development-runs").glob("*/status.json"):
        if read(path).get("state") in {"running", "prepared"}:
            raise RuntimeError(f"Development attempt still active: {path}")
    if output.is_relative_to(root) or output.exists():
        raise RuntimeError("Use a new archive path outside the data root")
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    if any(p.is_symlink() or not p.resolve().is_relative_to(root) for p in paths):
        raise RuntimeError("Backup input contains links outside the file inventory")
    before = {p.relative_to(root).as_posix(): sha(p) for p in paths}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "x", dereference=True) as archive:
        for path in paths:
            archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
    with tarfile.open(output) as archive:
        members = archive.getmembers()
        if len(members) != len(before) or {m.name for m in members} != set(before):
            raise RuntimeError("Backup inventory differs")
        for member in members:
            if (
                not member.isfile()
                or hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                != before[member.name]
            ):
                raise RuntimeError(f"Backup content differs: {member.name}")
    after = {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*") if p.is_file()}
    if before != after:
        raise RuntimeError(
            "Data changed during backup; preserve archive and retry after the run stops"
        )
    result = {
        "status": "PASS",
        "archive": str(output),
        "sha256": sha(output),
        "file_count": len(before),
        "content_verified": True,
        "source_after_verified": True,
    }
    write(output.with_name(output.name + ".receipt.json"), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser(
        "doctor", help="Verify qualified source, pinned environment and optional inputs"
    )
    check.add_argument("--data-root", type=Path)
    init = sub.add_parser("init-data", help="Copy admitted inputs into a fresh development root")
    init.add_argument("--from-data-root", required=True, type=Path)
    init.add_argument("--data-root", required=True, type=Path)
    archive = sub.add_parser("backup", help="Archive an inactive data root and verify every file")
    archive.add_argument("--data-root", required=True, type=Path)
    archive.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = args.data_root.resolve() if args.data_root else None
        if args.command == "doctor":
            result = doctor(root)
        elif args.command == "init-data":
            result = init_data(args.from_data_root.resolve(strict=True), root)
        else:
            result = backup(root, args.output.resolve())
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"status": "FAIL", "message": str(error)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
