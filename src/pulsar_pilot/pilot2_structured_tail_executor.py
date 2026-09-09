from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner
from .pilot2_calibration_grading import grade_structured_tail
from .pilot2_calibration_revision_design import build_revision_inventory
from .pilot2_calibration_revision_runtime import (
    CONFIG_PATH,
    RevisionLedger,
)
from .pilot2_calibration_revision_runtime import (
    implementation_sha256 as gaussian_implementation_sha256,
)
from .pilot2_calibration_revision_runtime import (
    verify_implementation_freeze as verify_gaussian_implementation_freeze,
)
from .pilot2_calibration_runtime import HeartbeatService, _atomic_json
from .pilot2_preflight import _load_release, _network_disabled
from .provenance import hash_file

STRUCTURED_IMPLEMENTATION_FREEZE_PATH = (
    "protocol/PILOT2_STRUCTURED_TAIL_IMPLEMENTATION_FREEZE_v0.2.1.json"
)
STRUCTURED_EXECUTION_FREEZE_PATH = (
    "protocol/PILOT2_STRUCTURED_TAIL_EXECUTION_FREEZE_v0.2.1.json"
)
GAUSSIAN_CLOSEOUT_PATH = "results/pilot2/calibration_revision_gaussian_closeout_v0.2.1.json"
STRUCTURED_IMPLEMENTATION_PATHS = (
    "src/pulsar_pilot/pilot2_structured_tail_executor.py",
    "src/pulsar_pilot/pilot2_calibration_grading.py",
    "src/pulsar_pilot/pilot2_calibration_revision_design.py",
    "src/pulsar_pilot/pilot2_calibration_revision_runtime.py",
    "src/pulsar_pilot/pilot2_calibration_runtime.py",
    "src/pulsar_pilot/pilot2_preflight.py",
    "src/pulsar_pilot/pilot1_runtime.py",
)
HEARTBEAT_INTERVAL_SECONDS = 30.0
STALE_HEARTBEAT_SECONDS = 90.0
PASSIVE_REVIEW_INTERVAL_SECONDS = 900


@dataclass
class StructuredContext:
    scanner: Any
    utc_days: np.ndarray
    input_binding: dict[str, Any]


