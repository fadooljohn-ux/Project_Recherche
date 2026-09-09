from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from .config import load_yaml
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot2_calibration_design import build_inventory, verify_design_freeze
from .provenance import hash_file, logical_path

CONFIG_PATH = "config/pilot2_calibration_v0.2.yaml"
EXECUTION_FREEZE_PATH = "protocol/PILOT2_CALIBRATION_EXECUTION_FREEZE_v0.2.json"
IMPLEMENTATION_FREEZE_PATH = "protocol/PILOT2_CALIBRATION_IMPLEMENTATION_FREEZE_v0.2.json"
STAGE_ORDER = (
    "gaussian_threshold_calibration",
    "commit_threshold_lock",
    "sealed_gaussian_evaluation",
    "structured_tail_evaluation",
    "injection_recovery_and_annual_map",
    "promotion_grade",
)
IMPLEMENTATION_PATHS = (
    "src/pulsar_pilot/pilot2_calibration_runtime.py",
    "src/pulsar_pilot/pilot2_calibration_grading.py",
)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def implementation_sha256() -> str:
    root = repository_root()
    digest = hashlib.sha256()
    for relative in IMPLEMENTATION_PATHS:
        path = root / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_execution_gate() -> dict[str, Any]:
    root = repository_root()
    design = verify_design_freeze()
    failures = list(design["failures"])
    path = root / EXECUTION_FREEZE_PATH
    if not path.is_file():
        failures.append("Calibration execution freeze is absent")
        return {"status": "locked", "failures": failures, "design": design}
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if freeze.get("status") != "frozen_before_first_pilot2_calibration_case":
        failures.append("Calibration execution freeze status is invalid")
    if freeze.get("observed_residual_access_authorized") is not False:
        failures.append("Observed residual access must remain prohibited")
    if freeze.get("observed_periodic_search_authorized") is not False:
        failures.append("Observed periodic search must remain prohibited")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        file_path = root / relative
        if not file_path.is_file() or hash_file(file_path, "sha256") != expected:
            failures.append(f"Execution hash mismatch: {relative}")
    config = load_yaml(root / CONFIG_PATH)
    inventory_hash = build_inventory(config)["inventory_sha256"]
    if freeze.get("inventory_sha256") != inventory_hash:
        failures.append("Execution inventory hash mismatch")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "design": design,
        "freeze_sha256": hash_file(path, "sha256"),
        "inventory_sha256": inventory_hash,
    }


