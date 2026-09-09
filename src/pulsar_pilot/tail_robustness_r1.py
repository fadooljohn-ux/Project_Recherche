from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _load_release, _peak_rss_gib
from .pilot1_evaluation import wilson_interval_95
from .pilot1_runtime import (
    ResumableArtifactLedger,
    build_search_frequency_grid,
    conservative_nearest_rank,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .provenance import hash_file, logical_path
from .tail_robustness import (
    _canonical_hash,
    _recovery_surface,
    _seed_for_case,
    generate_contaminated_null,
    theoretical_mixture_excess_kurtosis,
)
from .tail_robustness import build_null_orders as build_v0p1_null_orders

GATE_ID = "pilot1-tail-robustness-r1-v0.1"
CONFIG_PATH = "config/pilot1_tail_robustness_r1_v0.1.yaml"
FREEZE_PATH = "protocol/PILOT1_TAIL_ROBUSTNESS_R1_FREEZE_v0.1.json"
INITIAL_THRESHOLD_PATH = "protocol/PILOT1_THRESHOLD_LOCK_v0.1.json"
V0P1_CONFIG_PATH = "config/pilot1_tail_robustness_v0.1.yaml"


def build_null_orders(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    nulls = config["nulls"]
    orders: dict[str, list[dict[str, Any]]] = {}
    for family, count_key, seed_key in (
        ("calibration", "calibration_count", "calibration_base_seed"),
        ("evaluation", "evaluation_count", "evaluation_base_seed"),
    ):
        orders[family] = []
        for index in range(int(nulls[count_key])):
            case_id = f"tail-r1-null-{family}-{index:04d}"
            orders[family].append(
                {
                    "case_id": case_id,
                    "family": family,
                    "index": index,
                    "seed": _seed_for_case(int(nulls[seed_key]), case_id),
                }
            )
    calibration = orders["calibration"]
    evaluation = orders["evaluation"]
    prior = build_v0p1_null_orders(load_yaml(repository_root() / V0P1_CONFIG_PATH))
    r1_ids = {case["case_id"] for case in calibration + evaluation}
    r1_seeds = {case["seed"] for case in calibration + evaluation}
    prior_ids = {case["case_id"] for cases in prior.values() for case in cases}
    prior_seeds = {case["seed"] for cases in prior.values() for case in cases}
    if len(r1_ids) != len(calibration) + len(evaluation):
        raise RuntimeError("R1 case IDs are not unique")
    if len(r1_seeds) != len(calibration) + len(evaluation):
        raise RuntimeError("R1 seeds are not unique")
    if r1_ids & prior_ids or r1_seeds & prior_seeds:
        raise RuntimeError("R1 nulls overlap the original tail gate")
    return orders


def inventory_hashes(config: dict[str, Any]) -> dict[str, str]:
    orders = build_null_orders(config)
    return {key: _canonical_hash(value) for key, value in orders.items()}


def verify_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    config = load_yaml(root / CONFIG_PATH)
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_tail_robustness_r1_execution":
        failures.append("freeze status is invalid")
    if freeze.get("authorization") != "exact_disjoint_r1_nulls_and_threshold_only_regrade":
        failures.append("freeze authorization is invalid")
    if freeze.get("observed_residual_access_authorized") is not False:
        failures.append("observed residual access must remain unauthorized")
    if freeze.get("failed_evaluation_reuse_authorized") is not False:
        failures.append("failed evaluation reuse must remain unauthorized")
    if freeze.get("inventory_sha256") != inventory_hashes(config):
        failures.append("inventory hash mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        path = root / relative
        if not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_sha256": hash_file(freeze_path, "sha256"),
        "inventory_sha256": inventory_hashes(config),
    }


def verify_external_prerequisites(data_root: Path) -> dict[str, Any]:
    freeze = json.loads((repository_root() / FREEZE_PATH).read_text(encoding="utf-8"))
    failures: list[str] = []
    for relative, expected in freeze.get("external_prerequisites", {}).items():
        path = data_root / relative
        if not path.is_file() or path.stat().st_size != int(expected["bytes"]):
            failures.append(f"missing or wrong size: {relative}")
        elif hash_file(path, "sha256") != expected["sha256"]:
            failures.append(f"hash mismatch: {relative}")
    return {"status": "pass" if not failures else "fail", "failures": failures}


def _write_case(
    path: Path,
    record: dict[str, Any],
    ledger: ResumableArtifactLedger,
    data_root: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ledger.record(record["case"]["case_id"], path, data_root)


def _load_verified_recovery_records(data_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    ledger_path = data_root / "run_records/pilot1/tail-robustness-recovery-v0.1-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for case_id, artifact in sorted(ledger["completed_cases"].items()):
        path = data_root / artifact["logical_path"]
        if not path.is_file() or hash_file(path, "sha256") != artifact["sha256"]:
            failures.append(case_id)
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["case"]["case_id"] != case_id:
            failures.append(case_id)
            continue
        records.append(record)
    return records, failures


def run_gate(data_root: Path) -> dict[str, Any]:
    freeze = verify_freeze()
    if freeze["status"] != "pass":
        raise RuntimeError(f"R1 freeze failed: {freeze}")
    prerequisites = verify_external_prerequisites(data_root)
    if prerequisites["status"] != "pass":
        raise RuntimeError(f"R1 external prerequisites failed: {prerequisites}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    parent_plan = load_yaml(root / "config/pilot1.yaml")
    initial_threshold = float(
        json.loads((root / INITIAL_THRESHOLD_PATH).read_text(encoding="utf-8"))[
            "value_delta_chi2"
        ]
    )
    contamination = config["contamination_model"]
    probability = float(contamination["contaminated_coordinate_probability"])
    multiplier = float(contamination["contaminated_standard_deviation_multiplier"])
    orders = build_null_orders(config)

    log_path = data_root / "run_records/pilot1/tail-robustness-r1-v0.1.log"
    import pint.logging

    pint.logging.setup(
        level="INFO", sink=log_path, usecolors=False, capturewarnings=True, removeprior=True
    )
    start = time.perf_counter()
    release_model, release_toas = _load_release(data_root)
    from pint.fitter import WidebandTOAFitter

    fitter = WidebandTOAFitter(release_toas, release_model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(release_toas.table["tdbld"].data, dtype=float)
    frequencies, grid = build_search_frequency_grid(
        times,
        float(parent_plan["candidate_eligibility"]["search_period_minimum_days"]),
        float(parent_plan["candidate_eligibility"]["search_period_maximum_days"]),
    )
    scanner = prepare_covariance_gls_scanner(
        covariance,
        design,
        times,
        frequencies,
        float(parent_plan["injections"]["reference_epoch_mjd_tdb"]),
    )
    factor = scanner.covariance_cholesky
    execution_binding = hashlib.sha256(
        (
            hash_file(root / "src/pulsar_pilot/tail_robustness_r1.py", "sha256")
            + ":"
            + freeze["freeze_sha256"]
        ).encode()
    ).hexdigest()
    output_root = data_root / "derived/pilot1/tail-robustness-r1-v0.1"

    calibration_ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/tail-robustness-r1-calibration-v0.1-ledger.json",
        freeze["inventory_sha256"]["calibration"],
        execution_binding,
    )
    calibration_state = calibration_ledger.load()
    calibration_records: list[dict[str, Any]] = []
    calibration_samples: list[np.ndarray] = []
    for sequence, case in enumerate(orders["calibration"], 1):
        noise, contaminated_count = generate_contaminated_null(
            factor, np.random.default_rng(case["seed"]), probability, multiplier
        )
        calibration_samples.append(noise)
        path = output_root / "calibration" / f"{sequence:04d}-{case['case_id']}.json"
        if case["case_id"] in calibration_state["completed_cases"]:
            calibration_records.append(json.loads(path.read_text(encoding="utf-8")))
            continue
        scan = scanner.scan(noise)
        record = {
            "schema_version": 1,
            "gate_id": GATE_ID,
            "case": case,
            "contaminated_coordinate_count": contaminated_count,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
        }
        _write_case(path, record, calibration_ledger, data_root)
        calibration_records.append(record)

    contamination_threshold = conservative_nearest_rank(
        np.asarray(
            [record["trigger"]["trigger_statistic"] for record in calibration_records]
        ),
        float(config["nulls"]["threshold_quantile"]),
    )
    robust_threshold = max(initial_threshold, contamination_threshold)

    evaluation_ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/tail-robustness-r1-evaluation-v0.1-ledger.json",
        freeze["inventory_sha256"]["evaluation"],
        execution_binding,
    )
    evaluation_state = evaluation_ledger.load()
    evaluation_records: list[dict[str, Any]] = []
    evaluation_samples: list[np.ndarray] = []
    for sequence, case in enumerate(orders["evaluation"], 1):
        noise, contaminated_count = generate_contaminated_null(
            factor, np.random.default_rng(case["seed"]), probability, multiplier
        )
        evaluation_samples.append(noise)
        path = output_root / "evaluation" / f"{sequence:04d}-{case['case_id']}.json"
        if case["case_id"] in evaluation_state["completed_cases"]:
            evaluation_records.append(json.loads(path.read_text(encoding="utf-8")))
            continue
        scan = scanner.scan(noise)
        statistic = float(scan["trigger_statistic"])
        record = {
            "schema_version": 1,
            "gate_id": GATE_ID,
            "case": case,
            "contaminated_coordinate_count": contaminated_count,
            "triggered": statistic > robust_threshold,
            "robust_threshold_delta_chi2": robust_threshold,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
        }
        _write_case(path, record, evaluation_ledger, data_root)
        evaluation_records.append(record)

    false_positives = sum(bool(record["triggered"]) for record in evaluation_records)
    interval = wilson_interval_95(false_positives, len(evaluation_records))
    source_recovery, recovery_integrity_failures = _load_verified_recovery_records(data_root)
    regraded = [
        {
            **record,
            "triggered": float(record["trigger"]["trigger_statistic"]) > robust_threshold,
            "r1_robust_threshold_delta_chi2": robust_threshold,
        }
        for record in source_recovery
    ]
    surface = _recovery_surface(regraded)
    detected = [record for record in regraded if record["triggered"]]
    frequency_recovery_rate = (
        sum(bool(record["frequency_recovered"]) for record in detected) / len(detected)
        if detected
        else 0.0
    )
    refit_records = [record for record in regraded if "ordinary_fit" in record]
    full_audits = [record for record in regraded if "audit_comparison" in record]
    refit_failures = sum(
        not (
            record["ordinary_fit"]["returned_converged"]
            and record["ordinary_fit"]["fitter_converged"]
            and record["joint_fit"]["returned_converged"]
            and record["joint_fit"]["fitter_converged"]
        )
        for record in refit_records
    )
    audit_failures = int(
        json.loads(
            (data_root / "run_records/pilot1/tail-robustness-v0.1-summary.json").read_text(
                encoding="utf-8"
            )
        )["recovery"]["full_covariance_audit_failures"]
    )
    warnings = classify_warning_lines(
        [
            line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
    )
    elapsed_hours = (time.perf_counter() - start) / 3600.0
    ledgers = {
        "calibration": calibration_ledger.verify(data_root),
        "evaluation": evaluation_ledger.verify(data_root),
    }
    hard = config["hard_benchmarks"]
    criteria = {
        "freeze_verified": freeze["status"] == "pass",
        "external_prerequisites_verified": prerequisites["status"] == "pass",
        "exactly_2000_new_calibration_nulls": len(calibration_records) == 2000,
        "exactly_1000_new_evaluation_nulls": len(evaluation_records) == 1000,
        "r1_null_sets_disjoint": True,
        "r1_threshold_not_below_initial_v0p1": robust_threshold >= initial_threshold,
        "evaluation_false_positive_rate": interval["proportion"]
        <= float(hard["evaluation_false_positive_rate_maximum"]),
        "evaluation_false_positive_upper_95": interval["upper"]
        <= float(hard["evaluation_false_positive_rate_upper_95_maximum"]),
        "immutable_recovery_artifacts_verified": len(recovery_integrity_failures)
        <= int(hard["artifact_integrity_failures_maximum"]),
        "exactly_160_regraded_recovery_cases": len(regraded) == 160,
        "frequency_recovery": frequency_recovery_rate
        >= float(hard["injected_frequency_recovery_rate_minimum"]),
        "monotonic_recovery": surface["periods_with_monotonic_recovery_fraction"]
        >= int(hard["minimum_periods_with_monotonic_detection_fraction"]),
        "sensitivity_bracketing": surface[
            "periods_with_bracketed_50_and_90_percent_sensitivity"
        ]
        >= int(hard["minimum_periods_with_bracketed_50_and_90_percent_sensitivity"]),
        "complete_refit_failures": refit_failures
        <= int(hard["complete_refit_failures_maximum"]),
        "full_covariance_audit_failures": audit_failures
        <= int(hard["full_covariance_audit_failures_maximum"]),
        "new_artifact_ledgers_verified": all(
            item["status"] == "pass" for item in ledgers.values()
        ),
        "warning_hygiene": warnings["status"] == "pass",
        "runtime_under_cap": elapsed_hours <= float(hard["incremental_wall_hours_maximum"]),
        "peak_memory_under_cap": _peak_rss_gib() <= float(hard["peak_memory_gib"]),
        "storage_under_cap": _directory_size_gib(data_root)
        <= float(hard["complete_data_root_gib"]),
        "observed_residual_access_not_executed": True,
        "failed_evaluation_set_not_reused_for_grading": True,
    }
    scorecard = {
        "overall": "PASS" if all(criteria.values()) else "FAIL",
        "passed": sum(criteria.values()),
        "total": len(criteria),
        "criteria": {key: "PASS" if value else "FAIL" for key, value in criteria.items()},
    }
    result = {
        "schema_version": 1,
        "gate_id": GATE_ID,
        "status": "pass" if scorecard["overall"] == "PASS" else "fail",
        "freeze": freeze,
        "external_prerequisites": prerequisites,
        "contamination_model": {
            **contamination,
            "verified_theoretical_excess_kurtosis": theoretical_mixture_excess_kurtosis(
                probability, multiplier
            ),
        },
        "thresholds": {
            "initial_v0p1_delta_chi2": initial_threshold,
            "r1_contamination_calibration_delta_chi2": contamination_threshold,
            "r1_robust_locked_delta_chi2": robust_threshold,
        },
        "evaluation": {
            "false_positives": false_positives,
            "trials": len(evaluation_records),
            "interval": interval,
        },
        "recovery_regrade": {
            "source_case_count": len(source_recovery),
            "integrity_failures": recovery_integrity_failures,
            "detected_count": len(detected),
            "frequency_recovery_rate_among_triggers": frequency_recovery_rate,
            "surface": surface,
            "complete_refit_count": len(refit_records),
            "complete_refit_failures": refit_failures,
            "full_covariance_audit_count": len(full_audits),
            "full_covariance_audit_failures": audit_failures,
        },
        "synthetic_frequency_grid": grid,
        "null_diagnostics": {
            "calibration": null_ensemble_diagnostics(
                np.asarray(calibration_samples), factor
            ),
            "evaluation": null_ensemble_diagnostics(
                np.asarray(evaluation_samples), factor
            ),
        },
        "warnings": warnings,
        "ledgers": ledgers,
        "incremental_wall_hours": elapsed_hours,
        "peak_memory_gib": _peak_rss_gib(),
        "complete_data_root_gib": _directory_size_gib(data_root),
        "scorecard": scorecard,
        "observed_residual_accessed": False,
        "observed_residual_periodic_search_executed": False,
        "failed_v0p1_evaluation_reused_for_grading": False,
        "next_gate": (
            "separately_reviewed_one_shot_observed_residual_search_freeze"
            if scorecard["overall"] == "PASS"
            else "detector_rebaseline_or_robust_statistic_replacement"
        ),
    }
    summary_path = data_root / "run_records/pilot1/tail-robustness-r1-v0.1-summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["external_record"] = {
        "logical_path": logical_path(summary_path, data_root),
        "bytes": summary_path.stat().st_size,
        "sha256": hash_file(summary_path, "sha256"),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot1-tail-robustness-r1")
    parser.add_argument("command", choices=("plan", "verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "plan":
        config = load_yaml(repository_root() / CONFIG_PATH)
        result = {
            "schema_version": 1,
            "gate_id": GATE_ID,
            "status": "planned",
            "inventory_sha256": inventory_hashes(config),
            "counts": {
                key: len(value) for key, value in build_null_orders(config).items()
            },
            "observed_residual_access_authorized": False,
        }
    elif args.command == "verify-freeze":
        result = verify_freeze()
    else:
        data_root = configured_data_root(args.data_root)
        require_initialized_data_root(data_root)
        result = run_gate(data_root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result.get("status") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
