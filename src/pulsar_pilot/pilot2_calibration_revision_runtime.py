from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .config import load_yaml
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot2_calibration_revision_design import (
    build_revision_inventory,
    verify_revision_freeze,
)
from .pilot2_calibration_runtime import (
    CalibrationLedger,
    _atomic_json,
    _utc_now,
)
from .provenance import hash_file, logical_path

CONFIG_PATH = "config/pilot2_calibration_v0.2.1.yaml"
IMPLEMENTATION_FREEZE_PATH = "protocol/PILOT2_CALIBRATION_IMPLEMENTATION_FREEZE_v0.2.1.json"
EXECUTION_FREEZE_PATH = "protocol/PILOT2_CALIBRATION_EXECUTION_FREEZE_v0.2.1.json"
IMPLEMENTATION_PATHS = (
    "src/pulsar_pilot/pilot2_calibration_revision_runtime.py",
    "src/pulsar_pilot/pilot2_calibration_revision_grading.py",
    "src/pulsar_pilot/pilot2_calibration_revision_executor.py",
    "src/pulsar_pilot/pilot2_calibration_runtime.py",
)


def implementation_sha256() -> str:
    root = repository_root()
    digest = hashlib.sha256()
    for relative in IMPLEMENTATION_PATHS:
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((root / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_implementation_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / IMPLEMENTATION_FREEZE_PATH
    if not path.is_file():
        return {"status": "fail", "failures": ["Revision implementation freeze is absent"]}
    freeze = json.loads(path.read_text())
    failures: list[str] = []
    if freeze.get("status") != "implementation_frozen_execution_not_authorized":
        failures.append("Revision implementation status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append("Revision implementation freeze authorizes execution")
    if freeze.get("science_cases_executed_during_validation") != 0:
        failures.append("Revision implementation validation was not zero-case")
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("Revision implementation inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append("Revision aggregate implementation mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"Revision implementation hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "implementation_sha256": implementation_sha256(),
        "inventory_sha256": inventory["inventory_sha256"],
        "freeze_sha256": hash_file(path, "sha256"),
    }


def verify_execution_gate() -> dict[str, Any]:
    root = repository_root()
    design = verify_revision_freeze()
    implementation = verify_implementation_freeze()
    failures = list(design["failures"]) + list(implementation["failures"])
    path = root / EXECUTION_FREEZE_PATH
    if not path.is_file():
        failures.append("Revision execution freeze is absent")
        return {"status": "locked", "failures": failures}
    freeze = json.loads(path.read_text())
    if freeze.get("status") != "frozen_before_first_v0.2.1_calibration_case":
        failures.append("Revision execution freeze status is invalid")
    if freeze.get("execution_authorized") is not True:
        failures.append("Revision execution authorization is absent")
    for key in ("observed_residual_access_authorized", "observed_periodic_search_authorized"):
        if freeze.get(key) is not False:
            failures.append(f"Revision execution boundary invalid: {key}")
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("Revision execution inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append("Revision execution implementation mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"Revision execution hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_sha256": hash_file(path, "sha256"),
        "inventory_sha256": inventory["inventory_sha256"],
    }


class RevisionLedger(CalibrationLedger):
    def __init__(self, data_root: Path, inventory_sha256: str, implementation_hash: str):
        super().__init__(data_root, inventory_sha256, implementation_hash)
        self.path = data_root / "run_records/pilot2/calibration-v0.2.1-ledger.json"
        self.health_path = data_root / "run_records/pilot2/calibration-v0.2.1-health.json"
        self.dashboard_path = data_root / "derived/pilot2/calibration-v0.2.1-dashboard/index.html"

    def empty(self) -> dict[str, Any]:
        state = super().empty()
        state["run_id"] = "pilot2-b1937-calibration-v0.2.1"
        return state

    def commit_threshold_lock(self, threshold_result_path: Path) -> dict[str, Any]:
        state = self.load()
        if state["stage_status"]["gaussian_threshold_calibration"] != "pass":
            raise RuntimeError("Revision threshold cannot lock before calibration passes")
        result = json.loads(threshold_result_path.read_text())
        threshold = result.get("threshold", {})
        if threshold.get("status") != "proposed_not_locked":
            raise RuntimeError("Revision threshold is not a lockable proposal")
        record = {
            "schema_version": 1,
            "status": "locked_before_sealed_evaluation",
            "value_delta_chi2": float(threshold["value_delta_chi2"]),
            "rank": int(threshold["rank"]),
            "sample_count": int(threshold["sample_count"]),
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
        path = self.data_root / "run_records/pilot2/calibration-threshold-lock-v0.2.1.json"
        _atomic_json(path, record)
        state["stage_status"]["commit_threshold_lock"] = "pass"
        state["stage_results"]["commit_threshold_lock"] = {
            "logical_path": logical_path(path, self.data_root),
            "bytes": path.stat().st_size,
            "sha256": hash_file(path, "sha256"),
        }
        self.save(state)
        return record

    def verify_threshold_lock(self) -> dict[str, Any]:
        state = self.load()
        item = state.get("stage_results", {}).get("commit_threshold_lock")
        if not item:
            raise RuntimeError("Revision sealed evaluation requires a threshold lock")
        path = self.data_root / item["logical_path"]
        if not path.is_file() or hash_file(path, "sha256") != item["sha256"]:
            raise RuntimeError("Revision threshold lock artifact mismatch")
        lock = json.loads(path.read_text())
        if lock.get("inventory_sha256") != self.inventory_sha256:
            raise RuntimeError("Revision threshold lock inventory mismatch")
        return lock


def zero_case_dry_run(data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    config = load_yaml(repository_root() / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    ledger = RevisionLedger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    ledger.save(state)
    gate = verify_execution_gate()
    criteria = {
        "design_freeze_verified": verify_revision_freeze()["status"] == "pass",
        "implementation_freeze_verified": verify_implementation_freeze()["status"] == "pass",
        "execution_gate_locked": gate["status"] == "locked",
        "zero_cases_recorded": len(state["completed_cases"]) == 0,
        "all_stages_pending": all(value == "pending" for value in state["stage_status"].values()),
        "artifact_verification_passes": ledger.verify_artifacts()["status"] == "pass",
        "health_record_written": ledger.health_path.is_file(),
        "dashboard_written": ledger.dashboard_path.is_file(),
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "v0.2.1_zero_case_integrity_dry_run",
        "criteria": criteria,
        "science_cases_executed": 0,
        "random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-calibration-revision-runtime")
    parser.add_argument("command", choices=("verify-implementation", "verify-gate", "dry-run"))
    parser.add_argument("--data-root")
    args = parser.parse_args()
    if args.command == "verify-implementation":
        result = verify_implementation_freeze()
    elif args.command == "verify-gate":
        result = verify_execution_gate()
    else:
        result = zero_case_dry_run(configured_data_root(args.data_root))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
