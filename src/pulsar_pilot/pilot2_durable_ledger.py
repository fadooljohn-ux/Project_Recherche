from __future__ import annotations

import errno
import fcntl
import json
import os
import sys
import threading
import uuid
from collections.abc import Iterable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from .pilot2_trusted_data import (
    TrustedDataError,
    load_json,
    require_exact_keys,
    require_nonempty_string,
    require_sha256,
    require_type,
)
from .provenance import hash_file, logical_path

RUN_ID = "pilot2-b1937-injection-remediation-v0.2.8"
STAGE = "injection_remediation_evaluation"
TOTAL_CASES = 344
LEDGER_SCHEMA_VERSION = 1
TERMINAL_RESULT_KEYS = {
    "schema_version",
    "run_id",
    "status",
    "inventory_sha256",
    "execution_binding_sha256",
    "completed_case_count",
    "authorized_primary_fits",
    "solver_audits",
    "annual_mask_sha256",
    "threshold_lock_sha256",
    "threshold_retuned",
    "observed_residual_vector_used",
    "observed_periodic_scan_executed",
    "promotion_grade_executed",
    "science_cases_executed_this_invocation",
    "payload",
}
GRADE_KEYS = {
    "schema_version",
    "stage",
    "status",
    "gates",
    "diagnostics",
    "observed_residual_vector_used",
    "observed_periodic_scan_executed",
}
GRADE_DIAGNOSTIC_KEYS = {
    "all_triggered_main_phase_error_role",
    "all_triggered_main_phase_error_p90_radians",
    "phase_reference_error_p90_radians",
    "strong_control_minimum_recovery",
    "frequency_recovery_rate",
    "median_amplitude_bias_fraction",
    "monotonic_periods",
    "bracketed_periods",
}
EXPECTED_GATE_NAMES = {
    "main_case_count",
    "phase_reference_case_count",
    "annual_case_count",
    "boundary_case_count",
    "canonical_toa_metrics",
    "toa_application_error",
    "fit_convergence",
    "solver_audit_count",
    "solver_audit_failures",
    "strong_control_recovery",
    "frequency_recovery",
    "median_amplitude_bias",
    "monotonic_periods",
    "bracketed_periods",
    "phase_reference_trigger_recovery",
    "phase_reference_error_p90",
    "annual_eligibility_violations",
    "injection_wall_hours",
    "peak_memory_gib",
    "complete_data_root_gib",
    "unexpected_material_warnings",
}
ANNUAL_MASK_TOP_LEVEL_KEYS = {
    "schema_version",
    "run_id",
    "status",
    "inventory_sha256",
    "execution_binding_sha256",
    "periods",
    "updated_utc",
}