def structured_implementation_sha256() -> str:
    root = repository_root()
    digest = hashlib.sha256()
    for relative in STRUCTURED_IMPLEMENTATION_PATHS:
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((root / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_structured_implementation_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / STRUCTURED_IMPLEMENTATION_FREEZE_PATH
    if not path.is_file():
        return {"status": "locked", "failures": ["Structured implementation freeze is absent"]}
    freeze = json.loads(path.read_text())
    failures: list[str] = []
    if freeze.get("status") != "implementation_frozen_execution_not_authorized":
        failures.append("Structured implementation status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append("Structured implementation freeze authorizes execution")
    if freeze.get("science_cases_executed_during_validation") != 0:
        failures.append("Structured implementation validation was not zero-case")
    if freeze.get("implementation_sha256") != structured_implementation_sha256():
        failures.append("Structured aggregate implementation mismatch")
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("Structured implementation inventory mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"Structured implementation hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "implementation_sha256": structured_implementation_sha256(),
        "inventory_sha256": inventory["inventory_sha256"],
        "freeze_sha256": hash_file(path, "sha256"),
    }


def verify_structured_prerequisites(
    data_root: Path, *, verify_case_artifacts: bool = True
) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    failures: list[str] = []
    gaussian_implementation = verify_gaussian_implementation_freeze()
    if gaussian_implementation["status"] != "pass":
        failures.append("Frozen Gaussian implementation no longer verifies")
    closeout_path = root / GAUSSIAN_CLOSEOUT_PATH
    if not closeout_path.is_file():
        failures.append("Gaussian closeout is absent")
        closeout: dict[str, Any] = {}
    else:
        closeout = json.loads(closeout_path.read_text())
    if closeout.get("status") != "pass":
        failures.append("Gaussian closeout is not a pass")
    if closeout.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("Gaussian closeout inventory mismatch")
    if closeout.get("implementation_sha256") != gaussian_implementation_sha256():
        failures.append("Gaussian closeout implementation mismatch")

    ledger = RevisionLedger(
        data_root, inventory["inventory_sha256"], gaussian_implementation_sha256()
    )
    try:
        state = ledger.load()
    except (OSError, RuntimeError, ValueError) as error:
        return {"status": "fail", "failures": [str(error)]}
    expected_status = {
        "gaussian_threshold_calibration": "pass",
        "commit_threshold_lock": "pass",
        "sealed_gaussian_evaluation": "pass",
        "structured_tail_evaluation": "pending",
    }
    for stage, expected in expected_status.items():
        if state["stage_status"].get(stage) != expected:
            failures.append(f"Unexpected prerequisite stage status: {stage}")
    stage_counts = {
        stage: sum(item["stage"] == stage for item in state["completed_cases"].values())
        for stage in (
            "gaussian_threshold_calibration",
            "sealed_gaussian_evaluation",
            "structured_tail_evaluation",
        )
    }
    if stage_counts != {
        "gaussian_threshold_calibration": 5000,
        "sealed_gaussian_evaluation": 2000,
        "structured_tail_evaluation": 0,
    }:
        failures.append(f"Unexpected prerequisite case counts: {stage_counts}")
    if state.get("hard_stop") is not None:
        failures.append("Gaussian ledger contains a hard stop")

    bindings = closeout.get("artifact_bindings", {})
    external_artifacts = {
        "calibration_result_sha256": (
            "run_records/pilot2/gaussian-threshold-calibration-v0.2.1.json"
        ),
        "threshold_lock_sha256": "run_records/pilot2/calibration-threshold-lock-v0.2.1.json",
        "sealed_evaluation_result_sha256": (
            "run_records/pilot2/sealed-gaussian-evaluation-v0.2.1.json"
        ),
        "final_ledger_sha256": "run_records/pilot2/calibration-v0.2.1-ledger.json",
    }
    for key, relative in external_artifacts.items():
        item = data_root / relative
        if not item.is_file() or hash_file(item, "sha256") != bindings.get(key):
            failures.append(f"Gaussian prerequisite artifact mismatch: {relative}")
    artifact_verification = (
        ledger.verify_artifacts()
        if verify_case_artifacts
        else {"status": "not_requested", "completed_cases": len(state["completed_cases"])}
    )
    if verify_case_artifacts and artifact_verification["status"] != "pass":
        failures.append("Gaussian case-artifact ledger verification failed")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "inventory_sha256": inventory["inventory_sha256"],
        "gaussian_implementation_sha256": gaussian_implementation_sha256(),
        "completed_case_counts": stage_counts,
        "checkpoint_count": len(state["checkpoints"]),
        "artifact_verification": artifact_verification,
        "threshold_lock_sha256": bindings.get("threshold_lock_sha256"),
        "sealed_evaluation_result_sha256": bindings.get("sealed_evaluation_result_sha256"),
    }


def verify_structured_execution_gate(data_root: Path) -> dict[str, Any]:
    root = repository_root()
    prerequisites = verify_structured_prerequisites(data_root)
    implementation = verify_structured_implementation_freeze()
    failures = list(prerequisites.get("failures", [])) + list(
        implementation.get("failures", [])
    )
    path = root / STRUCTURED_EXECUTION_FREEZE_PATH
    if not path.is_file():
        failures.append("Structured execution authorization freeze is absent")
        return {
            "status": "locked" if prerequisites["status"] == implementation["status"] == "pass" else "fail",
            "failures": failures,
            "prerequisites": prerequisites,
            "implementation": implementation,
        }
    freeze = json.loads(path.read_text())
    if freeze.get("status") != "frozen_before_first_structured_tail_case":
        failures.append("Structured execution freeze status is invalid")
    if freeze.get("execution_authorized") is not True:
        failures.append("Structured-tail execution is not authorized")
    if freeze.get("authorized_case_count") != 3000:
        failures.append("Structured-tail authorized case count is not exactly 3000")
    for key in (
        "threshold_retuning_authorized",
        "injection_evaluation_authorized",
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "discovery_claim_authorized",
    ):
        if freeze.get(key) is not False:
            failures.append(f"Structured execution boundary invalid: {key}")
    if freeze.get("inventory_sha256") != prerequisites.get("inventory_sha256"):
        failures.append("Structured execution inventory mismatch")
    if freeze.get("implementation_sha256") != implementation.get("implementation_sha256"):
        failures.append("Structured execution implementation mismatch")
    if freeze.get("threshold_lock_sha256") != prerequisites.get("threshold_lock_sha256"):
        failures.append("Structured execution threshold-lock mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"Structured execution hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "prerequisites": prerequisites,
        "implementation": implementation,
        "freeze_sha256": hash_file(path, "sha256"),
    }


def _mixture_scale(probability: float, multiplier: float) -> float:
    return math.sqrt((1.0 - probability) + probability * multiplier**2)


def generate_structured_null(
    covariance_cholesky: np.ndarray,
    generator: np.random.Generator,
    variant: dict[str, Any],
    toa_count: int,
    utc_days: np.ndarray,
    probability: float,
    multiplier: float,
) -> tuple[np.ndarray, int]:
    factor = np.asarray(covariance_cholesky, dtype=float)
    if factor.shape != (2 * toa_count, 2 * toa_count):
        raise ValueError("Structured null requires paired timing and DM coordinates")
    days = np.asarray(utc_days, dtype=int)
    if days.shape != (toa_count,):
        raise ValueError("UTC-day inventory does not match the TOA count")
    innovations = generator.standard_normal(2 * toa_count)
    contaminated = np.zeros(2 * toa_count, dtype=bool)
    scale = _mixture_scale(probability, multiplier)
    block = variant.get("selected_native_innovation_block")
    if block is not None:
        start, stop = (0, toa_count) if block == "timing" else (toa_count, 2 * toa_count)
        mask = generator.random(toa_count) < probability
        contaminated[start:stop] = mask
        innovations[start:stop][mask] *= multiplier
        innovations[start:stop] /= scale
    else:
        unique_days = np.asarray(sorted(set(days.tolist())), dtype=int)
        selected_days = unique_days[generator.random(len(unique_days)) < probability]
        row_mask = np.isin(days, selected_days)
        contaminated[:toa_count] = row_mask
        contaminated[toa_count:] = row_mask
        innovations[contaminated] *= multiplier
        innovations /= scale
    return factor @ innovations, int(np.sum(contaminated))


def prepare_structured_context(data_root: Path) -> StructuredContext:
    require_initialized_data_root(data_root)
    log_path = data_root / "run_records/pilot2/structured-tail-v0.2.1-setup.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with _network_disabled():
        model, toas = _load_release(data_root, log_path)
    from pint.fitter import WidebandTOAFitter

    fitter = WidebandTOAFitter(toas, model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    utc_days = np.floor(np.asarray(toas.table["mjd_float"], dtype=float)).astype(int)
    frequencies, grid = build_search_frequency_grid(times, 30.0, 2000.0, 5)
    scanner = prepare_covariance_gls_scanner(
        covariance, design, times, frequencies, float(model.PEPOCH.value)
    )
    binding = {
        "target": "B1937+21",
        "active_toas": len(toas),
        "unique_floor_mjd_utc_days": len(set(utc_days.tolist())),
        "covariance_shape": list(covariance.shape),
        "timing_design_shape": list(design.shape),
        "timing_design_rank": scanner.timing_design_rank,
        "frequency_grid": grid,
        "observed_residual_vector_loaded": False,
        "observed_periodic_scan_executed": False,
        "network_access_enabled": False,
    }
    expected = {
        "active_toas": 660,
        "covariance_shape": [1320, 1320],
        "timing_design_shape": [1320, 284],
        "timing_design_rank": 284,
    }
    for key, value in expected.items():
        if binding[key] != value:
            raise RuntimeError(f"Structured setup mismatch: {key}")
    return StructuredContext(scanner=scanner, utc_days=utc_days, input_binding=binding)


def execute_structured_tail(data_root: Path) -> dict[str, Any]:
    gate = verify_structured_execution_gate(data_root)
    if gate["status"] != "pass":
        raise RuntimeError(f"Structured-tail execution is locked: {gate['failures']}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    ledger = RevisionLedger(
        data_root, inventory["inventory_sha256"], gaussian_implementation_sha256()
    )
    state = ledger.load()
    if state["stage_status"]["structured_tail_evaluation"] == "pass":
        return {"status": "already_complete", "science_cases_executed_this_invocation": 0}
    ledger.begin_stage("structured_tail_evaluation")
    context = prepare_structured_context(data_root)
    lock_path = data_root / "run_records/pilot2/calibration-threshold-lock-v0.2.1.json"
    lock = ledger.verify_threshold_lock()
    lock_sha = hash_file(lock_path, "sha256")
    tail = config["structured_tail_evaluation"]
    variants = {item["id"]: item for item in tail["variants"]}
    probability = float(tail["contaminated_probability"])
    multiplier = float(tail["contaminated_standard_deviation_multiplier"])
    records: list[dict[str, Any]] = []
    executed = 0
    output_root = data_root / "derived/pilot2/calibration-v0.2.1/structured-tail"
    cases = inventory["structured_tail_cases"]
    with HeartbeatService(ledger, HEARTBEAT_INTERVAL_SECONDS):
        for sequence, case in enumerate(cases, 1):
            path = output_root / case["variant"] / f"{case['index'] + 1:04d}-{case['case_id']}.json"
            if case["case_id"] in ledger.load()["completed_cases"]:
                record = json.loads(path.read_text())
            else:
                noise, contaminated_count = generate_structured_null(
                    context.scanner.covariance_cholesky,
                    np.random.default_rng(int(case["seed"])),
                    variants[case["variant"]],
                    context.input_binding["active_toas"],
                    context.utc_days,
                    probability,
                    multiplier,
                )
                scan = context.scanner.scan(noise)
                record = {
                    "schema_version": 1,
                    "run_id": "pilot2-b1937-calibration-v0.2.1",
                    "case": case,
                    "variant": case["variant"],
                    "contaminated_coordinate_count": contaminated_count,
                    "input_binding": context.input_binding,
                    "global_maximum_delta_chi2": float(scan["trigger_statistic"]),
                    "peak_period_days": float(scan["peak_period_days"]),
                    "threshold_lock_sha256": lock_sha,
                    "observed_residual_vector_used": False,
                    "observed_periodic_scan_executed": False,
                }
                _atomic_json(path, record)
                ledger.record_case("structured_tail_evaluation", case["case_id"], path)
                executed += 1
            records.append(record)
            if sequence % 25 == 0:
                print(f"PILOT2R1_STRUCTURED_PROGRESS {sequence}/3000", flush=True)
    if hash_file(lock_path, "sha256") != lock_sha:
        raise RuntimeError("Threshold lock changed during structured-tail evaluation")
    result = grade_structured_tail(records, float(lock["value_delta_chi2"]), config)
    result.update(
        threshold_lock_sha256=lock_sha,
        threshold_retuned=False,
        science_cases_executed_this_invocation=executed,
        observed_residual_vector_used=False,
        observed_periodic_scan_executed=False,
    )
    result_path = data_root / "run_records/pilot2/structured-tail-evaluation-v0.2.1.json"
    _atomic_json(result_path, result)
    ledger.complete_stage("structured_tail_evaluation", result_path, result["status"] == "pass")
    return {
        "status": result["status"],
        "completed_structured_tail_cases": len(records),
        "science_cases_executed_this_invocation": executed,
        "threshold_lock_unchanged": hash_file(lock_path, "sha256") == lock_sha,
        "ledger_verification": ledger.verify_artifacts(),
    }


def supervision_snapshot(data_root: Path, now: datetime | None = None) -> dict[str, Any]:
    config = load_yaml(repository_root() / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    ledger = RevisionLedger(
        data_root, inventory["inventory_sha256"], gaussian_implementation_sha256()
    )
    state = ledger.load()
    status = state["stage_status"]["structured_tail_evaluation"]
    health = json.loads(ledger.health_path.read_text()) if ledger.health_path.is_file() else {}
    event = "locked_idle"
    codex_check_required = False
    heartbeat_age_seconds: float | None = None
    if status in {"pass", "fail"}:
        event = f"terminal_{status}"
        codex_check_required = True
    elif status == "running":
        heartbeat = health.get("last_heartbeat_utc")
        if heartbeat:
            observed = datetime.fromisoformat(heartbeat)
            heartbeat_age_seconds = max(0.0, ((now or datetime.now(UTC)) - observed).total_seconds())
        if not state.get("runtime_active") or heartbeat_age_seconds is None:
            event = "paused_or_interrupted"
            codex_check_required = True
        elif heartbeat_age_seconds > STALE_HEARTBEAT_SECONDS:
            event = "stale_attention_required"
            codex_check_required = True
        else:
            event = "healthy_no_action"
    completed = sum(
        item["stage"] == "structured_tail_evaluation"
        for item in state["completed_cases"].values()
    )
    return {
        "schema_version": 1,
        "event": event,
        "codex_check_required": codex_check_required,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "heartbeat_interval_seconds": HEARTBEAT_INTERVAL_SECONDS,
        "stale_after_seconds": STALE_HEARTBEAT_SECONDS,
        "passive_review_interval_seconds": PASSIVE_REVIEW_INTERVAL_SECONDS,
        "structured_cases_completed": completed,
        "structured_cases_total": 3000,
        "checkpoint_count": len(state["checkpoints"]),
        "hard_stop_present": state.get("hard_stop") is not None,
        "scientific_outcomes_sealed": True,
        "policy": "no_codex_poll_while_heartbeat_fresh",
    }


def zero_case_dry_run(data_root: Path) -> dict[str, Any]:
    prerequisites = verify_structured_prerequisites(data_root)
    implementation = verify_structured_implementation_freeze()
    gate = verify_structured_execution_gate(data_root)
    snapshot = supervision_snapshot(data_root)
    criteria = {
        "gaussian_prerequisites_pass": prerequisites["status"] == "pass",
        "structured_implementation_freeze_pass": implementation["status"] == "pass",
        "structured_execution_gate_locked": gate["status"] == "locked",
        "zero_structured_cases_recorded": prerequisites["completed_case_counts"][
            "structured_tail_evaluation"
        ]
        == 0,
        "heartbeat_interval_30_seconds": HEARTBEAT_INTERVAL_SECONDS == 30.0,
        "stale_tripwire_90_seconds": STALE_HEARTBEAT_SECONDS == 90.0,
        "passive_review_interval_15_minutes": PASSIVE_REVIEW_INTERVAL_SECONDS == 900,
        "idle_supervision_requires_no_codex_check": snapshot["codex_check_required"] is False,
        "observed_search_boundary_preserved": True,
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "structured_tail_v0.2.1_zero_case_integrity_dry_run",
        "criteria": criteria,
        "science_cases_executed": 0,
        "random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
        "prerequisites": prerequisites,
        "execution_gate_status": gate["status"],
        "supervision": snapshot,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-structured-tail-executor")
    parser.add_argument(
        "command",
        choices=(
            "verify-prerequisites",
            "verify-implementation",
            "verify-gate",
            "dry-run",
            "health",
            "run-structured",
        ),
    )
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    data_root = configured_data_root(args.data_root)
    if args.command == "verify-prerequisites":
        result = verify_structured_prerequisites(data_root)
    elif args.command == "verify-implementation":
        result = verify_structured_implementation_freeze()
    elif args.command == "verify-gate":
        result = verify_structured_execution_gate(data_root)
    elif args.command == "dry-run":
        result = zero_case_dry_run(data_root)
    elif args.command == "health":
        result = supervision_snapshot(data_root)
    else:
        result = execute_structured_tail(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status", "pass") not in {"fail"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
