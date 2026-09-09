from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import (
    _directory_size_gib,
    _load_release,
    _peak_rss_gib,
    build_benchmark50_order,
)
from .pilot1_runtime import (
    ResumableArtifactLedger,
    build_pilot1_case_inventory,
    build_search_frequency_grid,
    conservative_nearest_rank,
    generate_covariance_null,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .provenance import hash_file, logical_path

CALIBRATION_ID = "pilot1-calibration-null-v0.1"
FREEZE_PATH = "protocol/PILOT1_CALIBRATION_FREEZE_v0.1.json"
PLAN_PATH = "results/pilot1/calibration_null_plan_v0.1.json"
BENCHMARK_DATA_ROOT = "derived/pilot1/benchmark50-r1"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_calibration_order(plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    inventory = build_pilot1_case_inventory(plan)
    calibration = sorted(
        (case for case in inventory["null_cases"] if case["family"] == "calibration"),
        key=lambda case: int(case["index"]),
    )
    reused_ids = {
        case["case_id"]
        for case in build_benchmark50_order(plan)
        if case["benchmark_role"] == "calibration_null"
    }
    reused = [case for case in calibration if case["case_id"] in reused_ids]
    remaining = [case for case in calibration if case["case_id"] not in reused_ids]
    if len(calibration) != 1000 or len(reused) != 10 or len(remaining) != 990:
        raise RuntimeError("Frozen calibration split is not 1,000 = 10 reused + 990 new")
    return {"all": calibration, "reused": reused, "remaining": remaining}


def calibration_plan(plan: dict[str, Any]) -> dict[str, Any]:
    order = build_calibration_order(plan)
    result = {
        "schema_version": 1,
        "calibration_id": CALIBRATION_ID,
        "execution_authorized": False,
        "calibration_case_count": len(order["all"]),
        "reused_benchmark_case_count": len(order["reused"]),
        "new_scan_case_count": len(order["remaining"]),
        "sealed_evaluation_case_count": 0,
        "all_case_order_sha256": _canonical_hash(order["all"]),
        "reused_case_order_sha256": _canonical_hash(order["reused"]),
        "remaining_case_order_sha256": _canonical_hash(order["remaining"]),
        "threshold_quantile": float(plan["nulls"]["threshold_quantile"]),
        "threshold_estimator": plan["nulls"]["threshold_estimator"],
        "trigger_comparison": plan["nulls"]["trigger_comparison"],
        "threshold_disposition": "proposed_not_locked",
    }
    return result


def verify_calibration_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    expected_plan = calibration_plan(load_yaml(root / "config/pilot1.yaml"))
    if freeze.get("status") != "frozen_before_remaining_calibration_nulls":
        failures.append("Calibration freeze status is invalid")
    if freeze.get("authorization") != "remaining_990_calibration_null_scans_only":
        failures.append("Authorization is not limited to the remaining calibration nulls")
    if freeze.get("sealed_evaluation_authorized") is not False:
        failures.append("Sealed evaluation must remain unauthorized")
    if freeze.get("observed_residual_search_authorized") is not False:
        failures.append("Observed-residual search must remain unauthorized")
    for key in (
        "all_case_order_sha256",
        "reused_case_order_sha256",
        "remaining_case_order_sha256",
    ):
        if freeze.get(key) != expected_plan[key]:
            failures.append(f"Calibration order mismatch: {key}")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        if hash_file(root / relative, "sha256") != expected:
            failures.append(f"Hash mismatch: {relative}")
    if hash_file(root / "pixi.lock", "sha256") != freeze.get("pixi_lock_sha256"):
        failures.append("Pixi lock hash mismatch")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_id": freeze.get("freeze_id"),
        "freeze_sha256": hash_file(freeze_path, "sha256"),
    }


def _load_reused_records(
    data_root: Path,
    order: list[dict[str, Any]],
    source_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {record["case_id"]: record for record in source_records}
    loaded: list[dict[str, Any]] = []
    for case in order:
        source = by_id.get(case["case_id"])
        if source is None:
            raise RuntimeError(f"No frozen benchmark source for {case['case_id']}")
        path = data_root / source["logical_path"]
        if not path.is_file() or hash_file(path, "sha256") != source["sha256"]:
            raise RuntimeError(f"Frozen benchmark source failed verification: {case['case_id']}")
        record = json.loads(path.read_text(encoding="utf-8"))
        actual = record.get("case", {})
        if actual.get("case_id") != case["case_id"] or actual.get("seed") != case["seed"]:
            raise RuntimeError(f"Frozen benchmark source identity mismatch: {case['case_id']}")
        loaded.append(record)
    return loaded


def run_calibration(data_root: Path) -> dict[str, Any]:
    freeze_verification = verify_calibration_freeze()
    if freeze_verification["status"] != "pass":
        raise RuntimeError(f"Pilot 1 calibration freeze failed: {freeze_verification}")
    root = repository_root()
    freeze = json.loads((root / FREEZE_PATH).read_text(encoding="utf-8"))
    plan = load_yaml(root / "config/pilot1.yaml")
    order = build_calibration_order(plan)

    log_path = data_root / "run_records/pilot1/calibration-null-v0.1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import pint.logging

    pint.logging.setup(
        level="INFO",
        sink=log_path,
        usecolors=False,
        capturewarnings=True,
        removeprior=True,
    )
    release_model, release_toas = _load_release(data_root)
    from pint.fitter import WidebandTOAFitter

    setup_start = time.perf_counter()
    fitter = WidebandTOAFitter(release_toas, release_model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(release_toas.table["tdbld"].data, dtype=float)
    frequencies, grid = build_search_frequency_grid(
        times,
        float(plan["candidate_eligibility"]["search_period_minimum_days"]),
        float(plan["candidate_eligibility"]["search_period_maximum_days"]),
    )
    scanner = prepare_covariance_gls_scanner(
        covariance,
        design,
        times,
        frequencies,
        float(plan["injections"]["reference_epoch_mjd_tdb"]),
    )
    setup_seconds = time.perf_counter() - setup_start

    source_records = freeze.get("reused_benchmark_artifacts", [])
    reused_records = _load_reused_records(data_root, order["reused"], source_records)
    trigger_by_id = {
        record["case"]["case_id"]: float(record["trigger"]["trigger_statistic"])
        for record in reused_records
    }

    output_root = data_root / "derived/pilot1/calibration-null-v0.1"
    output_root.mkdir(parents=True, exist_ok=True)
    implementation_sha = hash_file(root / "src/pulsar_pilot/pilot1_calibration.py", "sha256")
    execution_binding_sha = hashlib.sha256(
        f"{implementation_sha}:{freeze_verification['freeze_sha256']}".encode()
    ).hexdigest()
    inventory_sha = build_pilot1_case_inventory(plan)["inventory_sha256"]
    ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/calibration-null-v0.1-ledger.json",
        inventory_sha,
        execution_binding_sha,
    )
    prior_state = ledger.load()
    new_records: list[dict[str, Any]] = []
    noise_realizations: list[np.ndarray] = []
    factor = scanner.covariance_cholesky
    start = time.perf_counter()
    remaining_sequence = {case["case_id"]: index for index, case in enumerate(order["remaining"], 1)}
    for case in order["all"]:
        noise = generate_covariance_null(factor, np.random.default_rng(case["seed"]))
        noise_realizations.append(noise)
        if case["case_id"] in trigger_by_id:
            continue
        sequence = remaining_sequence[case["case_id"]]
        case_path = output_root / f"{sequence:04d}-{case['case_id']}.json"
        if case["case_id"] in prior_state["completed_cases"]:
            record = json.loads(case_path.read_text(encoding="utf-8"))
            trigger_by_id[case["case_id"]] = float(record["trigger"]["trigger_statistic"])
            new_records.append(record)
            continue
        scan_start = time.perf_counter()
        scan = scanner.scan(noise)
        record = {
            "schema_version": 1,
            "calibration_id": CALIBRATION_ID,
            "execution_binding_sha256": execution_binding_sha,
            "case": case,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
            "scan_wall_seconds": time.perf_counter() - scan_start,
        }
        case_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        ledger.record(case["case_id"], case_path, data_root)
        trigger_by_id[case["case_id"]] = float(record["trigger"]["trigger_statistic"])
        new_records.append(record)

    wall_seconds = time.perf_counter() - start
    ordered_statistics = np.asarray(
        [trigger_by_id[case["case_id"]] for case in order["all"]], dtype=float
    )
    quantile = float(plan["nulls"]["threshold_quantile"])
    threshold = conservative_nearest_rank(ordered_statistics, quantile)
    rank = int(np.ceil(quantile * len(ordered_statistics)))
    strict_exceedances = int(np.sum(ordered_statistics > threshold))
    diagnostics = null_ensemble_diagnostics(np.asarray(noise_realizations), factor)
    ledger_verification = ledger.verify(data_root)
    sanitized_log = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    warnings = classify_warning_lines(sanitized_log)
    thresholds = plan["promotion_benchmarks"]
    resources = plan["resource_caps"]
    peak_memory_gib = _peak_rss_gib()
    data_root_gib = _directory_size_gib(data_root)
    criteria = {
        "exactly_1000_calibration_nulls": len(trigger_by_id) == 1000,
        "exactly_10_verified_benchmark_reuses": len(reused_records) == 10,
        "exactly_990_new_scans": len(new_records) == 990,
        "sealed_evaluation_untouched": True,
        "observed_residual_search_not_executed": True,
        "conservative_nearest_rank_99_percent": (
            plan["nulls"]["threshold_estimator"] == "conservative_nearest_rank"
            and quantile == 0.99
            and rank == 990
        ),
        "strict_threshold_semantics": (
            plan["nulls"]["trigger_comparison"] == "strictly_greater_than_threshold"
            and strict_exceedances <= 10
        ),
        "null_whitened_variance": float(thresholds["null_whitened_variance_minimum"])
        <= float(diagnostics["whitened_variance"])
        <= float(thresholds["null_whitened_variance_maximum"]),
        "null_pooled_lag_correlation": float(
            diagnostics["maximum_absolute_ensemble_correlation"]
        )
        <= float(thresholds["null_maximum_absolute_ensemble_correlation"]),
        "warning_hygiene": warnings["status"] == "pass",
        "artifact_ledger_verified": (
            ledger_verification["status"] == "pass"
            and ledger_verification["completed_cases"] == 990
        ),
        "peak_memory_under_cap": peak_memory_gib <= float(resources["peak_memory_gib"]),
        "storage_under_cap": data_root_gib <= float(resources["complete_data_root_gib"]),
    }
    scorecard = {
        "overall": "PASS" if all(criteria.values()) else "FAIL",
        "passed": sum(criteria.values()),
        "total": len(criteria),
        "criteria": {key: "PASS" if value else "FAIL" for key, value in criteria.items()},
    }
    summary = {
        "schema_version": 1,
        "calibration_id": CALIBRATION_ID,
        "status": "pass" if scorecard["overall"] == "PASS" else "fail",
        "freeze": freeze_verification,
        "execution_binding_sha256": execution_binding_sha,
        "calibration_case_count": len(trigger_by_id),
        "reused_benchmark_case_count": len(reused_records),
        "new_scan_case_count": len(new_records),
        "sealed_evaluation_cases_executed": 0,
        "observed_residual_global_search_executed": False,
        "frequency_grid": grid,
        "threshold": {
            "status": "proposed_not_locked",
            "value_delta_chi2": threshold,
            "quantile": quantile,
            "estimator": "conservative_nearest_rank",
            "rank": rank,
            "sample_count": len(ordered_statistics),
            "strict_exceedance_count": strict_exceedances,
            "trigger_comparison": "strictly_greater_than_threshold",
        },
        "trigger_statistics_by_case": {
            case["case_id"]: trigger_by_id[case["case_id"]] for case in order["all"]
        },
        "null_diagnostics": diagnostics,
        "setup_wall_seconds": setup_seconds,
        "calibration_wall_seconds": wall_seconds,
        "peak_memory_gib": peak_memory_gib,
        "complete_data_root_gib": data_root_gib,
        "warnings": warnings,
        "ledger_verification": ledger_verification,
        "scorecard": scorecard,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    summary_path = data_root / "run_records/pilot1/calibration-null-v0.1-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["external_record"] = {
        "logical_path": logical_path(summary_path, data_root),
        "sha256": hash_file(summary_path, "sha256"),
        "bytes": summary_path.stat().st_size,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot1-calibration")
    parser.add_argument("command", choices=("plan", "verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "plan":
        result = calibration_plan(load_yaml(repository_root() / "config/pilot1.yaml"))
    elif args.command == "verify-freeze":
        result = verify_calibration_freeze()
    else:
        data_root = configured_data_root(args.data_root)
        require_initialized_data_root(data_root)
        result = run_calibration(data_root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result.get("status", "pass") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
