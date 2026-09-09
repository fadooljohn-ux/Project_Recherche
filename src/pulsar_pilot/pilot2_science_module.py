from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .pilot2_injection_remediation_v023 import build_v023_inventory
from .pilot2_injection_runner_v028 import (
    initialize_temporary_validation_root,
    zero_case_dry_run,
)
from .pilot2_offline_resources import (
    build_environment_manifest,
    build_resource_manifest,
    current_platform_observation,
)
from .pilot2_release_contract import (
    INVENTORY_SHA256,
    IOC_EXPECTED_ACCOUNTING,
    IOC_MODULE_ID,
    IOC_MODULE_RELEASE_ID,
    load_science_controls,
    validate_ioc_science_execution_binding,
    verify_data_root_identity,
    verify_ioc_science_execution_authorization,
)
from .pilot2_runtime_core import execute, prepare_context
from .pilot2_trusted_data import exact_typed_equal, load_json

EVIDENCE_SCHEMA = "pilot2-science-evidence-binding-v1"
EVIDENCE_FILENAME = "science-evidence-binding.json"
ZERO_SCIENCE_COUNTERS = (
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
GATE4_RESULT_SCHEMA = "pilot2-ioc-gate4-preflight-result-v1"
GATE4_RESTORE_SCHEMA = "pilot2-ioc-gate4-restore-boundary-v1"
GATE4_ZERO_SCIENCE_COUNTERS = (
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
ARTIFACT_PATHS = {
    "ledger": "run_records/pilot2/calibration-v0.2.8-ledger.json",
    "terminal_result": "run_records/pilot2/injection-evaluation-v0.2.8.json",
    "annual_mask": "run_records/pilot2/annual-identifiability-mask-v0.2.8.json",
    "health": "run_records/pilot2/calibration-v0.2.8-health.json",
}


class ScienceAdapterError(RuntimeError):
    """Fail-closed compatibility error outside the scientific calculation."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ScienceAdapterError(f"{label} is not a SHA-256")
    return value


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = (json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except FileExistsError as exc:
        raise ScienceAdapterError("science evidence receipt already exists") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _manifest_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _gate4_restore_boundary(authority: Mapping[str, Any]) -> dict[str, Any]:
    binding = authority.get("restore_boundary")
    if not isinstance(binding, Mapping) or set(binding) != {"receipt_path", "receipt_sha256"}:
        raise ScienceAdapterError("Gate 4 restore-boundary binding is not exact")
    path = Path(str(binding["receipt_path"]))
    expected = _require_sha256(binding["receipt_sha256"], "restore-boundary receipt")
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ScienceAdapterError("Gate 4 restore-boundary receipt is unavailable")
    if _sha256_file(path) != expected:
        raise ScienceAdapterError("Gate 4 restore-boundary receipt hash differs")
    receipt = load_json(path, "Gate 4 restore-boundary receipt")
    required = {
        "schema",
        "status",
        "source_data_root_id",
        "restored_data_root_id",
        "source_manifest_sha256",
        "restored_manifest_sha256",
        "science_executed",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ScienceAdapterError("Gate 4 restore-boundary receipt schema is not exact")
    if (
        receipt["schema"] != GATE4_RESTORE_SCHEMA
        or receipt["status"] != "PASS"
        or receipt["science_executed"] is not False
        or receipt["source_data_root_id"] != authority["science_data_root"]["data_root_id"]
        or not isinstance(receipt["restored_data_root_id"], str)
        or not receipt["restored_data_root_id"]
    ):
        raise ScienceAdapterError("Gate 4 restore-boundary receipt did not pass")
    source_sha = _require_sha256(receipt["source_manifest_sha256"], "restore source manifest")
    restored_sha = _require_sha256(receipt["restored_manifest_sha256"], "restore target manifest")
    if source_sha != restored_sha:
        raise ScienceAdapterError("Gate 4 restore-boundary manifest hashes differ")
    return dict(receipt)


def _gate4_disposable_validation() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for attempt in (1, 2):
        with tempfile.TemporaryDirectory(prefix=f"pilot2-gate4-disposable-{attempt}-") as raw:
            root = Path(raw) / "data-root"
            initialize_temporary_validation_root(root, f"gate4-disposable-{attempt}")
            result = zero_case_dry_run(root)
            if (
                result.get("status") != "pass"
                or not isinstance(result.get("criteria"), dict)
                or len(result["criteria"]) != 13
                or not all(value is True for value in result["criteria"].values())
                or type(result.get("science_cases_executed")) is not int
                or result.get("science_cases_executed") != 0
                or type(result.get("random_draws_generated")) is not int
                or result.get("random_draws_generated") != 0
                or type(result.get("model_fits_executed")) is not int
                or result.get("model_fits_executed") != 0
                or type(result.get("periodic_scans_executed")) is not int
                or result.get("periodic_scans_executed") != 0
                or result.get("observed_residual_accessed") is not False
            ):
                raise ScienceAdapterError("Gate 4 disposable-root validation failed")
            records.append(
                {
                    "attempt": attempt,
                    "status": "PASS",
                    "criteria": dict(result["criteria"]),
                    "candidate_implementation_sha256": result["candidate_implementation_sha256"],
                    "candidate_science_control_sha256": result["candidate_science_control_sha256"],
                    "science_cases_executed": result["science_cases_executed"],
                    "random_draws_generated": result["random_draws_generated"],
                    "model_fits_executed": result["model_fits_executed"],
                    "periodic_scans_executed": result["periodic_scans_executed"],
                    "observed_residual_accessed": result["observed_residual_accessed"],
                }
            )
    if not exact_typed_equal(records[0]["criteria"], records[1]["criteria"]):
        raise ScienceAdapterError("Gate 4 disposable-root validations differ")
    for key in (
        "candidate_implementation_sha256",
        "candidate_science_control_sha256",
    ):
        if records[0][key] != records[1][key]:
            raise ScienceAdapterError(f"Gate 4 disposable-root {key} differs")
    return records


def _validate_unused_output_path(data_root: Path, relative: str) -> Path:
    logical = Path(relative)
    if logical.is_absolute() or ".." in logical.parts or logical.as_posix() != relative:
        raise ScienceAdapterError("Gate 4 setup-log path is not confined")
    current = data_root
    for part in logical.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ScienceAdapterError("Gate 4 setup-log parent is a symlink")
        if current.exists() and not current.is_dir():
            raise ScienceAdapterError("Gate 4 setup-log parent is not a directory")
    target = data_root / logical
    if target.exists() or target.is_symlink():
        raise ScienceAdapterError("Gate 4 setup-log destination is already used")
    return target


def _gate4_preflight(
    project_root: Path,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    _, _, runner = load_science_controls(project_root)
    if dict(authority["manifest_paths"]) != dict(runner["manifests"]):
        raise ScienceAdapterError("Gate 4 manifest paths differ from science controls")
    disposable = _gate4_disposable_validation()
    restore = _gate4_restore_boundary(authority)
    observed_host = current_platform_observation()
    host = authority["host"]
    expected_host = {
        key: host[key]
        for key in (
            "python_version",
            "macos",
            "kernel_machine",
            "process_machine",
            "pointer_bits",
        )
    }
    actual_host = {key: observed_host[key] for key in expected_host}
    if not exact_typed_equal(actual_host, expected_host):
        raise ScienceAdapterError("Gate 4 designated host identity differs")
    if _sha256_file(Path(sys.executable).resolve()) != host["python_executable_sha256"]:
        raise ScienceAdapterError("Gate 4 Python executable identity differs")
    root_path = Path(str(authority["science_data_root"]["canonical_path"]))
    if not root_path.is_absolute() or root_path.is_symlink() or not root_path.is_dir():
        raise ScienceAdapterError("Gate 4 science data root is not a real directory")
    data_root = root_path.resolve(strict=True)
    if str(data_root) != str(root_path):
        raise ScienceAdapterError("Gate 4 science data root is not canonical")
    root_identity = verify_data_root_identity(data_root, dict(authority["science_data_root"]))
    if root_identity.get("status") != "pass":
        raise ScienceAdapterError("Gate 4 science data-root identity failed")
    storage = os.statvfs(data_root)
    storage_record = {
        "block_size": int(storage.f_frsize),
        "total_bytes": int(storage.f_blocks * storage.f_frsize),
        "free_bytes": int(storage.f_bavail * storage.f_frsize),
    }
    if storage_record["free_bytes"] < host["minimum_free_bytes"]:
        raise ScienceAdapterError("Gate 4 designated storage is insufficient")
    setup_paths = [
        _validate_unused_output_path(data_root, relative)
        for relative in authority["setup_log_paths"]
    ]
    prohibited_science_paths = [data_root / logical for logical in ARTIFACT_PATHS.values()] + [
        data_root / runner["paths"]["case_root"]
    ]
    if any(path.exists() or path.is_symlink() for path in prohibited_science_paths):
        raise ScienceAdapterError("Gate 4 found pre-existing v0.2.8 science artifacts")
    resource_spec = authority["resource_manifest"]
    resource_manifest = build_resource_manifest(
        data_root,
        manifest_id=resource_spec["manifest_id"],
        local_repository_relative_path=resource_spec["local_repository_relative_path"],
        clock_override_relative_path=resource_spec["clock_override_relative_path"],
        entries=resource_spec["entries"],
        required_resource_classes=resource_spec["required_resource_classes"],
    )
    resource_sha256 = _manifest_sha256(resource_manifest)
    environment_spec = authority["environment_manifest"]
    environment_manifest = build_environment_manifest(
        project_root,
        manifest_id=environment_spec["manifest_id"],
        resource_manifest_sha256=resource_sha256,
        critical_modules=environment_spec["critical_modules"],
        allowed_environment=environment_spec["allowed_environment"],
    )
    environment_sha256 = _manifest_sha256(environment_manifest)
    inventory = build_v023_inventory()
    if inventory.get("inventory_sha256") != INVENTORY_SHA256:
        raise ScienceAdapterError("Gate 4 case inventory identity differs")
    cases = inventory["cases"]
    context_passes: list[dict[str, Any]] = []
    for number, setup_log_relative in enumerate(authority["setup_log_paths"], start=1):
        context = prepare_context(
            data_root,
            cases,
            resource_manifest=resource_manifest,
            resource_manifest_sha256=resource_sha256,
            environment_manifest_sha256=environment_sha256,
            setup_log_relative=setup_log_relative,
        )
        context_passes.append(
            {
                "pass": number,
                "setup_log_relative": setup_log_relative,
                "setup_log_sha256": _sha256_file(setup_paths[number - 1]),
                "input_binding": dict(context.input_binding),
            }
        )
        del context
    if any(path.is_symlink() or not path.is_file() for path in setup_paths):
        raise ScienceAdapterError("Gate 4 setup-log evidence is incomplete")
    if any(path.exists() or path.is_symlink() for path in prohibited_science_paths):
        raise ScienceAdapterError("Gate 4 context created a science artifact")
    if not exact_typed_equal(
        context_passes[0]["input_binding"], context_passes[1]["input_binding"]
    ):
        raise ScienceAdapterError("Gate 4 context bindings differ")
    counters = dict.fromkeys(GATE4_ZERO_SCIENCE_COUNTERS, 0)
    return {
        "schema": GATE4_RESULT_SCHEMA,
        "status": "PASS",
        "disposable_validations": disposable,
        "data_root_identity": dict(root_identity),
        "host_storage": {"host": actual_host, "storage": storage_record},
        "resource_manifest": resource_manifest,
        "resource_manifest_sha256": resource_sha256,
        "environment_manifest": environment_manifest,
        "environment_manifest_sha256": environment_sha256,
        "context_passes": context_passes,
        "restore_boundary": restore,
        "zero_science_counters": counters,
        "run_root_created": False,
        "science_executed": False,
    }


def _artifact_records(data_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for name, logical_path in ARTIFACT_PATHS.items():
        path = data_root / logical_path
        if path.is_symlink():
            raise ScienceAdapterError(f"science artifact is not a regular file: {name}")
        if not path.exists():
            continue
        if not path.is_file():
            raise ScienceAdapterError(f"science artifact is not a regular file: {name}")
        records.append(
            {
                "name": name,
                "logical_path": logical_path,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return records


def _ledger_evidence(data_root: Path) -> tuple[str | None, bool]:
    ledger_path = data_root / ARTIFACT_PATHS["ledger"]
    if ledger_path.is_symlink():
        raise ScienceAdapterError("science ledger is not a regular file")
    if not ledger_path.exists():
        return None, False
    if not ledger_path.is_file():
        raise ScienceAdapterError("science ledger is not a regular file")
    ledger = load_json(ledger_path, "IOC-bound Pilot 2 ledger")
    if not isinstance(ledger, Mapping):
        raise ScienceAdapterError("science ledger is not an object")
    binding = ledger.get("execution_binding_sha256")
    if binding is not None:
        _require_sha256(binding, "science ledger execution binding")
    return binding, ledger.get("hard_stop") is not None


def _receipt(
    *,
    binding: Mapping[str, Any],
    manifest_sha256: str,
    data_root: Path,
    completed: int,
    checkpoint: int,
) -> dict[str, Any]:
    execution_binding, hard_stop_present = _ledger_evidence(data_root)
    root = binding["science_data_root"]
    return {
        "schema": EVIDENCE_SCHEMA,
        "ioc_run_id": binding["ioc_run_id"],
        "science_run_id": binding["science_run_id"],
        "ioc_manifest_sha256": manifest_sha256,
        "execution_freeze_sha256": binding["execution_freeze_sha256"],
        "inventory_sha256": binding["inventory_sha256"],
        "data_root_id": root["data_root_id"],
        "marker_sha256": root["marker_sha256"],
        "execution_binding_sha256": execution_binding,
        "accounting": {
            "completed": completed,
            "total": IOC_EXPECTED_ACCOUNTING["cases"],
            "checkpoint": checkpoint,
            "primary_fits": IOC_EXPECTED_ACCOUNTING["primary_fits"],
            "solver_audits": IOC_EXPECTED_ACCOUNTING["solver_audits"],
        },
        "artifacts": _artifact_records(data_root),
        "hard_stop_present": hard_stop_present,
        "scientific_outcomes_visible": False,
    }


class Pilot2ScienceModule:
    module_id = IOC_MODULE_ID
    release_id = IOC_MODULE_RELEASE_ID

    def verify_gate(
        self,
        project_root: Path,
        science_execution: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        result = verify_ioc_science_execution_authorization(
            binding=science_execution,
            root=project_root,
        )
        return {
            "status": "PASS" if result.get("status") == "pass" else "FAIL",
            "repository_authorization": dict(result),
        }

    def preflight(
        self,
        project_root: Path,
        qualification: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if qualification is not None:
            return _gate4_preflight(project_root, qualification)
        result = verify_ioc_science_execution_authorization(root=project_root)
        return {
            "zero_science_counters": dict.fromkeys(ZERO_SCIENCE_COUNTERS, 0),
            "run_root_created": False,
            "science_executed": False,
            "repository_authorization_status": result.get("status"),
        }

    def run(
        self,
        run_root: Path,
        manifest: Mapping[str, Any],
        publish_status: Callable[..., Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        if manifest.get("schema") == "recherche-development-v1":
            from .pilot2_development import execute_development

            return execute_development(run_root, manifest, publish_status)
        if not isinstance(manifest, Mapping) or not isinstance(
            manifest.get("science_execution"), Mapping
        ):
            raise ScienceAdapterError("IOC manifest lacks the science execution binding")
        binding = validate_ioc_science_execution_binding(
            manifest["science_execution"], ioc_run_id=str(manifest.get("run_id", ""))
        )
        if binding["module_release_id"] != self.release_id:
            raise ScienceAdapterError("science-module release binding differs")

        root_path = Path(binding["science_data_root"]["canonical_path"])
        if not root_path.is_absolute():
            raise ScienceAdapterError("science data root is not absolute")
        data_root = root_path.resolve(strict=True)
        if str(data_root) != str(root_path):
            raise ScienceAdapterError("science data root path is not canonical")

        manifest_path = Path(run_root).resolve(strict=True) / "manifest.json"
        if (
            manifest_path.parent != Path(run_root).resolve(strict=True)
            or not manifest_path.is_file()
        ):
            raise ScienceAdapterError("IOC manifest path is invalid")
        manifest_sha256 = _sha256_file(manifest_path)
        latest = {"completed": 0, "checkpoint": 0}

        def publish_foreground(**fields: Any) -> Mapping[str, Any]:
            completed = fields.get("completed")
            checkpoint = fields.get("checkpoint")
            total = fields.get("total")
            if any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in (completed, checkpoint, total)
            ):
                raise ScienceAdapterError("runtime status accounting is invalid")
            if not (0 <= checkpoint <= completed <= total == IOC_EXPECTED_ACCOUNTING["cases"]):
                raise ScienceAdapterError("runtime status accounting differs")
            latest.update(completed=completed, checkpoint=checkpoint)
            return publish_status(
                stage=str(fields.get("stage", "run")),
                completed=completed,
                total=total,
                checkpoint=checkpoint,
            )

        result: Mapping[str, Any] | None = None
        caught: BaseException | None = None
        caught_traceback: Any = None
        try:
            raw_result = execute(
                data_root,
                ioc_binding=binding,
                ioc_manifest_sha256=manifest_sha256,
                publish_status=publish_foreground,
            )
            if not isinstance(raw_result, Mapping):
                raise ScienceAdapterError("science runtime result is not an object")
            result = raw_result
            completed = result.get("completed_injection_cases")
            if completed != IOC_EXPECTED_ACCOUNTING["cases"]:
                raise ScienceAdapterError("science runtime accounting is incomplete")
            if result.get("status") not in {"pass", "fail"}:
                raise ScienceAdapterError("science runtime returned a nonterminal status")
            _require_sha256(
                result.get("execution_binding_sha256"),
                "science runtime execution binding",
            )
            latest.update(completed=completed, checkpoint=completed)
        except BaseException as exc:  # noqa: BLE001 - interruption is a governed terminal class
            caught = exc
            caught_traceback = exc.__traceback__

        try:
            receipt = _receipt(
                binding=binding,
                manifest_sha256=manifest_sha256,
                data_root=data_root,
                completed=latest["completed"],
                checkpoint=latest["checkpoint"],
            )
            if caught is None and (
                result is None
                or result.get("execution_binding_sha256") != receipt["execution_binding_sha256"]
            ):
                caught = ScienceAdapterError("science runtime and ledger execution bindings differ")
                caught_traceback = caught.__traceback__
            _write_once(Path(run_root) / EVIDENCE_FILENAME, receipt)
        except BaseException as evidence_error:
            if caught is not None:
                caught.add_note("science evidence receipt could not be completed")
                raise caught.with_traceback(caught_traceback) from evidence_error
            raise
        if caught is not None:
            raise caught.with_traceback(caught_traceback)
        if result is None:
            raise ScienceAdapterError("science runtime produced no result")
        return {
            "completed": IOC_EXPECTED_ACCOUNTING["cases"],
            "total": IOC_EXPECTED_ACCOUNTING["cases"],
            "checkpoint": IOC_EXPECTED_ACCOUNTING["cases"],
        }


SCIENCE_MODULE = Pilot2ScienceModule()