def verify_implementation_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / IMPLEMENTATION_FREEZE_PATH
    if not path.is_file():
        return {"status": "fail", "failures": ["Implementation freeze is absent"]}
    freeze = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "implementation_frozen_execution_not_authorized":
        failures.append("Implementation freeze status is invalid")
    if freeze.get("calibration_execution_authorized") is not False:
        failures.append("Implementation freeze must not authorize calibration execution")
    if freeze.get("observed_residual_access_authorized") is not False:
        failures.append("Implementation freeze must prohibit observed-residual access")
    if freeze.get("science_cases_executed_during_validation") != 0:
        failures.append("Implementation validation must execute zero science cases")
    config = load_yaml(root / CONFIG_PATH)
    inventory_hash = build_inventory(config)["inventory_sha256"]
    if freeze.get("inventory_sha256") != inventory_hash:
        failures.append("Implementation inventory hash mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append("Aggregate implementation hash mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        file_path = root / relative
        if not file_path.is_file() or hash_file(file_path, "sha256") != expected:
            failures.append(f"Implementation file hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_sha256": hash_file(path, "sha256"),
        "implementation_sha256": implementation_sha256(),
        "inventory_sha256": inventory_hash,
    }


class CalibrationLedger:
    def __init__(
        self,
        data_root: Path,
        inventory_sha256: str,
        implementation_sha256: str,
    ):
        self.data_root = data_root
        self.path = data_root / "run_records/pilot2/calibration-v0.2-ledger.json"
        self.health_path = data_root / "run_records/pilot2/calibration-v0.2-health.json"
        self.dashboard_path = data_root / "derived/pilot2/calibration-dashboard/index.html"
        self.inventory_sha256 = inventory_sha256
        self.implementation_sha256 = implementation_sha256

    def empty(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "run_id": "pilot2-b1937-calibration-v0.2",
            "inventory_sha256": self.inventory_sha256,
            "implementation_sha256": self.implementation_sha256,
            "created_utc": _utc_now(),
            "updated_utc": _utc_now(),
            "active_stage": None,
            "active_stage_started_utc": None,
            "runtime_active": False,
            "runner_pid": None,
            "stage_status": {stage: "pending" for stage in STAGE_ORDER},
            "completed_cases": {},
            "checkpoints": [],
            "stage_results": {},
            "hard_stop": None,
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty()
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("inventory_sha256") != self.inventory_sha256:
            raise RuntimeError("Calibration ledger inventory hash mismatch")
        if state.get("implementation_sha256") != self.implementation_sha256:
            raise RuntimeError("Calibration ledger implementation hash mismatch")
        return state

    def save(self, state: dict[str, Any]) -> None:
        state["updated_utc"] = _utc_now()
        _atomic_json(self.path, state)
        self.write_health(state)

    def begin_stage(self, stage: str) -> dict[str, Any]:
        if stage not in STAGE_ORDER:
            raise ValueError(f"Unknown calibration stage: {stage}")
        state = self.load()
        if state["hard_stop"] is not None:
            raise RuntimeError("Calibration ledger contains a hard stop")
        index = STAGE_ORDER.index(stage)
        for predecessor in STAGE_ORDER[:index]:
            if state["stage_status"][predecessor] != "pass":
                raise RuntimeError(f"Stage predecessor is not passed: {predecessor}")
        if stage == "sealed_gaussian_evaluation":
            self.verify_threshold_lock()
        if state["active_stage"] != stage:
            state["active_stage_started_utc"] = _utc_now()
        state["active_stage"] = stage
        state["stage_status"][stage] = "running"
        self.save(state)
        return state

    def record_case(self, stage: str, case_id: str, artifact_path: Path) -> dict[str, Any]:
        state = self.load()
        if state["active_stage"] != stage or state["stage_status"][stage] != "running":
            raise RuntimeError("Case cannot be recorded outside the active running stage")
        relative = logical_path(artifact_path, self.data_root)
        record = {
            "stage": stage,
            "logical_path": relative,
            "bytes": artifact_path.stat().st_size,
            "sha256": hash_file(artifact_path, "sha256"),
        }
        prior = state["completed_cases"].get(case_id)
        if prior is not None and prior != record:
            raise RuntimeError(f"Case artifact differs from ledger: {case_id}")
        if prior is not None:
            return prior
        state["completed_cases"][case_id] = record
        stage_count = sum(item["stage"] == stage for item in state["completed_cases"].values())
        if stage_count % 25 == 0:
            state["checkpoints"].append(
                {
                    "stage": stage,
                    "completed_stage_cases": stage_count,
                    "completed_total_cases": len(state["completed_cases"]),
                    "recorded_utc": _utc_now(),
                }
            )
        self.save(state)
        return record

    def complete_stage(self, stage: str, result_path: Path, passed: bool) -> None:
        state = self.load()
        if state["active_stage"] != stage:
            raise RuntimeError("Only the active stage can be completed")
        result_record = {
            "logical_path": logical_path(result_path, self.data_root),
            "bytes": result_path.stat().st_size,
            "sha256": hash_file(result_path, "sha256"),
        }
        state.setdefault("stage_results", {})[stage] = result_record
        state["stage_status"][stage] = "pass" if passed else "fail"
        state["active_stage"] = None
        state["active_stage_started_utc"] = None
        if not passed:
            state["hard_stop"] = {
                "stage": stage,
                "reason": "stage_gate_failure",
                "recorded_utc": _utc_now(),
            }
        self.save(state)

    def commit_threshold_lock(self, threshold_result_path: Path) -> dict[str, Any]:
        state = self.load()
        if state["stage_status"]["gaussian_threshold_calibration"] != "pass":
            raise RuntimeError("Threshold cannot lock before Gaussian calibration passes")
        result = json.loads(threshold_result_path.read_text(encoding="utf-8"))
        threshold = result.get("threshold", {})
        if threshold.get("status") != "proposed_not_locked":
            raise RuntimeError("Threshold result is not a proposed calibration threshold")
        record = {
            "schema_version": 1,
            "status": "locked_before_sealed_evaluation",
            "value_delta_chi2": float(threshold["value_delta_chi2"]),
            "trigger_comparison": "strictly_greater_than_threshold",
            "source": {
                "logical_path": logical_path(threshold_result_path, self.data_root),
                "bytes": threshold_result_path.stat().st_size,
                "sha256": hash_file(threshold_result_path, "sha256"),
            },
            "inventory_sha256": self.inventory_sha256,
            "implementation_sha256": self.implementation_sha256,
            "recorded_utc": _utc_now(),
        }
        lock_path = self.data_root / "run_records/pilot2/calibration-threshold-lock-v0.2.json"
        _atomic_json(lock_path, record)
        state["stage_status"]["commit_threshold_lock"] = "pass"
        state["stage_results"]["commit_threshold_lock"] = {
            "logical_path": logical_path(lock_path, self.data_root),
            "bytes": lock_path.stat().st_size,
            "sha256": hash_file(lock_path, "sha256"),
        }
        self.save(state)
        return record

    def verify_threshold_lock(self) -> dict[str, Any]:
        state = self.load()
        item = state.get("stage_results", {}).get("commit_threshold_lock")
        if not item:
            raise RuntimeError("Sealed evaluation requires a committed threshold lock")
        path = self.data_root / item["logical_path"]
        if not path.is_file() or hash_file(path, "sha256") != item["sha256"]:
            raise RuntimeError("Threshold lock artifact hash mismatch")
        lock = json.loads(path.read_text(encoding="utf-8"))
        if lock.get("status") != "locked_before_sealed_evaluation":
            raise RuntimeError("Threshold lock status is invalid")
        if lock.get("inventory_sha256") != self.inventory_sha256:
            raise RuntimeError("Threshold lock inventory mismatch")
        return lock

    def verify_artifacts(self) -> dict[str, Any]:
        state = self.load()
        failures: list[str] = []
        for case_id, artifact in state["completed_cases"].items():
            path = self.data_root / artifact["logical_path"]
            if (
                not path.is_file()
                or path.stat().st_size != int(artifact["bytes"])
                or hash_file(path, "sha256") != artifact["sha256"]
            ):
                failures.append(case_id)
        return {
            "status": "pass" if not failures else "fail",
            "completed_cases": len(state["completed_cases"]),
            "failures": failures,
        }

    def health(self, state: dict[str, Any]) -> dict[str, Any]:
        stage = state["active_stage"]
        stage_count = (
            sum(item["stage"] == stage for item in state["completed_cases"].values())
            if stage
            else 0
        )
        elapsed_seconds = 0.0
        if stage and state.get("active_stage_started_utc"):
            started = datetime.fromisoformat(state["active_stage_started_utc"])
            elapsed_seconds = max(0.0, (datetime.now(UTC) - started).total_seconds())
        if state.get("runtime_active"):
            process_health = "running"
        elif stage:
            process_health = "paused_or_interrupted"
        else:
            process_health = "stopped"
        return {
            "schema_version": 1,
            "run_id": state["run_id"],
            "process_health": process_health,
            "runner_pid": state.get("runner_pid"),
            "active_stage": stage,
            "active_stage_elapsed_seconds": elapsed_seconds,
            "stage_status": state["stage_status"],
            "completed_total_cases": len(state["completed_cases"]),
            "completed_active_stage_cases": stage_count,
            "checkpoint_count": len(state["checkpoints"]),
            "last_checkpoint": state["checkpoints"][-1] if state["checkpoints"] else None,
            "last_heartbeat_utc": _utc_now(),
            "hard_stop": state["hard_stop"],
            "scientific_outcomes_sealed": True,
            "manual_refresh_command": (
                "PYTHONPATH=src pixi run python -m "
                "pulsar_pilot.pilot2_calibration_runtime health --data-root <PATH>"
            ),
        }

    def write_health(self, state: dict[str, Any]) -> dict[str, Any]:
        health = self.health(state)
        _atomic_json(self.health_path, health)
        self.dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        self.dashboard_path.write_text(render_dashboard_html(health), encoding="utf-8")
        return health


class HeartbeatService:
    """Write health-only status periodically while a stage runner is active."""

    def __init__(self, ledger: CalibrationLedger, interval_seconds: float = 30.0):
        if interval_seconds <= 0:
            raise ValueError("Heartbeat interval must be positive")
        self.ledger = ledger
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        state = self.ledger.load()
        state["runtime_active"] = True
        state["runner_pid"] = os.getpid()
        self.ledger.save(state)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.ledger.write_health(self.ledger.load())

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds + 1.0))
        state = self.ledger.load()
        state["runtime_active"] = False
        state["runner_pid"] = None
        self.ledger.save(state)


