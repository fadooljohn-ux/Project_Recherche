from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_runtime import (
    build_search_frequency_grid,
    generate_covariance_null,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .pilot2_calibration_design import build_inventory
from .pilot2_calibration_grading import grade_gaussian_calibration, grade_sealed_gaussian
from .pilot2_calibration_runtime import (
    CONFIG_PATH,
    EXECUTION_FREEZE_PATH,
    CalibrationLedger,
    HeartbeatService,
    _atomic_json,
    implementation_sha256,
    verify_execution_gate,
)
from .pilot2_preflight import _load_release, _network_disabled
from .provenance import hash_file, logical_path


@dataclass
class GaussianContext:
    scanner: Any
    input_binding: dict[str, Any]


def prepare_gaussian_context(data_root: Path) -> GaussianContext:
    require_initialized_data_root(data_root)
    log_path = data_root / "run_records/pilot2/calibration-v0.2-setup.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with _network_disabled():
        model, toas = _load_release(data_root, log_path)
    from pint.fitter import WidebandTOAFitter

    fitter = WidebandTOAFitter(toas, model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    frequencies, grid = build_search_frequency_grid(times, 30.0, 2000.0, 5)
    scanner = prepare_covariance_gls_scanner(
        covariance, design, times, frequencies, float(model.PEPOCH.value)
    )
    binding = {
        "target": "B1937+21",
        "active_toas": len(toas),
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
            raise RuntimeError(f"Frozen B1937 setup mismatch: {key}")
    return GaussianContext(scanner=scanner, input_binding=binding)


def execute_first_gaussian_case(data_root: Path) -> dict[str, Any]:
    gate = verify_execution_gate()
    if gate["status"] != "pass":
        raise RuntimeError(f"Calibration execution gate failed: {gate['failures']}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_inventory(config)
    cases = [item for item in inventory["gaussian_null_cases"] if item["family"] == "calibration"]
    case = cases[0]
    ledger = CalibrationLedger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    if case["case_id"] in state["completed_cases"]:
        return {
            "status": "already_complete",
            "case_id": case["case_id"],
            "science_cases_executed_this_invocation": 0,
            "ledger_verification": ledger.verify_artifacts(),
        }
    if state["active_stage"] is None:
        ledger.begin_stage("gaussian_threshold_calibration")
    elif state["active_stage"] != "gaussian_threshold_calibration":
        raise RuntimeError("Ledger is active in a different calibration stage")
    context = prepare_gaussian_context(data_root)
    output = data_root / "derived/pilot2/calibration-v0.2/gaussian" / f"0001-{case['case_id']}.json"
    with HeartbeatService(ledger, 30.0):
        noise = generate_covariance_null(
            context.scanner.covariance_cholesky, np.random.default_rng(int(case["seed"]))
        )
        scan = context.scanner.scan(noise)
        record = {
            "schema_version": 1,
            "run_id": "pilot2-b1937-calibration-v0.2",
            "case": case,
            "input_binding": context.input_binding,
            "global_maximum_delta_chi2": float(scan["trigger_statistic"]),
            "peak_period_days": float(scan["peak_period_days"]),
            "whitened_innovation_sha256": hashlib.sha256(noise.tobytes()).hexdigest(),
            "observed_residual_vector_used": False,
            "observed_periodic_scan_executed": False,
        }
        _atomic_json(output, record)
        ledger.record_case("gaussian_threshold_calibration", str(case["case_id"]), output)
    verification = ledger.verify_artifacts()
    if verification["status"] != "pass":
        raise RuntimeError("First calibration artifact failed ledger verification")
    return {
        "status": "pass",
        "case_id": case["case_id"],
        "case_seed": case["seed"],
        "artifact": logical_path(output, data_root),
        "science_cases_executed_this_invocation": 1,
        "completed_calibration_cases": verification["completed_cases"],
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
        "ledger_verification": verification,
    }


def execute_remaining_gaussian_calibration(data_root: Path) -> dict[str, Any]:
    gate = verify_execution_gate()
    if gate["status"] != "pass":
        raise RuntimeError(f"Calibration execution gate failed: {gate['failures']}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_inventory(config)
    cases = [item for item in inventory["gaussian_null_cases"] if item["family"] == "calibration"]
    ledger = CalibrationLedger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    if state["stage_status"]["gaussian_threshold_calibration"] == "pass":
        return {
            "status": "already_complete",
            "completed_calibration_cases": len(cases),
            "science_cases_executed_this_invocation": 0,
        }
    if state["active_stage"] is None:
        ledger.begin_stage("gaussian_threshold_calibration")
    elif state["active_stage"] != "gaussian_threshold_calibration":
        raise RuntimeError("Ledger is active in a different calibration stage")
    context = prepare_gaussian_context(data_root)
    output_root = data_root / "derived/pilot2/calibration-v0.2/gaussian"
    records: list[dict[str, Any]] = []
    noise_realizations: list[np.ndarray] = []
    executed = 0
    with HeartbeatService(ledger, 30.0):
        for sequence, case in enumerate(cases, 1):
            noise = generate_covariance_null(
                context.scanner.covariance_cholesky,
                np.random.default_rng(int(case["seed"])),
            )
            noise_realizations.append(noise)
            output = output_root / f"{sequence:04d}-{case['case_id']}.json"
            current = ledger.load()
            if case["case_id"] in current["completed_cases"]:
                records.append(json.loads(output.read_text(encoding="utf-8")))
                continue
            scan = context.scanner.scan(noise)
            record = {
                "schema_version": 1,
                "run_id": "pilot2-b1937-calibration-v0.2",
                "case": case,
                "input_binding": context.input_binding,
                "global_maximum_delta_chi2": float(scan["trigger_statistic"]),
                "peak_period_days": float(scan["peak_period_days"]),
                "whitened_innovation_sha256": hashlib.sha256(noise.tobytes()).hexdigest(),
                "observed_residual_vector_used": False,
                "observed_periodic_scan_executed": False,
            }
            _atomic_json(output, record)
            ledger.record_case("gaussian_threshold_calibration", str(case["case_id"]), output)
            records.append(record)
            executed += 1
            if sequence % 25 == 0:
                print(f"PILOT2_CALIBRATION_PROGRESS {sequence}/1000", flush=True)
    diagnostics = null_ensemble_diagnostics(
        np.asarray(noise_realizations), context.scanner.covariance_cholesky
    )
    grade = grade_gaussian_calibration(records, diagnostics, config)
    result = {
        **grade,
        "input_binding": context.input_binding,
        "null_ensemble_diagnostics": diagnostics,
        "science_cases_executed_this_invocation": executed,
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
    }
    result_path = data_root / "run_records/pilot2/gaussian-threshold-calibration-v0.2.json"
    _atomic_json(result_path, result)
    ledger.complete_stage("gaussian_threshold_calibration", result_path, result["status"] == "pass")
    if result["status"] == "pass":
        ledger.commit_threshold_lock(result_path)
    verification = ledger.verify_artifacts()
    if verification["status"] != "pass":
        raise RuntimeError("Gaussian calibration artifacts failed ledger verification")
    return {
        "status": result["status"],
        "completed_calibration_cases": len(records),
        "science_cases_executed_this_invocation": executed,
        "threshold_lock_committed": result["status"] == "pass",
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
        "ledger_verification": verification,
    }


def execute_sealed_gaussian_evaluation(data_root: Path) -> dict[str, Any]:
    gate = verify_execution_gate()
    if gate["status"] != "pass":
        raise RuntimeError(f"Calibration execution gate failed: {gate['failures']}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_inventory(config)
    cases = [
        item for item in inventory["gaussian_null_cases"] if item["family"] == "sealed_evaluation"
    ]
    ledger = CalibrationLedger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    if state["stage_status"]["sealed_gaussian_evaluation"] in {"pass", "fail"}:
        return {
            "status": "already_complete",
            "stage_status": state["stage_status"]["sealed_gaussian_evaluation"],
            "science_cases_executed_this_invocation": 0,
        }
    threshold_lock = ledger.verify_threshold_lock()
    lock_path = data_root / "run_records/pilot2/calibration-threshold-lock-v0.2.json"
    lock_sha256 = hash_file(lock_path, "sha256")
    execution_freeze = json.loads((root / EXECUTION_FREEZE_PATH).read_text(encoding="utf-8"))
    if execution_freeze.get("threshold_lock_sha256") != lock_sha256:
        raise RuntimeError("Execution freeze does not bind the current threshold lock")
    ledger.begin_stage("sealed_gaussian_evaluation")
    context = prepare_gaussian_context(data_root)
    output_root = data_root / "derived/pilot2/calibration-v0.2/sealed-gaussian"
    records: list[dict[str, Any]] = []
    executed = 0
    with HeartbeatService(ledger, 30.0):
        for sequence, case in enumerate(cases, 1):
            output = output_root / f"{sequence:04d}-{case['case_id']}.json"
            current = ledger.load()
            if case["case_id"] in current["completed_cases"]:
                records.append(json.loads(output.read_text(encoding="utf-8")))
                continue
            noise = generate_covariance_null(
                context.scanner.covariance_cholesky,
                np.random.default_rng(int(case["seed"])),
            )
            scan = context.scanner.scan(noise)
            record = {
                "schema_version": 1,
                "run_id": "pilot2-b1937-calibration-v0.2",
                "case": case,
                "input_binding": context.input_binding,
                "threshold_lock_sha256": lock_sha256,
                "global_maximum_delta_chi2": float(scan["trigger_statistic"]),
                "peak_period_days": float(scan["peak_period_days"]),
                "whitened_innovation_sha256": hashlib.sha256(noise.tobytes()).hexdigest(),
                "observed_residual_vector_used": False,
                "observed_periodic_scan_executed": False,
            }
            _atomic_json(output, record)
            ledger.record_case("sealed_gaussian_evaluation", str(case["case_id"]), output)
            records.append(record)
            executed += 1
            if sequence % 25 == 0:
                print(f"PILOT2_SEALED_GAUSSIAN_PROGRESS {sequence}/500", flush=True)
    if hash_file(lock_path, "sha256") != lock_sha256:
        raise RuntimeError("Threshold lock changed during sealed evaluation")
    ledger.verify_threshold_lock()
    grade = grade_sealed_gaussian(records, float(threshold_lock["value_delta_chi2"]), config)
    result = {
        **grade,
        "threshold_lock_sha256": lock_sha256,
        "threshold_retuned": False,
        "input_binding": context.input_binding,
        "science_cases_executed_this_invocation": executed,
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
    }
    result_path = data_root / "run_records/pilot2/sealed-gaussian-evaluation-v0.2.json"
    _atomic_json(result_path, result)
    ledger.complete_stage("sealed_gaussian_evaluation", result_path, result["status"] == "pass")
    verification = ledger.verify_artifacts()
    if verification["status"] != "pass":
        raise RuntimeError("Sealed Gaussian artifacts failed ledger verification")
    return {
        "status": result["status"],
        "completed_sealed_cases": len(records),
        "science_cases_executed_this_invocation": executed,
        "threshold_lock_unchanged": hash_file(lock_path, "sha256") == lock_sha256,
        "threshold_retuned": False,
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
        "ledger_verification": verification,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-calibration-executor")
    parser.add_argument(
        "command", choices=("verify-setup", "run-first", "run-gaussian", "run-sealed")
    )
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    data_root = configured_data_root(args.data_root)
    if args.command == "verify-setup":
        context = prepare_gaussian_context(data_root)
        result = {"status": "pass", "input_binding": context.input_binding}
    elif args.command == "run-first":
        result = execute_first_gaussian_case(data_root)
    elif args.command == "run-gaussian":
        result = execute_remaining_gaussian_calibration(data_root)
    else:
        result = execute_sealed_gaussian_evaluation(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"pass", "already_complete"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
