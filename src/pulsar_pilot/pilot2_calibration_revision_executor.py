from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .paths import (
    configured_data_root,
    initialize_data_root,
    repository_root,
    require_initialized_data_root,
)
from .pilot1_runtime import (
    build_search_frequency_grid,
    generate_covariance_null,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .pilot2_calibration_revision_design import build_revision_inventory
from .pilot2_calibration_revision_grading import (
    grade_revision_calibration,
    grade_revision_sealed,
)
from .pilot2_calibration_revision_runtime import (
    CONFIG_PATH,
    EXECUTION_FREEZE_PATH,
    RevisionLedger,
    implementation_sha256,
    verify_execution_gate,
)
from .pilot2_calibration_runtime import HeartbeatService, _atomic_json
from .pilot2_preflight import _load_release, _network_disabled
from .provenance import hash_file


@dataclass
class RevisionContext:
    scanner: Any
    input_binding: dict[str, Any]


def _tree_manifest(root: Path) -> dict[str, str]:
    return {
        item.relative_to(root).as_posix(): hash_file(item, "sha256")
        for item in sorted(root.rglob("*"))
        if item.is_file() and not item.name.startswith("._")
    }


def prepare_revision_data_root(source: Path, destination: Path) -> dict[str, Any]:
    require_initialized_data_root(source)
    source_manifest = {
        "controlled": _tree_manifest(source / "controlled"),
        "cache": _tree_manifest(source / "derived/cache"),
    }
    if not destination.exists():
        temporary = destination.with_name(destination.name + ".staging")
        if temporary.exists():
            raise RuntimeError(f"Revision staging path already exists: {temporary}")
        initialize_data_root(temporary)
        shutil.copytree(source / "controlled", temporary / "controlled", dirs_exist_ok=True)
        shutil.copytree(source / "derived/cache", temporary / "derived/cache", dirs_exist_ok=True)
        os.replace(temporary, destination)
    require_initialized_data_root(destination)
    destination_manifest = {
        "controlled": _tree_manifest(destination / "controlled"),
        "cache": _tree_manifest(destination / "derived/cache"),
    }
    if destination_manifest != source_manifest:
        raise RuntimeError("Revision data-root copy does not match frozen source")
    return {
        "status": "pass",
        "source_generation": source.name,
        "destination_generation": destination.name,
        "controlled_files": len(source_manifest["controlled"]),
        "cache_files": len(source_manifest["cache"]),
        "science_cases_executed": 0,
    }


def prepare_context(data_root: Path) -> RevisionContext:
    require_initialized_data_root(data_root)
    log_path = data_root / "run_records/pilot2/calibration-v0.2.1-setup.log"
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
            raise RuntimeError(f"Revision setup mismatch: {key}")
    return RevisionContext(scanner=scanner, input_binding=binding)


def _case_record(
    context: RevisionContext, case: dict[str, Any]
) -> tuple[dict[str, Any], np.ndarray]:
    noise = generate_covariance_null(
        context.scanner.covariance_cholesky, np.random.default_rng(int(case["seed"]))
    )
    scan = context.scanner.scan(noise)
    return (
        {
            "schema_version": 1,
            "run_id": "pilot2-b1937-calibration-v0.2.1",
            "case": case,
            "input_binding": context.input_binding,
            "global_maximum_delta_chi2": float(scan["trigger_statistic"]),
            "peak_period_days": float(scan["peak_period_days"]),
            "whitened_innovation_sha256": hashlib.sha256(noise.tobytes()).hexdigest(),
            "observed_residual_vector_used": False,
            "observed_periodic_scan_executed": False,
        },
        noise,
    )


def execute_calibration(data_root: Path) -> dict[str, Any]:
    gate = verify_execution_gate()
    if gate["status"] != "pass":
        raise RuntimeError(f"Revision execution gate failed: {gate['failures']}")
    config = load_yaml(repository_root() / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    cases = [item for item in inventory["gaussian_null_cases"] if item["family"] == "calibration"]
    ledger = RevisionLedger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    if state["stage_status"]["gaussian_threshold_calibration"] == "pass":
        return {"status": "already_complete", "science_cases_executed_this_invocation": 0}
    if state["active_stage"] is None:
        ledger.begin_stage("gaussian_threshold_calibration")
    context = prepare_context(data_root)
    output_root = data_root / "derived/pilot2/calibration-v0.2.1/gaussian"
    records: list[dict[str, Any]] = []
    noises: list[np.ndarray] = []
    executed = 0
    with HeartbeatService(ledger, 30.0):
        for sequence, case in enumerate(cases, 1):
            output = output_root / f"{sequence:05d}-{case['case_id']}.json"
            if case["case_id"] in ledger.load()["completed_cases"]:
                record = json.loads(output.read_text())
                noise = generate_covariance_null(
                    context.scanner.covariance_cholesky,
                    np.random.default_rng(int(case["seed"])),
                )
            else:
                record, noise = _case_record(context, case)
                _atomic_json(output, record)
                ledger.record_case("gaussian_threshold_calibration", case["case_id"], output)
                executed += 1
            records.append(record)
            noises.append(noise)
            if sequence % 25 == 0:
                print(f"PILOT2R1_CALIBRATION_PROGRESS {sequence}/5000", flush=True)
    diagnostics = null_ensemble_diagnostics(np.asarray(noises), context.scanner.covariance_cholesky)
    result = grade_revision_calibration(records, diagnostics, config)
    result.update(
        input_binding=context.input_binding,
        null_ensemble_diagnostics=diagnostics,
        science_cases_executed_this_invocation=executed,
        observed_residual_vector_used=False,
        observed_periodic_scan_executed=False,
    )
    result_path = data_root / "run_records/pilot2/gaussian-threshold-calibration-v0.2.1.json"
    _atomic_json(result_path, result)
    ledger.complete_stage("gaussian_threshold_calibration", result_path, result["status"] == "pass")
    if result["status"] == "pass":
        ledger.commit_threshold_lock(result_path)
    return {
        "status": result["status"],
        "completed_calibration_cases": len(records),
        "science_cases_executed_this_invocation": executed,
        "threshold_lock_committed": result["status"] == "pass",
        "ledger_verification": ledger.verify_artifacts(),
    }


def execute_sealed(data_root: Path) -> dict[str, Any]:
    gate = verify_execution_gate()
    if gate["status"] != "pass":
        raise RuntimeError(f"Revision execution gate failed: {gate['failures']}")
    config = load_yaml(repository_root() / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    cases = [
        item for item in inventory["gaussian_null_cases"] if item["family"] == "sealed_evaluation"
    ]
    ledger = RevisionLedger(data_root, inventory["inventory_sha256"], implementation_sha256())
    lock = ledger.verify_threshold_lock()
    lock_path = data_root / "run_records/pilot2/calibration-threshold-lock-v0.2.1.json"
    lock_sha = hash_file(lock_path, "sha256")
    freeze = json.loads((repository_root() / EXECUTION_FREEZE_PATH).read_text())
    if freeze.get("threshold_lock_sha256") not in {None, lock_sha}:
        raise RuntimeError("Revision execution freeze threshold-lock mismatch")
    ledger.begin_stage("sealed_gaussian_evaluation")
    context = prepare_context(data_root)
    output_root = data_root / "derived/pilot2/calibration-v0.2.1/sealed-gaussian"
    records: list[dict[str, Any]] = []
    executed = 0
    with HeartbeatService(ledger, 30.0):
        for sequence, case in enumerate(cases, 1):
            output = output_root / f"{sequence:05d}-{case['case_id']}.json"
            if case["case_id"] in ledger.load()["completed_cases"]:
                record = json.loads(output.read_text())
            else:
                record, _ = _case_record(context, case)
                record["threshold_lock_sha256"] = lock_sha
                _atomic_json(output, record)
                ledger.record_case("sealed_gaussian_evaluation", case["case_id"], output)
                executed += 1
            records.append(record)
            if sequence % 25 == 0:
                print(f"PILOT2R1_SEALED_PROGRESS {sequence}/2000", flush=True)
    if hash_file(lock_path, "sha256") != lock_sha:
        raise RuntimeError("Revision threshold changed during sealed evaluation")
    result = grade_revision_sealed(records, float(lock["value_delta_chi2"]), config)
    result.update(
        threshold_lock_sha256=lock_sha,
        threshold_retuned=False,
        science_cases_executed_this_invocation=executed,
        observed_residual_vector_used=False,
        observed_periodic_scan_executed=False,
    )
    result_path = data_root / "run_records/pilot2/sealed-gaussian-evaluation-v0.2.1.json"
    _atomic_json(result_path, result)
    ledger.complete_stage("sealed_gaussian_evaluation", result_path, result["status"] == "pass")
    return {
        "status": result["status"],
        "completed_sealed_cases": len(records),
        "science_cases_executed_this_invocation": executed,
        "threshold_lock_unchanged": hash_file(lock_path, "sha256") == lock_sha,
        "ledger_verification": ledger.verify_artifacts(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-calibration-revision-executor")
    parser.add_argument(
        "command", choices=("prepare-root", "verify-setup", "run-calibration", "run-sealed")
    )
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--source-root")
    args = parser.parse_args()
    data_root = configured_data_root(args.data_root)
    if args.command == "prepare-root":
        if not args.source_root:
            raise RuntimeError("prepare-root requires --source-root")
        result = prepare_revision_data_root(Path(args.source_root).resolve(), data_root)
    elif args.command == "verify-setup":
        result = {"status": "pass", "input_binding": prepare_context(data_root).input_binding}
    elif args.command == "run-calibration":
        result = execute_calibration(data_root)
    else:
        result = execute_sealed(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"pass", "already_complete"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