def run_stage(
    ledger: CalibrationLedger,
    stage: str,
    cases: list[dict[str, Any]],
    execute_case: Any,
    grade_stage: Any,
    *,
    heartbeat_interval_seconds: float = 30.0,
) -> dict[str, Any]:
    """Run one frozen stage with resume and integrity controls.

    The caller supplies the science executor. This function will not invoke it unless
    the separate execution freeze passes verification.
    """
    gate = verify_execution_gate()
    if gate["status"] != "pass":
        raise RuntimeError("Calibration execution is locked")
    integrity = ledger.verify_artifacts()
    if integrity["status"] != "pass":
        raise RuntimeError("Recorded calibration artifact integrity failure")
    state = ledger.begin_stage(stage)
    completed = state["completed_cases"]
    with HeartbeatService(ledger, heartbeat_interval_seconds):
        for case in cases:
            case_id = str(case["case_id"])
            if case_id in completed:
                continue
            artifact_path = Path(execute_case(case))
            ledger.record_case(stage, case_id, artifact_path)
    result = grade_stage()
    result_path = Path(result["result_path"])
    ledger.complete_stage(stage, result_path, result.get("status") == "pass")
    return result


def render_dashboard_html(health: dict[str, Any]) -> str:
    stage_rows = "".join(
        f"<tr><td>{stage}</td><td>{status.upper()}</td></tr>"
        for stage, status in health["stage_status"].items()
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="30">
<title>Project Recherche — B1937+21 Calibration Health</title>
<style>body{{font:16px system-ui;background:#10141b;color:#e8eef7;margin:2rem;}}
table{{border-collapse:collapse;min-width:44rem}}td,th{{padding:.55rem;border:1px solid #3b4656}}
.ok{{color:#77d69c}}.muted{{color:#aab6c7}}</style></head><body>
<h1>B1937+21 calibration health</h1>
<p class="ok">Scientific outcomes remain sealed.</p>
<p>Process: {health["process_health"]} · Active stage: {health["active_stage"] or "none"}</p>
<p>Active-stage elapsed: {health["active_stage_elapsed_seconds"]:.1f} seconds</p>
<p>Completed: {health["completed_total_cases"]} · Checkpoints: {health["checkpoint_count"]}</p>
<p class="muted">Last heartbeat: {health["last_heartbeat_utc"]}</p>
<table><tr><th>Stage</th><th>Status</th></tr>{stage_rows}</table>
<p class="muted">This page refreshes every 30 seconds. Use the recorded manual refresh command for JSON.</p>
</body></html>"""


def zero_case_dry_run(data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    root = repository_root()
    design = verify_design_freeze()
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_inventory(config)
    implementation_sha = implementation_sha256()
    ledger = CalibrationLedger(data_root, inventory["inventory_sha256"], implementation_sha)
    state = ledger.load()
    ledger.save(state)
    gate = verify_execution_gate()
    criteria = {
        "design_freeze_verified": design["status"] == "pass",
        "inventory_matches_design": inventory["inventory_sha256"] == design["inventory_sha256"],
        "execution_gate_locked": gate["status"] == "locked",
        "zero_cases_recorded": len(state["completed_cases"]) == 0,
        "all_stages_pending": all(value == "pending" for value in state["stage_status"].values()),
        "health_record_written": ledger.health_path.is_file(),
        "dashboard_written": ledger.dashboard_path.is_file(),
        "artifact_verification_passes": ledger.verify_artifacts()["status"] == "pass",
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "zero_case_integrity_dry_run",
        "criteria": criteria,
        "execution_gate": gate,
        "inventory_sha256": inventory["inventory_sha256"],
        "science_cases_executed": 0,
        "random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
        "health_record": logical_path(ledger.health_path, data_root),
        "dashboard": logical_path(ledger.dashboard_path, data_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-calibration-runtime")
    parser.add_argument(
        "command", choices=("verify-gate", "verify-implementation", "dry-run", "health")
    )
    parser.add_argument("--data-root")
    args = parser.parse_args()
    if args.command == "verify-gate":
        result = verify_execution_gate()
    elif args.command == "verify-implementation":
        result = verify_implementation_freeze()
    else:
        data_root = configured_data_root(args.data_root)
        if args.command == "dry-run":
            result = zero_case_dry_run(data_root)
        else:
            config = load_yaml(repository_root() / CONFIG_PATH)
            inventory = build_inventory(config)
            implementation_sha = implementation_sha256()
            ledger = CalibrationLedger(data_root, inventory["inventory_sha256"], implementation_sha)
            result = ledger.write_health(ledger.load())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status", "pass") not in {"fail"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
