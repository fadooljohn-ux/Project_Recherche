from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _load_release, _peak_rss_gib
from .pilot1_runtime import (
    ResumableArtifactLedger,
    build_pilot1_case_inventory,
    build_search_frequency_grid,
    generate_covariance_null,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .provenance import hash_file, logical_path

EVALUATION_ID = "pilot1-sealed-null-evaluation-v0.1"
FREEZE_PATH = "protocol/PILOT1_EVALUATION_FREEZE_v0.1.json"
THRESHOLD_LOCK_PATH = "protocol/PILOT1_THRESHOLD_LOCK_v0.1.json"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_evaluation_order(plan: dict[str, Any]) -> list[dict[str, Any]]:
    inventory = build_pilot1_case_inventory(plan)
    evaluation = sorted(
        (case for case in inventory["null_cases"] if case["family"] == "sealed_evaluation"),
        key=lambda case: int(case["index"]),
    )
    calibration = [case for case in inventory["null_cases"] if case["family"] == "calibration"]
    if len(evaluation) != 500:
        raise RuntimeError("Frozen sealed evaluation must contain exactly 500 cases")
    if {case["case_id"] for case in evaluation} & {case["case_id"] for case in calibration}:
        raise RuntimeError("Calibration and evaluation case IDs overlap")
    if {case["seed"] for case in evaluation} & {case["seed"] for case in calibration}:
        raise RuntimeError("Calibration and evaluation seeds overlap")
    return evaluation


def evaluation_plan(plan: dict[str, Any], threshold_lock: dict[str, Any]) -> dict[str, Any]:
    order = build_evaluation_order(plan)
    return {
        "schema_version": 1,
        "evaluation_id": EVALUATION_ID,
        "execution_authorized": False,
        "case_count": len(order),
        "case_order_sha256": _canonical_hash(order),
        "calibration_cases_executed": 0,
        "observed_residual_search_authorized": False,
        "locked_threshold_delta_chi2": float(threshold_lock["value_delta_chi2"]),
        "trigger_comparison": threshold_lock["trigger_comparison"],
        "threshold_retuning_authorized": False,
        "binomial_interval": plan["nulls"]["evaluation_binomial_interval"],
    }


def verify_evaluation_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    threshold_path = root / THRESHOLD_LOCK_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    threshold_lock = json.loads(threshold_path.read_text(encoding="utf-8"))
    plan = evaluation_plan(load_yaml(root / "config/pilot1.yaml"), threshold_lock)
    failures: list[str] = []
    if threshold_lock.get("status") != "locked_before_sealed_evaluation":
        failures.append("Threshold is not locked before evaluation")
    if threshold_lock.get("trigger_comparison") != "strictly_greater_than_threshold":
        failures.append("Threshold comparison is not strict")
    if freeze.get("status") != "frozen_before_sealed_evaluation":
        failures.append("Evaluation freeze status is invalid")
    if freeze.get("authorization") != "exact_500_sealed_evaluation_null_scans_only":
        failures.append("Authorization is not limited to the sealed evaluation")
    if freeze.get("threshold_retuning_authorized") is not False:
        failures.append("Threshold retuning must remain unauthorized")
    if freeze.get("observed_residual_search_authorized") is not False:
        failures.append("Observed-residual search must remain unauthorized")
    if freeze.get("case_order_sha256") != plan["case_order_sha256"]:
        failures.append("Sealed evaluation case order mismatch")
    if float(freeze.get("locked_threshold_delta_chi2", float("nan"))) != float(
        threshold_lock["value_delta_chi2"]
    ):
        failures.append("Frozen and locked thresholds differ")
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
        "threshold_lock_sha256": hash_file(threshold_path, "sha256"),
    }


def wilson_interval_95(successes: int, trials: int) -> dict[str, float]:
    if trials <= 0 or successes < 0 or successes > trials:
        raise ValueError("Invalid binomial counts")
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = (proportion + z * z / (2.0 * trials)) / denominator
    half_width = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials)
        )
        / denominator
    )
    return {
        "proportion": proportion,
        "lower": max(0.0, center - half_width),
        "upper": min(1.0, center + half_width),
        "confidence": 0.95,
        "method": "wilson_score",
    }


def _verify_calibration_source(data_root: Path, threshold_lock: dict[str, Any]) -> None:
    source = threshold_lock["calibration_summary"]
    path = data_root / source["logical_path"]
    if not path.is_file():
        raise RuntimeError("Locked calibration summary is missing")
    if path.stat().st_size != int(source["bytes"]):
        raise RuntimeError("Locked calibration summary size mismatch")
    if hash_file(path, "sha256") != source["sha256"]:
        raise RuntimeError("Locked calibration summary hash mismatch")