LEDGER_KEYS = {
    "schema_version",
    "run_id",
    "inventory_sha256",
    "implementation_sha256",
    "science_control_sha256",
    "environment_manifest_sha256",
    "resource_manifest_sha256",
    "execution_binding_sha256",
    "created_utc",
    "updated_utc",
    "active_stage",
    "active_stage_started_utc",
    "stage_status",
    "completed_cases",
    "stage_results",
    "active_attempt",
    "attempt_history",
    "checkpoints",
    "hard_stop",
    "runtime_active",
    "runner_pid",
    "last_heartbeat_utc",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sync_regular_file(file_descriptor: int) -> None:
    os.fsync(file_descriptor)
    if sys.platform == "darwin":
        fcntl.fcntl(file_descriptor, fcntl.F_FULLFSYNC)


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_mkdirs(path: Path) -> None:
    missing: list[Path] = []
    cursor = path
    while not cursor.exists():
        missing.append(cursor)
        cursor = cursor.parent
    for directory in reversed(missing):
        directory.mkdir()
        sync_directory(directory.parent)


def durable_atomic_json(path: Path, value: Any) -> None:
    durable_mkdirs(path.parent)
    payload = (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            _sync_regular_file(handle.fileno())
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


class SingleWriterLock(AbstractContextManager["SingleWriterLock"]):
    """An OS-owned, nonblocking, version-specific writer lock."""

    def __init__(self, data_root: Path, release_id: str = RUN_ID):
        self.path = data_root / "run_records/pilot2/locks/pilot2-v0.2.8.lock"
        self.release_id = release_id
        self._handle: Any | None = None

    @property
    def held(self) -> bool:
        return self._handle is not None

    def acquire(self) -> SingleWriterLock:
        if self.held:
            raise RuntimeError("v0.2.8 writer lock is already held by this object")
        durable_mkdirs(self.path.parent)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.close()
            if error.errno in {errno.EACCES, errno.EAGAIN}:
                raise RuntimeError("another live v0.2.8 writer holds the data-root lock") from error
            raise
        metadata = {
            "schema_version": 1,
            "release_id": self.release_id,
            "pid": os.getpid(),
            "process_start_observed_utc": utc_now(),
            "host": os.uname().nodename,
            "lock_authority": "fcntl_flock_descriptor_lifetime",
        }
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
        handle.flush()
        _sync_regular_file(handle.fileno())
        sync_directory(self.path.parent)
        self._handle = handle
        return self

    def release(self) -> None:
        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def __enter__(self) -> Self:
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()


def _require_nullable_string(value: Any, label: str) -> None:
    if value is not None:
        require_nonempty_string(value, label)


def _validate_artifact(value: Any, label: str, completed_case: bool) -> None:
    expected = {"logical_path", "bytes", "sha256"}
    if completed_case:
        expected |= {"sequence", "family"}
    artifact = require_exact_keys(value, expected, label)
    require_nonempty_string(artifact["logical_path"], f"{label}.logical_path")
    require_sha256(artifact["sha256"], f"{label}.sha256")
    require_type(artifact["bytes"], int, f"{label}.bytes")
    if artifact["bytes"] < 0:
        raise TrustedDataError(f"{label}.bytes is negative")
    if completed_case:
        require_type(artifact["sequence"], int, f"{label}.sequence")
        if artifact["sequence"] < 1 or artifact["sequence"] > TOTAL_CASES:
            raise TrustedDataError(f"{label}.sequence is outside the inventory")
        require_nonempty_string(artifact["family"], f"{label}.family")


def _validate_attempt(value: Any, label: str, history: bool) -> None:
    keys = {
        "case_id",
        "sequence",
        "seed",
        "family",
        "artifact_logical_path",
        "execution_binding_sha256",
        "input_binding_sha256",
        "status",
        "started_utc",
    }
    if history:
        keys |= {"disposition", "recorded_utc"}
    attempt = require_exact_keys(value, keys, label)
    require_nonempty_string(attempt["case_id"], f"{label}.case_id")
    require_type(attempt["sequence"], int, f"{label}.sequence")
    require_type(attempt["seed"], int, f"{label}.seed")
    require_nonempty_string(attempt["family"], f"{label}.family")
    require_nonempty_string(attempt["artifact_logical_path"], f"{label}.artifact_logical_path")
    require_sha256(attempt["execution_binding_sha256"], f"{label}.execution_binding_sha256")
    require_sha256(attempt["input_binding_sha256"], f"{label}.input_binding_sha256")
    if attempt["status"] != "started_seed_consumed":
        raise TrustedDataError(f"{label}.status is invalid")
    require_nonempty_string(attempt["started_utc"], f"{label}.started_utc")
    if history:
        require_nonempty_string(attempt["disposition"], f"{label}.disposition")
        require_nonempty_string(attempt["recorded_utc"], f"{label}.recorded_utc")


def validate_ledger_state(
    value: Any,
    *,
    inventory_sha256: str,
    implementation_sha256: str,
    science_control_sha256: str,
    environment_manifest_sha256: str,
    resource_manifest_sha256: str,
) -> dict[str, Any]:
    state = require_exact_keys(value, LEDGER_KEYS, "v0.2.8 ledger")
    if state["schema_version"] != LEDGER_SCHEMA_VERSION or type(state["schema_version"]) is not int:
        raise TrustedDataError("v0.2.8 ledger schema version is invalid")
    if state["run_id"] != RUN_ID:
        raise TrustedDataError("v0.2.8 ledger run ID is invalid")
    expected_hashes = {
        "inventory_sha256": inventory_sha256,
        "implementation_sha256": implementation_sha256,
        "science_control_sha256": science_control_sha256,
        "environment_manifest_sha256": environment_manifest_sha256,
        "resource_manifest_sha256": resource_manifest_sha256,
    }
    for key, expected in expected_hashes.items():
        require_sha256(state[key], f"v0.2.8 ledger.{key}")
        if state[key] != expected:
            raise TrustedDataError(f"v0.2.8 ledger {key} mismatch")
    if state["execution_binding_sha256"] is not None:
        require_sha256(state["execution_binding_sha256"], "v0.2.8 ledger execution binding")
    require_nonempty_string(state["created_utc"], "v0.2.8 ledger.created_utc")
    require_nonempty_string(state["updated_utc"], "v0.2.8 ledger.updated_utc")
    _require_nullable_string(state["active_stage"], "v0.2.8 ledger.active_stage")
    _require_nullable_string(
        state["active_stage_started_utc"], "v0.2.8 ledger.active_stage_started_utc"
    )
    statuses = require_exact_keys(state["stage_status"], {STAGE}, "v0.2.8 stage status")
    status = statuses[STAGE]
    if type(status) is not str or status not in {"pending", "running", "pass", "fail"}:
        raise TrustedDataError("v0.2.8 stage status is invalid")
    completed = require_type(state["completed_cases"], dict, "v0.2.8 completed cases")
    if len(completed) > TOTAL_CASES:
        raise TrustedDataError("v0.2.8 ledger contains more than 344 completed cases")
    sequences: set[int] = set()
    for case_id, artifact in completed.items():
        require_nonempty_string(case_id, "v0.2.8 completed case ID")
        _validate_artifact(artifact, f"v0.2.8 completed case {case_id}", True)
        if artifact["sequence"] in sequences:
            raise TrustedDataError("v0.2.8 ledger contains a duplicate sequence")
        sequences.add(artifact["sequence"])
    stage_results = require_type(state["stage_results"], dict, "v0.2.8 stage results")
    if set(stage_results) - {"terminal_result", "annual_mask"}:
        raise TrustedDataError("v0.2.8 ledger contains an unknown stage result")
    for name, artifact in stage_results.items():
        _validate_artifact(artifact, f"v0.2.8 stage result {name}", False)
    active_attempt = state["active_attempt"]
    if active_attempt is not None:
        _validate_attempt(active_attempt, "v0.2.8 active attempt", False)
    history = require_type(state["attempt_history"], list, "v0.2.8 attempt history")
    for index, attempt in enumerate(history):
        _validate_attempt(attempt, f"v0.2.8 attempt history[{index}]", True)
    checkpoints = require_type(state["checkpoints"], list, "v0.2.8 checkpoints")
    prior_count = -1
    for index, checkpoint in enumerate(checkpoints):
        item = require_exact_keys(
            checkpoint,
            {"completed_cases", "recorded_utc"},
            f"v0.2.8 checkpoint[{index}]",
        )
        require_type(item["completed_cases"], int, f"v0.2.8 checkpoint[{index}].completed_cases")
        require_nonempty_string(item["recorded_utc"], f"v0.2.8 checkpoint[{index}].recorded_utc")
        if item["completed_cases"] <= prior_count or item["completed_cases"] > TOTAL_CASES:
            raise TrustedDataError("v0.2.8 checkpoints regress or exceed inventory")
        prior_count = item["completed_cases"]
    hard_stop = state["hard_stop"]
    if hard_stop is not None:
        item = require_exact_keys(
            hard_stop,
            {"reason", "stage", "detail", "recorded_utc", "case_id"},
            "v0.2.8 hard stop",
        )
        for key in ("reason", "stage", "detail", "recorded_utc"):
            require_nonempty_string(item[key], f"v0.2.8 hard stop.{key}")
        _require_nullable_string(item["case_id"], "v0.2.8 hard stop.case_id")
    require_type(state["runtime_active"], bool, "v0.2.8 runtime_active")
    if state["runner_pid"] is not None:
        require_type(state["runner_pid"], int, "v0.2.8 runner_pid")
    _require_nullable_string(state["last_heartbeat_utc"], "v0.2.8 last heartbeat")

    if status == "pending":
        if completed or stage_results or active_attempt is not None or hard_stop is not None:
            raise TrustedDataError("v0.2.8 pending ledger contains execution state")
        if state["active_stage"] is not None or state["execution_binding_sha256"] is not None:
            raise TrustedDataError("v0.2.8 pending ledger contains an active binding")
    elif status == "running":
        if state["active_stage"] != STAGE or state["active_stage_started_utc"] is None:
            raise TrustedDataError("v0.2.8 running ledger lacks active stage identity")
        if hard_stop is not None or state["execution_binding_sha256"] is None:
            raise TrustedDataError("v0.2.8 running ledger has contradictory terminal state")
    elif status == "pass":
        if len(completed) != TOTAL_CASES or set(stage_results) != {
            "terminal_result",
            "annual_mask",
        }:
            raise TrustedDataError("v0.2.8 PASS lacks 344 cases and both terminal artifacts")
        if active_attempt is not None or hard_stop is not None:
            raise TrustedDataError("v0.2.8 PASS contains active attempt or hard stop")
        if state["active_stage"] is not None or state["runtime_active"]:
            raise TrustedDataError("v0.2.8 PASS still reports an active runtime")
    else:
        if hard_stop is None or state["active_stage"] is not None or state["runtime_active"]:
            raise TrustedDataError("v0.2.8 FAIL lacks terminal hard-stop invariants")
    if state["runtime_active"] != (state["runner_pid"] is not None):
        raise TrustedDataError("v0.2.8 runtime-active and runner-PID fields disagree")
    return state


def validate_terminal_result(
    value: Any,
    *,
    inventory_sha256: str,
    execution_binding_sha256: str,
    annual_mask_sha256: str,
) -> dict[str, Any]:
    result = require_exact_keys(value, TERMINAL_RESULT_KEYS, "v0.2.8 terminal result")
    if result["schema_version"] != 1 or type(result["schema_version"]) is not int:
        raise TrustedDataError("v0.2.8 terminal-result schema is invalid")
    if result["run_id"] != RUN_ID or result["status"] != "pass":
        raise TrustedDataError("v0.2.8 terminal-result identity or status is invalid")
    if result["inventory_sha256"] != inventory_sha256:
        raise TrustedDataError("v0.2.8 terminal-result inventory differs")
    if result["execution_binding_sha256"] != execution_binding_sha256:
        raise TrustedDataError("v0.2.8 terminal-result execution binding differs")
    if result["annual_mask_sha256"] != annual_mask_sha256:
        raise TrustedDataError("v0.2.8 terminal-result annual-mask binding differs")
    require_sha256(result["threshold_lock_sha256"], "v0.2.8 terminal threshold lock")
    expected_integers = {
        "completed_case_count": TOTAL_CASES,
        "authorized_primary_fits": 688,
        "solver_audits": 35,
    }
    for key, expected in expected_integers.items():
        if type(result[key]) is not int or result[key] != expected:
            raise TrustedDataError(f"v0.2.8 terminal-result {key} is invalid")
    require_type(
        result["science_cases_executed_this_invocation"],
        int,
        "v0.2.8 terminal invocation case count",
    )
    if not 0 <= result["science_cases_executed_this_invocation"] <= TOTAL_CASES:
        raise TrustedDataError("v0.2.8 terminal invocation case count is outside inventory")
    for key in (
        "threshold_retuned",
        "observed_residual_vector_used",
        "observed_periodic_scan_executed",
        "promotion_grade_executed",
    ):
        if result[key] is not False:
            raise TrustedDataError(f"v0.2.8 terminal boundary differs: {key}")
    payload = require_exact_keys(result["payload"], GRADE_KEYS, "v0.2.8 terminal grade")
    if (
        payload["schema_version"] != 1
        or type(payload["schema_version"]) is not int
        or payload["stage"] != STAGE
        or payload["status"] != "pass"
    ):
        raise TrustedDataError("v0.2.8 terminal grade identity or status is invalid")
    if (
        payload["observed_residual_vector_used"] is not False
        or payload["observed_periodic_scan_executed"] is not False
    ):
        raise TrustedDataError("v0.2.8 terminal grade crosses observed-data boundary")
    require_exact_keys(payload["diagnostics"], GRADE_DIAGNOSTIC_KEYS, "v0.2.8 diagnostics")
    gates = require_type(payload["gates"], list, "v0.2.8 terminal gates")
    names: set[str] = set()
    for index, raw_gate in enumerate(gates):
        gate = require_exact_keys(
            raw_gate,
            {"name", "observed", "comparator", "limit", "status"},
            f"v0.2.8 gate[{index}]",
        )
        name = require_nonempty_string(gate["name"], f"v0.2.8 gate[{index}].name")
        require_nonempty_string(gate["comparator"], f"v0.2.8 gate[{index}].comparator")
        if gate["status"] != "pass" or name in names:
            raise TrustedDataError("v0.2.8 terminal gates contain failure or duplicate")
        names.add(name)
    if names != EXPECTED_GATE_NAMES:
        raise TrustedDataError("v0.2.8 terminal gate set is not exact")
    return result


def validate_terminal_annual_mask(
    value: Any,
    *,
    inventory_sha256: str,
    execution_binding_sha256: str,
) -> dict[str, Any]:
    mask = require_exact_keys(value, ANNUAL_MASK_TOP_LEVEL_KEYS, "v0.2.8 annual mask")
    if mask["schema_version"] != 1 or type(mask["schema_version"]) is not int:
        raise TrustedDataError("v0.2.8 annual-mask schema is invalid")
    if mask["run_id"] != RUN_ID or mask["status"] != "complete":
        raise TrustedDataError("v0.2.8 annual-mask identity or status is invalid")
    if mask["inventory_sha256"] != inventory_sha256:
        raise TrustedDataError("v0.2.8 annual-mask inventory differs")
    if mask["execution_binding_sha256"] != execution_binding_sha256:
        raise TrustedDataError("v0.2.8 annual-mask execution binding differs")
    require_type(mask["periods"], list, "v0.2.8 annual-mask periods")
    require_nonempty_string(mask["updated_utc"], "v0.2.8 annual-mask updated time")
    return mask


def _synchronized(method: Any) -> Any:
    @wraps(method)
    def wrapped(self: V028Ledger, *args: Any, **kwargs: Any) -> Any:
        with self._thread_lock:
            return method(self, *args, **kwargs)

    return wrapped


class V028Ledger:
    def __init__(
        self,
        data_root: Path,
        *,
        inventory_sha256: str,
        implementation_sha256: str,
        science_control_sha256: str,
        environment_manifest_sha256: str,
        resource_manifest_sha256: str,
    ):
        self.data_root = data_root
        self.path = data_root / "run_records/pilot2/calibration-v0.2.8-ledger.json"
        self.health_path = data_root / "run_records/pilot2/calibration-v0.2.8-health.json"
        self.inventory_sha256 = inventory_sha256
        self.implementation_sha256 = implementation_sha256
        self.science_control_sha256 = science_control_sha256
        self.environment_manifest_sha256 = environment_manifest_sha256
        self.resource_manifest_sha256 = resource_manifest_sha256
        self._thread_lock = threading.RLock()

    def empty(self) -> dict[str, Any]:
        now = utc_now()
        return {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "run_id": RUN_ID,
            "inventory_sha256": self.inventory_sha256,
            "implementation_sha256": self.implementation_sha256,
            "science_control_sha256": self.science_control_sha256,
            "environment_manifest_sha256": self.environment_manifest_sha256,
            "resource_manifest_sha256": self.resource_manifest_sha256,
            "execution_binding_sha256": None,
            "created_utc": now,
            "updated_utc": now,
            "active_stage": None,
            "active_stage_started_utc": None,
            "stage_status": {STAGE: "pending"},
            "completed_cases": {},
            "stage_results": {},
            "active_attempt": None,
            "attempt_history": [],
            "checkpoints": [],
            "hard_stop": None,
            "runtime_active": False,
            "runner_pid": None,
            "last_heartbeat_utc": None,
        }

    def validate(self, state: Any) -> dict[str, Any]:
        return validate_ledger_state(
            state,
            inventory_sha256=self.inventory_sha256,
            implementation_sha256=self.implementation_sha256,
            science_control_sha256=self.science_control_sha256,
            environment_manifest_sha256=self.environment_manifest_sha256,
            resource_manifest_sha256=self.resource_manifest_sha256,
        )

    def load(self) -> dict[str, Any]:
        with self._thread_lock:
            if not self.path.exists():
                return self.empty()
            return self.validate(load_json(self.path, "v0.2.8 ledger"))

    def save(self, state: dict[str, Any]) -> None:
        with self._thread_lock:
            state["updated_utc"] = utc_now()
            self.validate(state)
            durable_atomic_json(self.path, state)
            self.write_health(state)

    def write_health(self, state: dict[str, Any]) -> dict[str, Any]:
        with self._thread_lock:
            self.validate(state)
            health = {
                "schema_version": 1,
                "run_id": RUN_ID,
                "process_state": "running" if state["runtime_active"] else "stopped",
                "runner_pid": state["runner_pid"],
                "stage_status": state["stage_status"][STAGE],
                "completed_cases": len(state["completed_cases"]),
                "total_cases": TOTAL_CASES,
                "checkpoint_count": len(state["checkpoints"]),
                "active_attempt_present": state["active_attempt"] is not None,
                "hard_stop_present": state["hard_stop"] is not None,
                "last_heartbeat_utc": state["last_heartbeat_utc"],
                "scientific_outcomes_in_health_record": False,
            }
            durable_atomic_json(self.health_path, health)
            return health

    def verify_artifacts(self) -> dict[str, Any]:
        state = self.load()
        failures: list[str] = []
        for case_id, artifact in state["completed_cases"].items():
            path = self.data_root / artifact["logical_path"]
            if (
                not path.is_file()
                or path.stat().st_size != artifact["bytes"]
                or hash_file(path, "sha256") != artifact["sha256"]
            ):
                failures.append(f"completed_case:{case_id}")
        for name, artifact in state["stage_results"].items():
            path = self.data_root / artifact["logical_path"]
            if (
                not path.is_file()
                or path.stat().st_size != artifact["bytes"]
                or hash_file(path, "sha256") != artifact["sha256"]
            ):
                failures.append(f"stage_result:{name}")
        return {
            "status": "pass" if not failures else "fail",
            "completed_cases": len(state["completed_cases"]),
            "stage_results": len(state["stage_results"]),
            "failures": failures,
        }

    @_synchronized
    def begin_stage(self, execution_binding_sha256: str) -> None:
        require_sha256(execution_binding_sha256, "execution binding")
        state = self.load()
        if state["stage_status"][STAGE] != "pending":
            raise RuntimeError("v0.2.8 stage is not pending")
        state["execution_binding_sha256"] = execution_binding_sha256
        state["active_stage"] = STAGE
        state["active_stage_started_utc"] = utc_now()
        state["stage_status"][STAGE] = "running"
        state["runtime_active"] = True
        state["runner_pid"] = os.getpid()
        state["last_heartbeat_utc"] = utc_now()
        self.save(state)

    @_synchronized
    def resume_runtime(self, execution_binding_sha256: str) -> None:
        require_sha256(execution_binding_sha256, "execution binding")
        state = self.load()
        if state["stage_status"][STAGE] != "running" or state["active_stage"] != STAGE:
            raise RuntimeError("v0.2.8 ledger is not in a resumable running state")
        if state["execution_binding_sha256"] != execution_binding_sha256:
            raise RuntimeError("v0.2.8 resume execution binding differs")
        state["runtime_active"] = True
        state["runner_pid"] = os.getpid()
        state["last_heartbeat_utc"] = utc_now()
        self.save(state)

    @_synchronized
    def begin_attempt(
        self,
        *,
        case_id: str,
        sequence: int,
        seed: int,
        family: str,
        artifact_path: Path,
        execution_binding_sha256: str,
        input_binding_sha256: str,
    ) -> None:
        state = self.load()
        if state["stage_status"][STAGE] != "running" or state["active_attempt"] is not None:
            raise RuntimeError("v0.2.8 cannot begin an attempt in the current ledger state")
        if case_id in state["completed_cases"]:
            raise RuntimeError("v0.2.8 cannot consume an already completed case")
        state["active_attempt"] = {
            "case_id": case_id,
            "sequence": sequence,
            "seed": seed,
            "family": family,
            "artifact_logical_path": logical_path(artifact_path, self.data_root),
            "execution_binding_sha256": execution_binding_sha256,
            "input_binding_sha256": input_binding_sha256,
            "status": "started_seed_consumed",
            "started_utc": utc_now(),
        }
        self.save(state)

    @_synchronized
    def record_case(self, case_id: str, sequence: int, family: str, path: Path) -> None:
        state = self.load()
        attempt = state["active_attempt"]
        if attempt is None or attempt["case_id"] != case_id:
            raise RuntimeError("v0.2.8 case commit does not match the active attempt")
        state["completed_cases"][case_id] = {
            "sequence": sequence,
            "family": family,
            "logical_path": logical_path(path, self.data_root),
            "bytes": path.stat().st_size,
            "sha256": hash_file(path, "sha256"),
        }
        count = len(state["completed_cases"])
        if count % 25 == 0 or count == TOTAL_CASES:
            state["checkpoints"].append({"completed_cases": count, "recorded_utc": utc_now()})
        self.save(state)

    @_synchronized
    def clear_attempt(self, disposition: str) -> None:
        state = self.load()
        attempt = state["active_attempt"]
        if attempt is None:
            raise RuntimeError("v0.2.8 has no active attempt to clear")
        state["attempt_history"].append(
            {**attempt, "disposition": disposition, "recorded_utc": utc_now()}
        )
        state["active_attempt"] = None
        self.save(state)

    @_synchronized
    def heartbeat(self) -> None:
        state = self.load()
        if state["stage_status"][STAGE] != "running":
            return
        state["last_heartbeat_utc"] = utc_now()
        self.save(state)

    @_synchronized
    def commit_stage_result(self, name: str, path: Path) -> None:
        if name not in {"terminal_result", "annual_mask"}:
            raise ValueError(f"unknown v0.2.8 stage result {name!r}")
        state = self.load()
        state["stage_results"][name] = {
            "logical_path": logical_path(path, self.data_root),
            "bytes": path.stat().st_size,
            "sha256": hash_file(path, "sha256"),
        }
        self.save(state)

    @_synchronized
    def complete_pass(self, expected_case_ids: Iterable[str]) -> dict[str, Any]:
        state = self.load()
        if set(state["completed_cases"]) != set(expected_case_ids):
            raise RuntimeError("v0.2.8 terminal case membership is not exact")
        if set(state["stage_results"]) != {"terminal_result", "annual_mask"}:
            raise RuntimeError("v0.2.8 terminal result or annual mask is absent")
        if state["active_attempt"] is not None:
            raise RuntimeError("v0.2.8 cannot pass with an active attempt")
        state["active_stage"] = None
        state["active_stage_started_utc"] = None
        state["stage_status"][STAGE] = "pass"
        state["runtime_active"] = False
        state["runner_pid"] = None
        state["last_heartbeat_utc"] = utc_now()
        self.save(state)
        return self.verify_terminal_pass(expected_case_ids)

    @_synchronized
    def fail(self, reason: str, detail: str, case_id: str | None = None) -> None:
        state = self.load()
        if state["active_attempt"] is not None:
            attempt = state["active_attempt"]
            state["attempt_history"].append(
                {
                    **attempt,
                    "disposition": "consumed_terminal_hard_stop",
                    "recorded_utc": utc_now(),
                }
            )
            state["active_attempt"] = None
        state["active_stage"] = None
        state["active_stage_started_utc"] = None
        state["stage_status"][STAGE] = "fail"
        state["runtime_active"] = False
        state["runner_pid"] = None
        state["last_heartbeat_utc"] = utc_now()
        state["hard_stop"] = {
            "reason": reason,
            "stage": STAGE,
            "detail": detail,
            "recorded_utc": utc_now(),
            "case_id": case_id,
        }
        self.save(state)

    def verify_terminal_pass(self, expected_case_ids: Iterable[str]) -> dict[str, Any]:
        state = self.load()
        failures: list[str] = []
        if state["stage_status"][STAGE] != "pass":
            failures.append("stage_not_pass")
        if set(state["completed_cases"]) != set(expected_case_ids):
            failures.append("case_membership_mismatch")
        artifacts = self.verify_artifacts()
        failures.extend(artifacts["failures"])
        if not failures:
            result_artifact = state["stage_results"]["terminal_result"]
            mask_artifact = state["stage_results"]["annual_mask"]
            result = load_json(self.data_root / result_artifact["logical_path"], "v0.2.8 result")
            mask = load_json(self.data_root / mask_artifact["logical_path"], "v0.2.8 annual mask")
            try:
                validate_terminal_annual_mask(
                    mask,
                    inventory_sha256=self.inventory_sha256,
                    execution_binding_sha256=state["execution_binding_sha256"],
                )
                validate_terminal_result(
                    result,
                    inventory_sha256=self.inventory_sha256,
                    execution_binding_sha256=state["execution_binding_sha256"],
                    annual_mask_sha256=mask_artifact["sha256"],
                )
            except TrustedDataError as error:
                failures.append(str(error))
        return {
            "status": "pass" if not failures else "fail",
            "completed_cases": len(state["completed_cases"]),
            "failures": failures,
        }

    def already_complete(self, expected_case_ids: Iterable[str]) -> bool:
        state = self.load()
        if state["stage_status"][STAGE] != "pass":
            return False
        verification = self.verify_terminal_pass(expected_case_ids)
        if verification["status"] != "pass":
            raise RuntimeError(f"v0.2.8 false-complete ledger: {verification['failures']}")
        return True
