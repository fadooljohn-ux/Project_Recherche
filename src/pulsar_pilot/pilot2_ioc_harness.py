"""Small foreground operator conductor for a separately bound Pilot 2 run.

This module deliberately owns only authority, preflight, run identity, status,
and terminal evidence.  A science implementation is supplied through the
``ScienceModule`` protocol; the default CLI adapter is loaded only at the
command boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

import psutil

from .paths import MARKER_PROJECT
from .pilot2_release_contract import validate_ioc_science_execution_binding
from .pilot2_trusted_data import exact_typed_equal

AUTHORITY_SCHEMA = "pilot2-ioc-authority"
GATE4_AUTHORITY_SCHEMA = "pilot2-ioc-gate4-preflight-authority-v1"
GATE4_PREFLIGHT_SCHEMA = "pilot2-ioc-gate4-preflight-v1"
GATE4_RESULT_SCHEMA = "pilot2-ioc-gate4-preflight-result-v1"
GATE4_NETWORK_PROFILE = "(version 1)(allow default)(deny network*)"
GATE_SCHEMA = "pilot2-ioc-gate"
PREFLIGHT_SCHEMA = "pilot2-ioc-preflight"
MANIFEST_SCHEMA = "pilot2-ioc-manifest"
EVENT_SCHEMA = "pilot2-ioc-event"
TERMINAL_SCHEMA = "pilot2-ioc-terminal-inventory"
STATUS_SCHEMA = "pilot2-ioc-status"
DEFAULT_ADAPTER = "pulsar_pilot.pilot2_science_module:SCIENCE_MODULE"

ZERO_SCIENCE_COUNTERS: tuple[str, ...] = (
    "network_requests",
    "resource_acquisitions",
    "operational_context_loads",
    "operational_qualification_cases",
    "operational_science_entry_calls",
    "controlled_artifact_loads",
    "observed_artifact_loads",
    "observed_residual_reads",
    "external_data_root_accesses",
)
GATE4_ZERO_SCIENCE_COUNTERS: tuple[str, ...] = (
    "network_connection_attempts",
    "downloaded_bytes",
    "science_cases_executed",
    "random_draws_generated",
    "primary_fits_executed",
    "solver_audits_executed",
    "periodic_scans_executed",
    "observed_residual_reads",
    "science_entry_calls",
    "science_run_roots_created",
    "science_artifacts_created",
)
STATUS_STATES = {"prepared", "running", "complete", "controlled_stop", "operational_failure"}
STATUS_STAGES = {"prepared", "run", "terminal"}
STATUS_TERMINAL = {"complete", "controlled_stop", "operational_failure"}
SCIENCE_EVIDENCE_SCHEMA = "pilot2-science-evidence-binding-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEX_RE = re.compile(r"^[0-9a-f]+$")


class ScienceModule(Protocol):
    """The only execution surface the conductor accepts from science."""

    module_id: str
    release_id: str

    def verify_gate(
        self,
        project_root: Path,
        science_execution: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def preflight(
        self,
        project_root: Path,
        qualification: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]: ...

    def run(
        self,
        run_root: Path,
        manifest: Mapping[str, Any],
        publish_status: Callable[..., Mapping[str, Any]],
    ) -> Mapping[str, Any]: ...


class ControlledStop(RuntimeError):
    """The operator interrupted the one-shot foreground run."""


class IocError(RuntimeError):
    """Fail-closed conductor error."""


GATE_KEYS = {
    "schema",
    "status",
    "authority",
    "repository",
    "science_module",
    "adapter_gate",
    "authority_sha256",
}
PREFLIGHT_KEYS = {
    "schema",
    "status",
    "authority_sha256",
    "gate_sha256",
    "repository",
    "science_module",
    "zero_science_counters",
    "adapter_preflight",
}
MANIFEST_KEYS = {
    "schema",
    "run_id",
    "project_root",
    "runs_root",
    "release",
    "science_module",
    "authority_sha256",
    "gate_sha256",
    "preflight_sha256",
    "status_path",
    "events_path",
    "terminal_inventory_path",
    "science_execution",
}

SCIENCE_EVIDENCE_KEYS = {
    "schema",
    "ioc_run_id",
    "science_run_id",
    "ioc_manifest_sha256",
    "execution_freeze_sha256",
    "inventory_sha256",
    "data_root_id",
    "marker_sha256",
    "execution_binding_sha256",
    "accounting",
    "artifacts",
    "hard_stop_present",
    "scientific_outcomes_visible",
}
SCIENCE_EVIDENCE_ACCOUNTING_KEYS = {
    "completed",
    "total",
    "checkpoint",
    "primary_fits",
    "solver_audits",
}
SCIENCE_EVIDENCE_ARTIFACT_PATHS = {
    "ledger": "run_records/pilot2/calibration-v0.2.8-ledger.json",
    "terminal_result": "run_records/pilot2/injection-evaluation-v0.2.8.json",
    "annual_mask": "run_records/pilot2/annual-identifiability-mask-v0.2.8.json",
    "health": "run_records/pilot2/calibration-v0.2.8-health.json",
}


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise IocError(f"{label} is not a timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise IocError(f"{label} is not a timestamp") from exc
    if parsed.tzinfo is None:
        raise IocError(f"{label} is not timezone-aware")
    return parsed


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise IocError(f"{label} is not a SHA-256")
    return value


def _safe_project_root(path: Path) -> Path:
    root = Path(path).resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        raise IocError("project root is not a Git checkout")
    return root


def _safe_external(path: Path, project_root: Path, *, create: bool = False) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        raise IocError("evidence or runs root must be absolute")
    if candidate.exists() and (candidate.is_symlink() or not candidate.is_dir()):
        raise IocError("evidence or runs root is not a real directory")
    if create:
        candidate.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(candidate, 0o700)
    resolved = candidate.resolve(strict=False)
    if resolved == project_root or project_root in resolved.parents:
        raise IocError("evidence or runs root must be outside the project root")
    return resolved


def _git(project_root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(project_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise IocError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def repository_identity(project_root: Path) -> dict[str, Any]:
    root = _safe_project_root(project_root)
    commit = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    tracked = _git(root, "ls-files", "-s")
    return {
        "root": str(root),
        "commit": commit,
        "tree": tree,
        "clean": status == "",
        "tracked_manifest_sha256": _sha256_bytes((tracked + "\n").encode("utf-8")),
    }


def _module_identity(module: ScienceModule) -> dict[str, str]:
    module_id = getattr(module, "module_id", None)
    release_id = getattr(module, "release_id", None)
    if not isinstance(module_id, str) or not module_id:
        raise IocError("science adapter is unbound: module_id is absent")
    if not isinstance(release_id, str) or not release_id:
        raise IocError("science adapter is unbound: release_id is absent")
    return {"module_id": module_id, "release_id": release_id}


def _load_default_module() -> ScienceModule:
    module_name, separator, attribute = DEFAULT_ADAPTER.partition(":")
    if not separator:
        raise IocError(f"fixed science adapter is malformed: {DEFAULT_ADAPTER}")
    try:
        loaded = importlib.import_module(module_name)
    except Exception as exc:
        raise IocError(
            f"fixed science adapter is unbound: {DEFAULT_ADAPTER} ({type(exc).__name__}: {exc})"
        ) from exc
    value = getattr(loaded, attribute, None)
    if value is None:
        raise IocError(f"fixed science adapter is unbound: {DEFAULT_ADAPTER}")
    return cast(ScienceModule, value)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IocError(f"cannot read JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise IocError(f"JSON evidence is not an object: {path}")
    return value


def _write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    encoded = _canonical(value) if not isinstance(value, bytes) else value
    try:
        with path.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise IocError(f"write-once evidence already exists: {path}") from exc
    try:
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError:
        pass


def _write_event(path: Path, event: Mapping[str, Any]) -> None:
    if not path.exists():
        _write_once(path, _canonical(dict(event)))
        return
    with path.open("ab") as handle:
        handle.write(_canonical(dict(event)))
        handle.flush()
        os.fsync(handle.fileno())


def _validate_authority(
    authority: Mapping[str, Any],
    project_root: Path,
    repository: Mapping[str, Any],
    module: ScienceModule,
) -> dict[str, Any]:
    required = {
        "schema",
        "authority_id",
        "run_id",
        "created_at",
        "expires_at",
        "project_root",
        "runs_root",
        "attempt",
        "one_shot",
        "release",
        "science_module",
        "science_execution",
    }
    if set(authority) != required or authority.get("schema") != AUTHORITY_SCHEMA:
        raise IocError("authority schema is not exact")
    if not isinstance(authority.get("authority_id"), str) or not authority["authority_id"]:
        raise IocError("authority identity is invalid")
    run_id = authority.get("run_id")
    if not isinstance(run_id, str) or not run_id.startswith("pilot2-ioc-"):
        raise IocError("authority run identity is invalid")
    try:
        validate_ioc_science_execution_binding(
            authority.get("science_execution"), ioc_run_id=run_id
        )
    except Exception as exc:
        raise IocError("science-execution authority binding is invalid") from exc
    if authority.get("attempt") != 1 or authority.get("one_shot") is not True:
        raise IocError("authority is not a one-shot attempt")
    created_at = _parse_time(authority["created_at"], "created_at")
    expires_at = _parse_time(authority["expires_at"], "expires_at")
    if created_at > datetime.now(UTC):
        raise IocError("authority is not yet valid")
    if expires_at <= created_at or expires_at <= datetime.now(UTC):
        raise IocError("authority is expired")
    if authority.get("project_root") != str(project_root):
        raise IocError("authority project root differs")
    runs_root = _safe_external(Path(str(authority["runs_root"])), project_root)
    release = authority.get("release")
    if not isinstance(release, Mapping) or set(release) != {
        "commit",
        "tree",
        "tracked_manifest_sha256",
    }:
        raise IocError("authority release binding is not exact")
    for field in ("commit", "tree"):
        if not isinstance(release[field], str) or HEX_RE.fullmatch(release[field]) is None:
            raise IocError(f"authority release {field} is invalid")
    _require_sha(release["tracked_manifest_sha256"], "authority tracked manifest")
    if (
        dict(release) != {key: repository[key] for key in release}
        or repository.get("clean") is not True
    ):
        raise IocError("repository is dirty or release identity differs")
    expected_module = _module_identity(module)
    if authority.get("science_module") != expected_module:
        raise IocError("authority science-module binding differs")
    return {
        **dict(authority),
        "runs_root": str(runs_root),
        "release": dict(release),
        "science_module": expected_module,
        "science_execution": authority["science_execution"],
    }


def _confined_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise IocError(f"{label} is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise IocError(f"{label} is not a confined relative path")
    return value


def _validate_gate4_authority(
    authority: Mapping[str, Any],
    project_root: Path,
    repository: Mapping[str, Any],
    module: ScienceModule,
    supplied_evidence_root: Path,
) -> dict[str, Any]:
    required = {
        "schema",
        "authority_id",
        "qualification_id",
        "created_at",
        "expires_at",
        "project_root",
        "evidence_root",
        "attempt",
        "one_shot",
        "release",
        "science_module",
        "science_data_root",
        "manifest_paths",
        "setup_log_paths",
        "resource_manifest",
        "environment_manifest",
        "network_denial",
        "qualification_receipts",
        "restore_boundary",
        "host",
        "expected_zero_counters",
        "execution_authorized",
    }
    if set(authority) != required or authority.get("schema") != GATE4_AUTHORITY_SCHEMA:
        raise IocError("Gate 4 authority schema is not exact")
    if not isinstance(authority["authority_id"], str) or not authority["authority_id"]:
        raise IocError("Gate 4 authority identity is invalid")
    qualification_id = authority["qualification_id"]
    if not isinstance(qualification_id, str) or not qualification_id.startswith("pilot2-gate4-"):
        raise IocError("Gate 4 qualification identity is invalid")
    if authority["attempt"] != 1 or authority["one_shot"] is not True:
        raise IocError("Gate 4 authority is not a one-shot attempt")
    if authority["execution_authorized"] is not False:
        raise IocError("Gate 4 authority grants execution")
    created_at = _parse_time(authority["created_at"], "Gate 4 created_at")
    expires_at = _parse_time(authority["expires_at"], "Gate 4 expires_at")
    if created_at > datetime.now(UTC):
        raise IocError("Gate 4 authority is not yet valid")
    if expires_at <= created_at or expires_at <= datetime.now(UTC):
        raise IocError("Gate 4 authority is expired")
    if authority["project_root"] != str(project_root):
        raise IocError("Gate 4 project root differs")
    evidence = _safe_external(Path(str(authority["evidence_root"])), project_root)
    supplied = _safe_external(Path(supplied_evidence_root), project_root)
    if evidence != supplied or authority["evidence_root"] != str(evidence):
        raise IocError("Gate 4 evidence root differs")
    release = authority["release"]
    if not isinstance(release, Mapping) or set(release) != {
        "commit",
        "tree",
        "tracked_manifest_sha256",
    }:
        raise IocError("Gate 4 release binding is not exact")
    for field in ("commit", "tree"):
        if not isinstance(release[field], str) or HEX_RE.fullmatch(release[field]) is None:
            raise IocError(f"Gate 4 release {field} is invalid")
    _require_sha(release["tracked_manifest_sha256"], "Gate 4 tracked manifest")
    if (
        dict(release) != {key: repository[key] for key in release}
        or repository.get("clean") is not True
    ):
        raise IocError("repository is dirty or Gate 4 release identity differs")
    expected_module = _module_identity(module)
    if authority["science_module"] != expected_module:
        raise IocError("Gate 4 science-module binding differs")
    data_root = authority["science_data_root"]
    if not isinstance(data_root, Mapping) or set(data_root) != {
        "canonical_path",
        "data_root_id",
        "marker_sha256",
    }:
        raise IocError("Gate 4 data-root binding is not exact")
    canonical_path = data_root["canonical_path"]
    if (
        not isinstance(canonical_path, str)
        or not Path(canonical_path).is_absolute()
        or str(Path(canonical_path)) != canonical_path
    ):
        raise IocError("Gate 4 data-root path is invalid")
    if not isinstance(data_root["data_root_id"], str) or not data_root["data_root_id"]:
        raise IocError("Gate 4 data-root ID is invalid")
    _require_sha(data_root["marker_sha256"], "Gate 4 marker")
    manifest_paths = authority["manifest_paths"]
    expected_manifest_paths = {
        "resource": "protocol/PILOT2_RUNTIME_RESOURCE_MANIFEST_v0.2.8.json",
        "environment": "protocol/PILOT2_RUNTIME_ENVIRONMENT_MANIFEST_v0.2.8.json",
    }
    if manifest_paths != expected_manifest_paths:
        raise IocError("Gate 4 manifest destinations differ")
    for relative in expected_manifest_paths.values():
        target = project_root / relative
        if target.exists() or target.is_symlink():
            raise IocError(f"Gate 4 manifest destination already exists: {relative}")
    setup_logs = authority["setup_log_paths"]
    if not isinstance(setup_logs, list) or len(setup_logs) != 2:
        raise IocError("Gate 4 setup-log paths are not exact")
    normalized_logs = [
        _confined_relative(value, f"Gate 4 setup log[{index}]")
        for index, value in enumerate(setup_logs)
    ]
    if len(set(normalized_logs)) != 2 or any(
        not Path(value).is_relative_to(Path("run_records/pilot2")) or Path(value).suffix != ".log"
        for value in normalized_logs
    ):
        raise IocError("Gate 4 setup-log destinations are invalid")
    resource = authority["resource_manifest"]
    if not isinstance(resource, Mapping) or set(resource) != {
        "manifest_id",
        "local_repository_relative_path",
        "clock_override_relative_path",
        "entries",
        "required_resource_classes",
    }:
        raise IocError("Gate 4 resource-manifest specification is not exact")
    environment = authority["environment_manifest"]
    if not isinstance(environment, Mapping) or set(environment) != {
        "manifest_id",
        "critical_modules",
        "allowed_environment",
    }:
        raise IocError("Gate 4 environment-manifest specification is not exact")
    denial = authority["network_denial"]
    if not isinstance(denial, Mapping) or set(denial) != {
        "executable",
        "executable_sha256",
        "profile",
    }:
        raise IocError("Gate 4 network-denial binding is not exact")
    if (
        denial["executable"] != "/usr/bin/sandbox-exec"
        or denial["profile"] != GATE4_NETWORK_PROFILE
    ):
        raise IocError("Gate 4 network-denial command differs")
    denial_path = Path(denial["executable"])
    if denial_path.is_symlink() or not denial_path.is_file():
        raise IocError("Gate 4 network-denial executable is unavailable")
    if _sha256_file(denial_path) != _require_sha(
        denial["executable_sha256"], "Gate 4 network-denial executable"
    ):
        raise IocError("Gate 4 network-denial executable hash differs")
    receipts = authority["qualification_receipts"]
    if not isinstance(receipts, Mapping) or set(receipts) != {"gate2", "gate3"}:
        raise IocError("Gate 4 qualification-receipt binding is not exact")
    for name, raw in receipts.items():
        if not isinstance(raw, Mapping) or set(raw) != {"relative_path", "sha256"}:
            raise IocError(f"Gate 4 {name} receipt binding is not exact")
        relative = _confined_relative(raw["relative_path"], f"Gate 4 {name} receipt")
        path = project_root / relative
        if path.is_symlink() or not path.is_file():
            raise IocError(f"Gate 4 {name} receipt is unavailable")
        if _sha256_file(path) != _require_sha(raw["sha256"], f"Gate 4 {name} receipt"):
            raise IocError(f"Gate 4 {name} receipt hash differs")
    restore = authority["restore_boundary"]
    if not isinstance(restore, Mapping) or set(restore) != {
        "receipt_path",
        "receipt_sha256",
    }:
        raise IocError("Gate 4 restore-boundary binding is not exact")
    restore_path = Path(str(restore["receipt_path"]))
    if not restore_path.is_absolute() or restore_path.is_symlink() or not restore_path.is_file():
        raise IocError("Gate 4 restore-boundary receipt is unavailable")
    if _sha256_file(restore_path) != _require_sha(
        restore["receipt_sha256"], "Gate 4 restore-boundary receipt"
    ):
        raise IocError("Gate 4 restore-boundary receipt hash differs")
    host = authority["host"]
    if not isinstance(host, Mapping) or set(host) != {
        "python_version",
        "python_executable_sha256",
        "macos",
        "kernel_machine",
        "process_machine",
        "pointer_bits",
        "minimum_free_bytes",
    }:
        raise IocError("Gate 4 host binding is not exact")
    for name in ("python_version", "macos", "kernel_machine", "process_machine"):
        if not isinstance(host[name], str) or not host[name]:
            raise IocError(f"Gate 4 host binding is invalid: {name}")
    _require_sha(host["python_executable_sha256"], "Gate 4 Python executable")
    for name in ("pointer_bits", "minimum_free_bytes"):
        if isinstance(host[name], bool) or not isinstance(host[name], int) or host[name] < 0:
            raise IocError(f"Gate 4 host binding is invalid: {name}")
    _zero_gate4_counters(authority["expected_zero_counters"])
    return {
        **dict(authority),
        "evidence_root": str(evidence),
        "release": dict(release),
        "science_module": expected_module,
        "science_data_root": dict(data_root),
        "manifest_paths": dict(manifest_paths),
        "setup_log_paths": normalized_logs,
        "resource_manifest": dict(resource),
        "environment_manifest": dict(environment),
        "network_denial": dict(denial),
        "qualification_receipts": {key: dict(value) for key, value in receipts.items()},
        "restore_boundary": dict(restore),
        "host": dict(host),
        "expected_zero_counters": dict(authority["expected_zero_counters"]),
    }


def _zero_counters(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(ZERO_SCIENCE_COUNTERS):
        raise IocError("zero-science counter schema is not exact")
    normalized: dict[str, int] = {}
    for name in ZERO_SCIENCE_COUNTERS:
        item = value[name]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise IocError(f"zero-science counter is invalid: {name}")
        if item != 0:
            raise IocError(f"zero-science boundary is nonzero: {name}")
        normalized[name] = item
    return normalized


def _zero_gate4_counters(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(GATE4_ZERO_SCIENCE_COUNTERS):
        raise IocError("Gate 4 zero-science counter schema is not exact")
    normalized: dict[str, int] = {}
    for name in GATE4_ZERO_SCIENCE_COUNTERS:
        item = value[name]
        if isinstance(item, bool) or not isinstance(item, int) or item != 0:
            raise IocError(f"Gate 4 zero-science boundary is nonzero or invalid: {name}")
        normalized[name] = item
    return normalized


def _evidence_root(authority: Mapping[str, Any], project_root: Path, supplied: Path | None) -> Path:
    candidate = (
        supplied
        if supplied is not None
        else Path(str(authority["runs_root"])) / f".{authority['run_id']}.evidence"
    )
    return _safe_external(candidate, project_root, create=True)


def _load_authority(path: Path) -> dict[str, Any]:
    return _read_json(Path(path).resolve(strict=True))


def verify_gate(
    project_root: Path,
    authority_path: Path,
    *,
    module: ScienceModule,
) -> dict[str, Any]:
    root = _safe_project_root(project_root)
    authority = _load_authority(authority_path)
    repository = repository_identity(root)
    bound = _validate_authority(authority, root, repository, module)
    result = module.verify_gate(root, bound["science_execution"])
    if not isinstance(result, Mapping) or result.get("status") not in {"PASS", "pass"}:
        raise IocError("science gate did not pass")
    gate = {
        "schema": GATE_SCHEMA,
        "status": "PASS",
        "authority": bound,
        "repository": dict(repository),
        "science_module": _module_identity(module),
        "adapter_gate": dict(result),
    }
    return gate


def _validate_gate4_result(
    value: Any,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema",
        "status",
        "disposable_validations",
        "data_root_identity",
        "host_storage",
        "resource_manifest",
        "resource_manifest_sha256",
        "environment_manifest",
        "environment_manifest_sha256",
        "context_passes",
        "restore_boundary",
        "zero_science_counters",
        "run_root_created",
        "science_executed",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise IocError("Gate 4 adapter result schema is not exact")
    result = dict(value)
    if result["schema"] != GATE4_RESULT_SCHEMA or result["status"] != "PASS":
        raise IocError("Gate 4 adapter result did not pass")
    if result["run_root_created"] is not False or result["science_executed"] is not False:
        raise IocError("Gate 4 adapter crossed the science boundary")
    counters = _zero_gate4_counters(result["zero_science_counters"])
    if counters != authority["expected_zero_counters"]:
        raise IocError("Gate 4 zero-science counters differ from authority")
    disposable = result["disposable_validations"]
    disposable_keys = {
        "attempt",
        "status",
        "criteria",
        "candidate_implementation_sha256",
        "candidate_science_control_sha256",
        "science_cases_executed",
        "random_draws_generated",
        "model_fits_executed",
        "periodic_scans_executed",
        "observed_residual_accessed",
    }
    if (
        not isinstance(disposable, list)
        or len(disposable) != 2
        or [item.get("attempt") for item in disposable if isinstance(item, Mapping)] != [1, 2]
        or any(
            not isinstance(item, Mapping)
            or set(item) != disposable_keys
            or item["status"] != "PASS"
            or not isinstance(item["criteria"], Mapping)
            or len(item["criteria"]) != 13
            or not all(value is True for value in item["criteria"].values())
            or type(item["science_cases_executed"]) is not int
            or item["science_cases_executed"] != 0
            or type(item["random_draws_generated"]) is not int
            or item["random_draws_generated"] != 0
            or type(item["model_fits_executed"]) is not int
            or item["model_fits_executed"] != 0
            or type(item["periodic_scans_executed"]) is not int
            or item["periodic_scans_executed"] != 0
            or item["observed_residual_accessed"] is not False
            for item in disposable
        )
    ):
        raise IocError("Gate 4 disposable-root validation evidence is incomplete")
    for item in disposable:
        _require_sha(item["candidate_implementation_sha256"], "Gate 4 disposable implementation")
        _require_sha(item["candidate_science_control_sha256"], "Gate 4 disposable controls")
    if not exact_typed_equal(disposable[0]["criteria"], disposable[1]["criteria"]):
        raise IocError("Gate 4 disposable-root validation criteria differ")
    for key in (
        "candidate_implementation_sha256",
        "candidate_science_control_sha256",
    ):
        if disposable[0][key] != disposable[1][key]:
            raise IocError(f"Gate 4 disposable-root {key} differs")
    contexts = result["context_passes"]
    if (
        not isinstance(contexts, list)
        or len(contexts) != 2
        or [item.get("pass") for item in contexts if isinstance(item, Mapping)] != [1, 2]
        or any(
            not isinstance(item, Mapping)
            or set(item) != {"pass", "setup_log_relative", "setup_log_sha256", "input_binding"}
            for item in contexts
        )
    ):
        raise IocError("Gate 4 context-pass evidence is incomplete")
    if [item["setup_log_relative"] for item in contexts] != authority["setup_log_paths"]:
        raise IocError("Gate 4 context setup-log binding differs")
    for item in contexts:
        _require_sha(item["setup_log_sha256"], "Gate 4 context setup log")
    if not exact_typed_equal(contexts[0]["input_binding"], contexts[1]["input_binding"]):
        raise IocError("Gate 4 context bindings differ")
    for name in ("resource_manifest", "environment_manifest"):
        if not isinstance(result[name], Mapping):
            raise IocError(f"Gate 4 {name} is not an object")
        expected_hash = _sha256_bytes(_canonical(result[name]))
        if result[f"{name}_sha256"] != expected_hash:
            raise IocError(f"Gate 4 {name} hash differs")
    data_root_identity = result["data_root_identity"]
    if not isinstance(data_root_identity, Mapping) or set(data_root_identity) != {
        "status",
        "failures",
        "marker",
    }:
        raise IocError("Gate 4 data-root identity record is invalid")
    marker = data_root_identity["marker"]
    if (
        data_root_identity["status"] != "pass"
        or data_root_identity["failures"] != []
        or not isinstance(marker, Mapping)
        or set(marker) != {"schema_version", "project", "data_root_id", "generation"}
        or marker["schema_version"] != 2
        or marker["project"] != MARKER_PROJECT
        or marker["data_root_id"] != authority["science_data_root"]["data_root_id"]
        or not isinstance(marker["generation"], str)
        or not marker["generation"]
    ):
        raise IocError("Gate 4 data-root identity did not pass")
    host_storage = result["host_storage"]
    if not isinstance(host_storage, Mapping) or set(host_storage) != {"host", "storage"}:
        raise IocError("Gate 4 host/storage record is invalid")
    expected_host = {
        key: authority["host"][key]
        for key in (
            "python_version",
            "macos",
            "kernel_machine",
            "process_machine",
            "pointer_bits",
        )
    }
    if not exact_typed_equal(host_storage["host"], expected_host):
        raise IocError("Gate 4 host result differs from authority")
    storage = host_storage["storage"]
    if not isinstance(storage, Mapping) or set(storage) != {
        "block_size",
        "total_bytes",
        "free_bytes",
    }:
        raise IocError("Gate 4 storage record is invalid")
    if (
        any(
            isinstance(storage[name], bool)
            or not isinstance(storage[name], int)
            or storage[name] < 0
            for name in storage
        )
        or storage["free_bytes"] < authority["host"]["minimum_free_bytes"]
    ):
        raise IocError("Gate 4 storage result is invalid or insufficient")
    restore = result["restore_boundary"]
    if not isinstance(restore, Mapping) or restore.get("status") != "PASS":
        raise IocError("Gate 4 restore-boundary record did not pass")
    bound_restore = _read_json(Path(authority["restore_boundary"]["receipt_path"]))
    if not exact_typed_equal(restore, bound_restore):
        raise IocError("Gate 4 restore-boundary result differs from bound receipt")
    return result


def _gate4_preflight(
    project_root: Path,
    authority: Mapping[str, Any],
    evidence_root: Path,
    *,
    module: ScienceModule,
) -> dict[str, Any]:
    repository = repository_identity(project_root)
    bound = _validate_gate4_authority(
        authority,
        project_root,
        repository,
        module,
        evidence_root,
    )
    evidence = _safe_external(evidence_root, project_root, create=True)
    _write_once(evidence / "authority.json", bound)
    try:
        raw_result = module.preflight(project_root, bound)
        result = _validate_gate4_result(raw_result, bound)
        manifest_hashes: dict[str, str] = {}
        for name in ("resource", "environment"):
            relative = bound["manifest_paths"][name]
            key = f"{name}_manifest"
            target = project_root / relative
            _write_once(target, result[key])
            observed_hash = _sha256_file(target)
            if observed_hash != result[f"{key}_sha256"]:
                raise IocError(f"Gate 4 written {name} manifest hash differs")
            manifest_hashes[name] = observed_hash
        context_hashes: list[str] = []
        for item in result["context_passes"]:
            path = evidence / f"context-pass-{item['pass']}.json"
            _write_once(path, item)
            context_hashes.append(_sha256_file(path))
        observed_status = set(
            _git(project_root, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
        )
        expected_status = {f"?? {relative}" for relative in bound["manifest_paths"].values()}
        if observed_status != expected_status:
            raise IocError("Gate 4 repository outputs are not the exact manifest pair")
        receipt = {
            "schema": GATE4_PREFLIGHT_SCHEMA,
            "status": "PASS",
            "qualification_id": bound["qualification_id"],
            "authority_sha256": _sha256_file(evidence / "authority.json"),
            "repository_before": dict(repository),
            "repository_manifest_outputs": dict(bound["manifest_paths"]),
            "science_module": _module_identity(module),
            "resource_manifest_sha256": manifest_hashes["resource"],
            "environment_manifest_sha256": manifest_hashes["environment"],
            "context_pass_sha256": context_hashes,
            "disposable_validations": result["disposable_validations"],
            "host_storage": result["host_storage"],
            "restore_boundary_receipt_sha256": bound["restore_boundary"]["receipt_sha256"],
            "zero_science_counters": result["zero_science_counters"],
            "execution_authorized": False,
            "run_root_created": False,
            "science_executed": False,
        }
        _write_once(evidence / "gate4-preflight.json", receipt)
        return receipt
    except BaseException as error:
        failure = {
            "schema": GATE4_PREFLIGHT_SCHEMA,
            "status": "FAIL",
            "qualification_id": bound["qualification_id"],
            "authority_sha256": _sha256_file(evidence / "authority.json"),
            "error_type": type(error).__name__,
            "message": str(error) or type(error).__name__,
            "execution_authorized": False,
            "run_root_created": False,
            "science_executed": False,
        }
        try:
            _write_once(evidence / "gate4-failure.json", failure)
        except BaseException as receipt_error:  # noqa: BLE001 - do not mask initiating failure.
            error.add_note(
                "Gate 4 failure receipt could not be written: "
                f"{type(receipt_error).__name__}: {receipt_error}"
            )
        raise


def preflight(
    project_root: Path,
    authority_path: Path,
    evidence_root: Path,
    *,
    module: ScienceModule,
) -> dict[str, Any]:
    root = _safe_project_root(project_root)
    authority = _load_authority(authority_path)
    if authority.get("schema") == GATE4_AUTHORITY_SCHEMA:
        return _gate4_preflight(root, authority, evidence_root, module=module)
    gate = verify_gate(root, authority_path, module=module)
    bound = dict(gate["authority"])
    repository = dict(gate["repository"])
    evidence = _evidence_root(bound, root, evidence_root)
    _write_once(evidence / "authority.json", bound)
    gate = {
        **gate,
        "authority_sha256": _sha256_file(evidence / "authority.json"),
    }
    _write_once(evidence / "gate.json", gate)
    result = module.preflight(root)
    if not isinstance(result, Mapping):
        raise IocError("science preflight did not return an object")
    counters = _zero_counters(result.get("zero_science_counters"))
    if result.get("run_root_created") is not False:
        raise IocError("science preflight created a run root")
    if result.get("science_executed") is not False:
        raise IocError("science preflight executed science")
    record = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "PASS",
        "authority_sha256": _sha256_file(evidence / "authority.json"),
        "gate_sha256": _sha256_file(evidence / "gate.json"),
        "repository": dict(repository),
        "science_module": _module_identity(module),
        "zero_science_counters": counters,
        "adapter_preflight": dict(result),
    }
    _write_once(evidence / "preflight.json", record)
    return record


def _status_value(
    run_id: str,
    state: str,
    stage: str,
    completed: int,
    total: int,
    checkpoint: int,
    message: str,
    *,
    error_type: str | None = None,
    terminal: bool = False,
    elapsed_seconds: float = 0.0,
) -> dict[str, Any]:
    process = psutil.Process(os.getpid())
    try:
        process_started = float(process.create_time()) if state == "running" else 0.0
    except (psutil.Error, OSError):
        process_started = 0.0
    try:
        cpu = float(process.cpu_percent(interval=None)) if state == "running" else 0.0
        rss = float(process.memory_info().rss) / 1024**3 if state == "running" else 0.0
    except (psutil.Error, OSError):
        cpu, rss = 0.0, 0.0
    return {
        "schema": STATUS_SCHEMA,
        "run_id": run_id,
        "state": state,
        "stage": stage,
        "completed": completed,
        "total": total,
        "checkpoint": checkpoint,
        "updated_at": _utc_now(),
        "elapsed_seconds": round(max(0.0, float(elapsed_seconds)), 3),
        "pid": os.getpid() if state == "running" else 0,
        "process_started_at_epoch": process_started,
        "cpu_percent": round(max(0.0, cpu), 2),
        "rss_gib": round(max(0.0, rss), 6),
        "error_type": error_type,
        "terminal": terminal,
        "science_outcomes_visible": False,
        "message": message,
    }


def _validate_status(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "run_id",
        "state",
        "stage",
        "completed",
        "total",
        "checkpoint",
        "updated_at",
        "elapsed_seconds",
        "pid",
        "process_started_at_epoch",
        "cpu_percent",
        "rss_gib",
        "error_type",
        "terminal",
        "science_outcomes_visible",
        "message",
    }
    if set(value) != required or value.get("schema") != STATUS_SCHEMA:
        raise IocError("status contract is not exact")
    if not isinstance(value["run_id"], str) or not value["run_id"].startswith("pilot2-ioc-"):
        raise IocError("status run identity is invalid")
    if value["state"] not in STATUS_STATES or value["stage"] not in STATUS_STAGES:
        raise IocError("status state or stage is invalid")
    if any(
        isinstance(value[name], bool) or not isinstance(value[name], int) or value[name] < 0
        for name in ("completed", "total", "checkpoint", "pid")
    ):
        raise IocError("status accounting is invalid")
    if value["checkpoint"] > value["completed"] or value["completed"] > value["total"]:
        raise IocError("status completed count exceeds total")
    if any(
        isinstance(value[name], bool)
        or not isinstance(value[name], (int, float))
        or not math.isfinite(float(value[name]))
        or value[name] < 0
        for name in ("elapsed_seconds", "process_started_at_epoch", "cpu_percent", "rss_gib")
    ):
        raise IocError("status process metrics are invalid")
    if not isinstance(value["error_type"], (str, type(None))) or not isinstance(
        value["message"], str
    ):
        raise IocError("status error or message is invalid")
    if any(not isinstance(value[name], bool) for name in ("terminal", "science_outcomes_visible")):
        raise IocError("status flags are invalid")
    if value["science_outcomes_visible"] is not False or value["terminal"] != (
        value["state"] in STATUS_TERMINAL
    ):
        raise IocError("status exposes science or has an invalid terminal flag")
    if value["state"] == "complete" and not value["terminal"]:
        raise IocError("complete status is not terminal")
    _parse_time(value["updated_at"], "status.updated_at")
    return dict(value)


def _publish_status(run_root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    _validate_status(value)
    temporary = run_root / ".status.json.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(_canonical(dict(value)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, run_root / "status.json")
    finally:
        if temporary.exists():
            temporary.unlink()
    return dict(value)


def prepare(
    project_root: Path,
    evidence_root: Path,
    *,
    module: ScienceModule,
) -> Path:
    root = _safe_project_root(project_root)
    evidence = _safe_external(evidence_root, root)
    authority = _read_json(evidence / "authority.json")
    repository = repository_identity(root)
    bound = _validate_authority(authority, root, repository, module)
    gate = _read_json(evidence / "gate.json")
    preflight_record = _read_json(evidence / "preflight.json")
    if set(gate) != GATE_KEYS or set(preflight_record) != PREFLIGHT_KEYS:
        raise IocError("gate or preflight schema is not exact")
    if gate.get("schema") != GATE_SCHEMA or gate.get("status") != "PASS":
        raise IocError("gate is not passed")
    if (
        preflight_record.get("schema") != PREFLIGHT_SCHEMA
        or preflight_record.get("status") != "PASS"
    ):
        raise IocError("preflight is not passed")
    _zero_counters(preflight_record.get("zero_science_counters"))
    if (
        gate.get("authority") != bound
        or gate.get("repository") != repository
        or gate.get("science_module") != _module_identity(module)
        or gate.get("authority_sha256") != _sha256_file(evidence / "authority.json")
        or preflight_record.get("authority_sha256") != _sha256_file(evidence / "authority.json")
        or preflight_record.get("gate_sha256") != _sha256_file(evidence / "gate.json")
        or preflight_record.get("repository") != repository
        or preflight_record.get("science_module") != _module_identity(module)
    ):
        raise IocError("gate or preflight evidence binding differs")
    runs_root = _safe_external(Path(bound["runs_root"]), root, create=True)
    run_root = runs_root / bound["run_id"]
    try:
        run_root.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise IocError("run identity has already been used") from exc
    os.chmod(run_root, 0o700)
    _write_once(
        run_root / "run.lock",
        {"run_id": bound["run_id"], "created_at": _utc_now(), "one_shot": True},
    )
    _write_once(run_root / "authority.json", bound)
    _write_once(run_root / "gate.json", gate)
    _write_once(run_root / "preflight.json", preflight_record)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "run_id": bound["run_id"],
        "project_root": str(root),
        "runs_root": str(runs_root),
        "release": dict(repository),
        "science_module": _module_identity(module),
        "science_execution": bound["science_execution"],
        "authority_sha256": _sha256_file(run_root / "authority.json"),
        "gate_sha256": _sha256_file(run_root / "gate.json"),
        "preflight_sha256": _sha256_file(run_root / "preflight.json"),
        "status_path": str(run_root / "status.json"),
        "events_path": str(run_root / "events.jsonl"),
        "terminal_inventory_path": str(run_root / "terminal-inventory.json"),
    }
    _write_once(run_root / "manifest.json", manifest)
    _write_event(
        run_root / "events.jsonl",
        {"schema": EVENT_SCHEMA, "event": "prepared", "run_id": bound["run_id"], "at": _utc_now()},
    )
    _publish_status(
        run_root,
        _status_value(
            bound["run_id"],
            "prepared",
            "prepared",
            0,
            0,
            0,
            "Prepared; awaiting operator foreground start",
        ),
    )
    return run_root / "manifest.json"


def _terminalize(
    run_root: Path,
    manifest: Mapping[str, Any],
    state: str,
    error_type: str | None,
    status: Mapping[str, Any],
) -> dict[str, Any]:
    path = run_root / "terminal-inventory.json"
    artifacts = []
    for item in sorted(run_root.rglob("*")):
        if item == path:
            continue
        if item.is_symlink() or not item.is_file():
            continue
        artifacts.append(
            {
                "path": item.relative_to(run_root).as_posix(),
                "size_bytes": item.stat().st_size,
                "sha256": _sha256_file(item),
            }
        )
    inventory = {
        "schema": TERMINAL_SCHEMA,
        "run_id": manifest["run_id"],
        "terminal_state": state,
        "at": _utc_now(),
        "error_type": error_type,
        "manifest_sha256": _sha256_file(run_root / "manifest.json"),
        "artifacts": artifacts,
        "status": dict(status),
    }
    _write_once(path, inventory)
    return inventory


def _validate_science_evidence_binding(
    value: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    manifest_path: Path,
    science_execution: Mapping[str, Any],
    result: Mapping[str, Any],
    require_complete: bool = True,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != SCIENCE_EVIDENCE_KEYS:
        raise IocError("science-evidence receipt schema is not exact")
    if value.get("schema") != SCIENCE_EVIDENCE_SCHEMA:
        raise IocError("science-evidence receipt schema is invalid")
    if value.get("ioc_run_id") != manifest.get("run_id"):
        raise IocError("science-evidence IOC run binding differs")
    if value.get("science_run_id") != science_execution.get("science_run_id"):
        raise IocError("science-evidence science run binding differs")
    if value.get("ioc_manifest_sha256") != _sha256_file(manifest_path):
        raise IocError("science-evidence manifest binding differs")
    for receipt_key, binding_key in (
        ("execution_freeze_sha256", "execution_freeze_sha256"),
        ("inventory_sha256", "inventory_sha256"),
    ):
        if value.get(receipt_key) != science_execution.get(binding_key):
            raise IocError(f"science-evidence {receipt_key} binding differs")
    data_root = science_execution.get("science_data_root")
    if not isinstance(data_root, Mapping):
        raise IocError("science-evidence data-root binding is invalid")
    if value.get("data_root_id") != data_root.get("data_root_id"):
        raise IocError("science-evidence data-root binding differs")
    if value.get("marker_sha256") != data_root.get("marker_sha256"):
        raise IocError("science-evidence marker binding differs")
    execution_binding = value.get("execution_binding_sha256")
    if execution_binding is not None:
        _require_sha(execution_binding, "science-evidence execution binding")
    elif require_complete:
        raise IocError("science-evidence execution binding is absent")
    if not isinstance(value.get("data_root_id"), str) or not value["data_root_id"]:
        raise IocError("science-evidence data-root ID is invalid")
    _require_sha(value.get("execution_freeze_sha256"), "science-evidence execution freeze")
    _require_sha(value.get("inventory_sha256"), "science-evidence inventory")
    _require_sha(value.get("marker_sha256"), "science-evidence marker")
    accounting = value.get("accounting")
    if not isinstance(accounting, Mapping) or set(accounting) != SCIENCE_EVIDENCE_ACCOUNTING_KEYS:
        raise IocError("science-evidence accounting is not exact")
    for key in SCIENCE_EVIDENCE_ACCOUNTING_KEYS:
        if (
            isinstance(accounting[key], bool)
            or not isinstance(accounting[key], int)
            or accounting[key] < 0
        ):
            raise IocError(f"science-evidence accounting is invalid: {key}")
    expected_accounting = science_execution.get("expected_accounting")
    if not isinstance(expected_accounting, Mapping) or (
        accounting["completed"] != result.get("completed")
        or accounting["checkpoint"] != result.get("checkpoint")
        or accounting["total"] != expected_accounting.get("cases")
        or accounting["primary_fits"] != expected_accounting.get("primary_fits")
        or accounting["solver_audits"] != expected_accounting.get("solver_audits")
        or not 0 <= accounting["checkpoint"] <= accounting["completed"] <= accounting["total"]
    ):
        raise IocError("science-evidence accounting binding differs")
    if require_complete and accounting["total"] != result.get("total"):
        raise IocError("science-evidence completion total differs")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or (
        require_complete and len(artifacts) != len(SCIENCE_EVIDENCE_ARTIFACT_PATHS)
    ):
        raise IocError("science-evidence artifact inventory is not exact")
    names: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, Mapping) or set(artifact) != {
            "name",
            "logical_path",
            "size_bytes",
            "sha256",
        }:
            raise IocError("science-evidence artifact entry is not exact")
        name = artifact["name"]
        if (
            not isinstance(name, str)
            or name not in SCIENCE_EVIDENCE_ARTIFACT_PATHS
            or name in names
        ):
            raise IocError("science-evidence artifact name is invalid")
        names.add(name)
        if artifact["logical_path"] != SCIENCE_EVIDENCE_ARTIFACT_PATHS[name]:
            raise IocError("science-evidence artifact path differs")
        if (
            isinstance(artifact["size_bytes"], bool)
            or not isinstance(artifact["size_bytes"], int)
            or artifact["size_bytes"] < 0
        ):
            raise IocError("science-evidence artifact size is invalid")
        _require_sha(artifact["sha256"], f"science-evidence artifact {name}")
    if require_complete and names != set(SCIENCE_EVIDENCE_ARTIFACT_PATHS):
        raise IocError("science-evidence artifact set is incomplete")
    if (
        not isinstance(value.get("hard_stop_present"), bool)
        or value.get("scientific_outcomes_visible") is not False
    ):
        raise IocError("science-evidence outcome boundary is invalid")
    return dict(value)


def _failure_receipt_evidence(
    run_root: Path,
    *,
    manifest: Mapping[str, Any],
    manifest_path: Path,
    latest_status: Mapping[str, Any],
) -> dict[str, bool]:
    receipt_path = run_root / "science-evidence-binding.json"
    present = receipt_path.is_file()
    valid = False
    if present:
        try:
            _validate_science_evidence_binding(
                _read_json(receipt_path),
                manifest=manifest,
                manifest_path=manifest_path,
                science_execution=manifest["science_execution"],
                result={
                    "completed": latest_status.get("completed"),
                    "checkpoint": latest_status.get("checkpoint"),
                },
                require_complete=False,
            )
            valid = True
        except Exception:  # noqa: BLE001 - invalid evidence must not mask terminal cause
            valid = False
    return {
        "science_evidence_receipt_present": present,
        "science_evidence_receipt_valid": valid,
        "science_evidence_receipt_incident": not valid,
    }


def run_foreground(manifest_path: Path, *, module: ScienceModule) -> dict[str, Any]:
    manifest_file = Path(manifest_path).resolve(strict=True)
    run_root = manifest_file.parent
    manifest = _read_json(manifest_file)
    expected_paths = {
        "status_path": str(run_root / "status.json"),
        "events_path": str(run_root / "events.jsonl"),
        "terminal_inventory_path": str(run_root / "terminal-inventory.json"),
    }
    if (
        set(manifest) != MANIFEST_KEYS
        or manifest.get("schema") != MANIFEST_SCHEMA
        or any(manifest.get(name) != path for name, path in expected_paths.items())
        or manifest.get("run_id") != run_root.name
    ):
        raise IocError("manifest is not exact or is at the wrong path")
    try:
        validate_ioc_science_execution_binding(
            manifest.get("science_execution"), ioc_run_id=manifest["run_id"]
        )
    except Exception as exc:
        raise IocError("science-execution manifest binding is invalid") from exc
    if not (run_root / "run.lock").is_file():
        raise IocError("persistent run lock is absent")
    lock = _read_json(run_root / "run.lock")
    if (
        set(lock) != {"run_id", "created_at", "one_shot"}
        or lock.get("run_id") != manifest["run_id"]
        or lock.get("one_shot") is not True
    ):
        raise IocError("persistent run lock is invalid")
    if (run_root / "terminal-inventory.json").exists():
        raise IocError("run identity is already terminal")
    status_before = _read_json(run_root / "status.json")
    _validate_status(status_before)
    if status_before["run_id"] != manifest["run_id"] or status_before["state"] != "prepared":
        raise IocError("run identity has already been started")
    root = _safe_project_root(Path(str(manifest["project_root"])))
    repository = repository_identity(root)
    if dict(manifest["release"]) != repository or repository.get("clean") is not True:
        raise IocError("release changed or repository is dirty")
    if run_root.parent != _safe_external(Path(str(manifest["runs_root"])), root):
        raise IocError("manifest runs root differs")
    for name, expected in (
        ("authority.json", manifest.get("authority_sha256")),
        ("gate.json", manifest.get("gate_sha256")),
        ("preflight.json", manifest.get("preflight_sha256")),
    ):
        if not isinstance(expected, str) or _sha256_file(run_root / name) != expected:
            raise IocError(f"{name} does not match the manifest")
    bound = _validate_authority(
        _read_json(run_root / "authority.json"),
        root,
        repository,
        module,
    )
    if bound["run_id"] != manifest["run_id"]:
        raise IocError("authority run identity differs from the manifest")
    if bound["science_execution"] != manifest["science_execution"]:
        raise IocError("science-execution authority and manifest bindings differ")
    if manifest.get("science_module") != _module_identity(module):
        raise IocError("science-module identity changed")
    if (run_root / "run.active").exists():
        raise IocError("run identity is already active")
    _write_once(
        run_root / "run.active",
        {"run_id": manifest["run_id"], "started_at": _utc_now(), "single_writer": True},
    )
    return _conduct_run(run_root, manifest, module=module)


def _conduct_run(
    run_root: Path, manifest: Mapping[str, Any], *, module: ScienceModule,
    development: bool = False,
) -> dict[str, Any]:
    """Shared foreground lifecycle for development and formal science."""
    manifest_file = run_root / "manifest.json"
    status_before = _read_json(run_root / "status.json")
    started_monotonic = time.monotonic()
    latest_status = {"value": status_before}

    def publish_progress(**fields: Any) -> Mapping[str, Any]:
        latest_status["value"] = _publish_status(
            run_root,
            _status_value(
                str(manifest["run_id"]),
                "running",
                str(fields.get("stage", "run")),
                int(fields.get("completed", 0)),
                int(fields.get("total", 0)),
                int(fields.get("checkpoint", fields.get("completed", 0))),
                "Foreground checkpoint updated",
                elapsed_seconds=time.monotonic() - started_monotonic,
            ),
        )
        return latest_status["value"]

    try:
        latest_status["value"] = _publish_status(
            run_root,
            _status_value(
                str(manifest["run_id"]),
                "running",
                "run",
                0,
                0,
                0,
                "Foreground conductor running",
            ),
        )
        _write_event(
            run_root / "events.jsonl",
            {
                "schema": EVENT_SCHEMA,
                "event": "run_started",
                "run_id": manifest["run_id"],
                "at": _utc_now(),
            },
        )
        result = module.run(run_root, manifest, publish_progress)
        if not isinstance(result, Mapping) or set(result) != {
            "completed",
            "total",
            "checkpoint",
        }:
            raise IocError("science module completion accounting is not exact")
        if any(
            isinstance(result[name], bool) or not isinstance(result[name], int) or result[name] < 0
            for name in ("completed", "total", "checkpoint")
        ):
            raise IocError("science module completion accounting is invalid")
        if (
            result["total"] == 0
            or result["completed"] != result["total"]
            or result["checkpoint"] != result["completed"]
        ):
            raise IocError("science module did not complete the exact workload")
        if development:
            if result["total"] != len(manifest["cases"]):
                raise IocError("Development case accounting differs")
        else:
            _validate_science_evidence_binding(
                _read_json(run_root / "science-evidence-binding.json"),
                manifest=manifest,
                manifest_path=manifest_file,
                science_execution=manifest["science_execution"],
                result=result,
            )
        terminal = _status_value(
            str(manifest["run_id"]),
            "complete",
            "terminal",
            result["completed"],
            result["total"],
            result["checkpoint"],
            "Foreground run complete; science remains sealed",
            terminal=True,
            elapsed_seconds=time.monotonic() - started_monotonic,
        )
        _write_event(
            run_root / "events.jsonl",
            {
                "schema": EVENT_SCHEMA,
                "event": "terminal",
                "run_id": manifest["run_id"],
                "state": "complete",
                "at": _utc_now(),
            },
        )
        _publish_status(run_root, terminal)
        inventory = _terminalize(run_root, manifest, "complete", None, terminal)
        return inventory
    except KeyboardInterrupt as exc:
        latest = latest_status["value"]
        receipt_evidence = {} if development else _failure_receipt_evidence(
            run_root,
            manifest=manifest,
            manifest_path=manifest_file,
            latest_status=latest,
        )
        terminal = _status_value(
            str(manifest["run_id"]),
            "controlled_stop",
            "terminal",
            int(latest.get("completed", 0)),
            int(latest.get("total", 0)),
            int(latest.get("checkpoint", 0)),
            "Operator-controlled stop; run identity consumed",
            error_type=type(exc).__name__,
            terminal=True,
            elapsed_seconds=time.monotonic() - started_monotonic,
        )
        _write_event(
            run_root / "events.jsonl",
            {
                "schema": EVENT_SCHEMA,
                "event": "controlled_stop",
                "run_id": manifest["run_id"],
                "at": _utc_now(),
                **receipt_evidence,
            },
        )
        _publish_status(run_root, terminal)
        _terminalize(run_root, manifest, "controlled_stop", type(exc).__name__, terminal)
        raise ControlledStop("operator interrupted the foreground conductor") from exc
    except BaseException as exc:
        latest = latest_status["value"]
        receipt_evidence = {} if development else _failure_receipt_evidence(
            run_root,
            manifest=manifest,
            manifest_path=manifest_file,
            latest_status=latest,
        )
        terminal = _status_value(
            str(manifest["run_id"]),
            "operational_failure",
            "terminal",
            int(latest.get("completed", 0)),
            int(latest.get("total", 0)),
            int(latest.get("checkpoint", 0)),
            "Critical failure stopped the foreground conductor",
            error_type=type(exc).__name__,
            terminal=True,
            elapsed_seconds=time.monotonic() - started_monotonic,
        )
        _write_event(
            run_root / "events.jsonl",
            {
                "schema": EVENT_SCHEMA,
                "event": "operational_failure",
                "run_id": manifest["run_id"],
                "at": _utc_now(),
                "error_type": type(exc).__name__,
                **receipt_evidence,
            },
        )
        _publish_status(run_root, terminal)
        _terminalize(run_root, manifest, "operational_failure", type(exc).__name__, terminal)
        raise


def observe_status(run_root: Path) -> dict[str, Any]:
    root = Path(run_root).resolve(strict=True)
    value = _read_json(root / "status.json")
    _validate_status(value)
    updated = _parse_time(value.get("updated_at"), "status.updated_at").timestamp()
    age = max(0.0, time.time() - updated)
    terminal = bool(value.get("terminal"))
    process_state = (
        "terminal" if terminal else "not_started" if value.get("state") == "prepared" else "stopped"
    )
    live_rss = value["rss_gib"]
    live_cpu = None
    if not terminal and value.get("pid"):
        try:
            process = psutil.Process(int(value["pid"]))
            process_state = (
                "running"
                if abs(process.create_time() - float(value.get("process_started_at_epoch", 0.0)))
                < 0.01
                else "stopped"
            )
            if process_state == "running":
                live_rss = process.memory_info().rss / 1024**3
                live_cpu = process.cpu_percent(interval=0.1)
        except (psutil.Error, OSError, ValueError):
            process_state = "stopped"
    return {
        **value,
        "observed_process_state": process_state,
        "observed_rss_gib": round(live_rss, 6),
        "observed_cpu_percent": live_cpu,
        "progress_age_seconds": round(age, 3),
        "progress_state": "terminal" if terminal else "recent" if age <= 180 else "waiting",
        # Compatibility names: this is foreground progress, not a periodic heartbeat.
        "heartbeat_age_seconds": round(age, 3),
        "heartbeat_state": "terminal" if terminal else "process_alive" if process_state == "running" else process_state,
    }


def develop(data_root: Path, *, run_id: str | None, module: ScienceModule,
            case_family: str | None = None, solver_check: bool = False) -> dict[str, Any]:
    """Prepare a distinct development attempt and use the existing conductor."""
    import uuid

    from .paths import repository_root
    from .pilot2_development import development_cases, solver_check_cases, verify_inputs

    if solver_check and case_family is not None:
        raise IocError("Choose either the solver check or a single case family")
    cases = solver_check_cases() if solver_check else development_cases()
    root = data_root.resolve(strict=True)
    verify_inputs(root)
    run_id = run_id or f"pilot2-ioc-dev-{uuid.uuid4().hex[:12]}"
    if not re.fullmatch(r"pilot2-ioc-dev-[a-zA-Z0-9_-]+", run_id):
        raise IocError("Development run IDs must start with pilot2-ioc-dev-")
    run_root = root / "development-runs" / run_id
    if run_root.parent.is_symlink():
        raise IocError("Development run directory must be local")
    run_root.mkdir(parents=True, exist_ok=False)
    repo = repository_root()
    manifest = {
        "schema": "recherche-development-v1", "run_id": run_id,
        "mode": "development", "data_root": str(root),
        "cases": [c for c in cases if case_family is None or c['family'] == case_family],
        "formal_qualification": False,
        "source_sha256": {
            str(p.relative_to(repo)): _sha256_file(p)
            for p in sorted((repo / "src/pulsar_pilot").glob("*.py"))
        },
        "input_receipt_sha256": _sha256_file(root / "metadata/provisioning-receipt.json"),
        "resources_sha256": _sha256_file(root / "metadata/resources.json"),
        "environment_sha256": _sha256_file(root / "metadata/development-environment.json"),
    }
    _write_once(run_root / "manifest.json", manifest)
    _publish_status(run_root, _status_value(run_id, "prepared", "prepared", 0,
                                          len(manifest["cases"]), 0, "Development fixture prepared"))
    _write_once(run_root / "run.active", {"run_id": run_id, "started_at": _utc_now()})
    return _conduct_run(run_root, manifest, module=module, development=True)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pilot 2 foreground operator conductor")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify-gate")
    verify.add_argument("--project-root", required=True, type=Path)
    verify.add_argument("--authority", required=True, type=Path)
    pre = sub.add_parser("preflight")
    pre.add_argument("--project-root", required=True, type=Path)
    pre.add_argument("--authority", required=True, type=Path)
    pre.add_argument("--evidence-root", required=True, type=Path)
    prep = sub.add_parser("prepare")
    prep.add_argument("--project-root", required=True, type=Path)
    prep.add_argument("--evidence-root", required=True, type=Path)
    run = sub.add_parser("run")
    run.add_argument("--manifest", required=True, type=Path)
    status = sub.add_parser("status")
    status.add_argument("--run-root", required=True, type=Path)
    dev = sub.add_parser("develop", help="Run the separate four-case development fixture")
    dev.add_argument("--data-root", required=True, type=Path)
    dev.add_argument("--run-id")
    selection = dev.add_mutually_exclusive_group()
    selection.add_argument("--case-family", choices=['main', 'phase_reference', 'annual', 'boundary'])
    selection.add_argument("--solver-check", action="store_true",
                           help="Check the two fixed annual fixtures and one ordinary control")
    args = parser.parse_args(argv)
    if args.command == "status":
        print(json.dumps(observe_status(args.run_root), sort_keys=True))
        return 0
    module = _load_default_module()
    if args.command == "develop":
        value = develop(args.data_root, run_id=args.run_id, module=module,
                        case_family=args.case_family, solver_check=args.solver_check)
    elif args.command == "verify-gate":
        value = verify_gate(args.project_root, args.authority, module=module)
    elif args.command == "preflight":
        value = preflight(args.project_root, args.authority, args.evidence_root, module=module)
    elif args.command == "prepare":
        value = {"manifest": str(prepare(args.project_root, args.evidence_root, module=module))}
    else:
        value = run_foreground(args.manifest, module=module)
    print(json.dumps(value, sort_keys=True, default=str))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return _main(argv)
    except ControlledStop:
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI boundary emits one fail-closed receipt.
        print(
            json.dumps(
                {"status": "FAIL", "error_type": type(exc).__name__, "message": str(exc)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUTHORITY_SCHEMA",
    "GATE4_AUTHORITY_SCHEMA",
    "GATE4_NETWORK_PROFILE",
    "GATE4_PREFLIGHT_SCHEMA",
    "GATE4_ZERO_SCIENCE_COUNTERS",
    "GATE_SCHEMA",
    "MANIFEST_SCHEMA",
    "PREFLIGHT_SCHEMA",
    "STATUS_SCHEMA",
    "TERMINAL_SCHEMA",
    "ZERO_SCIENCE_COUNTERS",
    "ControlledStop",
    "IocError",
    "ScienceModule",
    "main",
    "observe_status",
    "preflight",
    "prepare",
    "repository_identity",
    "run_foreground",
    "verify_gate",
]