def run_evaluation(data_root: Path) -> dict[str, Any]:
    freeze_verification = verify_evaluation_freeze()
    if freeze_verification["status"] != "pass":
        raise RuntimeError(f"Pilot 1 evaluation freeze failed: {freeze_verification}")
    root = repository_root()
    plan = load_yaml(root / "config/pilot1.yaml")
    threshold_lock = json.loads((root / THRESHOLD_LOCK_PATH).read_text(encoding="utf-8"))
    _verify_calibration_source(data_root, threshold_lock)
    threshold = float(threshold_lock["value_delta_chi2"])
    order = build_evaluation_order(plan)

    log_path = data_root / "run_records/pilot1/sealed-evaluation-v0.1.log"
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

    output_root = data_root / "derived/pilot1/sealed-evaluation-v0.1"
    output_root.mkdir(parents=True, exist_ok=True)
    implementation_sha = hash_file(root / "src/pulsar_pilot/pilot1_evaluation.py", "sha256")
    execution_binding_sha = hashlib.sha256(
        f"{implementation_sha}:{freeze_verification['freeze_sha256']}".encode()
    ).hexdigest()
    inventory_sha = build_pilot1_case_inventory(plan)["inventory_sha256"]
    ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/sealed-evaluation-v0.1-ledger.json",
        inventory_sha,
        execution_binding_sha,
    )
    prior_state = ledger.load()
    records: list[dict[str, Any]] = []
    noise_realizations: list[np.ndarray] = []
    factor = scanner.covariance_cholesky
    start = time.perf_counter()
    for sequence, case in enumerate(order, 1):
        noise = generate_covariance_null(factor, np.random.default_rng(case["seed"]))
        noise_realizations.append(noise)
        case_path = output_root / f"{sequence:04d}-{case['case_id']}.json"
        if case["case_id"] in prior_state["completed_cases"]:
            records.append(json.loads(case_path.read_text(encoding="utf-8")))
            continue
        scan_start = time.perf_counter()
        scan = scanner.scan(noise)
        statistic = float(scan["trigger_statistic"])
        record = {
            "schema_version": 1,
            "evaluation_id": EVALUATION_ID,
            "execution_binding_sha256": execution_binding_sha,
            "case": case,
            "locked_threshold_delta_chi2": threshold,
            "triggered": statistic > threshold,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
            "scan_wall_seconds": time.perf_counter() - scan_start,
        }
        case_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        ledger.record(case["case_id"], case_path, data_root)
        records.append(record)
    wall_seconds = time.perf_counter() - start

    false_positives = sum(bool(record["triggered"]) for record in records)
    interval = wilson_interval_95(false_positives, len(records))
    diagnostics = null_ensemble_diagnostics(np.asarray(noise_realizations), factor)
    ledger_verification = ledger.verify(data_root)
    sanitized_log = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    warnings = classify_warning_lines(sanitized_log)
    limits = plan["promotion_benchmarks"]
    resources = plan["resource_caps"]
    peak_memory_gib = _peak_rss_gib()
    data_root_gib = _directory_size_gib(data_root)
    criteria = {
        "exactly_500_sealed_evaluation_nulls": len(records) == 500,
        "calibration_evaluation_split_preserved": True,
        "locked_threshold_used_without_retuning": all(
            float(record["locked_threshold_delta_chi2"]) == threshold for record in records
        ),
        "strict_threshold_comparison": all(
            bool(record["triggered"])
            == (float(record["trigger"]["trigger_statistic"]) > threshold)
            for record in records
        ),
        "false_positive_rate": interval["proportion"]
        <= float(limits["evaluation_false_positive_rate_maximum"]),
        "false_positive_upper_95": interval["upper"]
        <= float(limits["evaluation_false_positive_rate_upper_95_maximum"]),
        "null_whitened_variance": float(limits["null_whitened_variance_minimum"])
        <= float(diagnostics["whitened_variance"])
        <= float(limits["null_whitened_variance_maximum"]),
        "null_pooled_lag_correlation": float(
            diagnostics["maximum_absolute_ensemble_correlation"]
        )
        <= float(limits["null_maximum_absolute_ensemble_correlation"]),
        "warning_hygiene": warnings["status"] == "pass",
        "artifact_ledger_verified": (
            ledger_verification["status"] == "pass"
            and ledger_verification["completed_cases"] == 500
        ),
        "observed_residual_search_not_executed": True,
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
        "evaluation_id": EVALUATION_ID,
        "status": "pass" if scorecard["overall"] == "PASS" else "fail",
        "freeze": freeze_verification,
        "execution_binding_sha256": execution_binding_sha,
        "case_count": len(records),
        "calibration_cases_executed": 0,
        "observed_residual_global_search_executed": False,
        "locked_threshold_delta_chi2": threshold,
        "threshold_retuned": False,
        "false_positives": false_positives,
        "false_positive_interval": interval,
        "frequency_grid": grid,
        "trigger_statistics_by_case": {
            record["case"]["case_id"]: float(record["trigger"]["trigger_statistic"])
            for record in records
        },
        "null_diagnostics": diagnostics,
        "setup_wall_seconds": setup_seconds,
        "evaluation_wall_seconds": wall_seconds,
        "peak_memory_gib": peak_memory_gib,
        "complete_data_root_gib": data_root_gib,
        "warnings": warnings,
        "ledger_verification": ledger_verification,
        "scorecard": scorecard,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    summary_path = data_root / "run_records/pilot1/sealed-evaluation-v0.1-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["external_record"] = {
        "logical_path": logical_path(summary_path, data_root),
        "sha256": hash_file(summary_path, "sha256"),
        "bytes": summary_path.stat().st_size,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot1-evaluation")
    parser.add_argument("command", choices=("plan", "verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = repository_root()
    if args.command == "plan":
        result = evaluation_plan(
            load_yaml(root / "config/pilot1.yaml"),
            json.loads((root / THRESHOLD_LOCK_PATH).read_text(encoding="utf-8")),
        )
    elif args.command == "verify-freeze":
        result = verify_evaluation_freeze()
    else:
        data_root = configured_data_root(args.data_root)
        require_initialized_data_root(data_root)
        result = run_evaluation(data_root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result.get("status", "pass") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
