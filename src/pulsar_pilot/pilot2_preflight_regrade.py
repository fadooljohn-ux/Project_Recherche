from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import repository_root, require_initialized_data_root
from .provenance import hash_file, logical_path

FREEZE_PATH = "protocol/PILOT2_PREFLIGHT_R1_REGRADE_FREEZE_v0.2.1.json"
SOURCE_RELATIVE = (
    "run_records/pilot2/pilot2-preflight-20260809T124548Z-summary.json"
)
SOURCE_SHA256 = "b007205c4751e9171c5ab04c54ce02ed7b5e48bc4ed2d219e1477db7542d8d6a"
APPLICATION_ERROR_MAXIMUM_MICROSECONDS = 0.001
AUDIT_AMPLITUDE_DIFFERENCE_MAXIMUM_MICROSECONDS = 0.01
AUDIT_PHASE_DIFFERENCE_MAXIMUM_RADIANS = 0.001
AUDIT_CHI2_DIFFERENCE_MAXIMUM = 0.1
EXPECTED_ARECIBO_OVERRIDE = (
    "Clock file from RECHERCHE_DATA_ROOT/controlled/nanograv15yr-v2.1.0/clock/"
    "time_ao.dat overrides global clock file time_ao.dat because of "
    "PINT_CLOCK_OVERRIDE"
)


def verify_regrade_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_json_only_preflight_regrade":
        failures.append("Regrade freeze status is invalid")
    if freeze.get("authorized_operation") != "existing_json_artifact_regrade_only":
        failures.append("Regrade authorization scope is invalid")
    if freeze.get("new_science_cases_authorized") is not False:
        failures.append("New science cases must remain unauthorized")
    if freeze.get("observed_periodic_search_authorized") is not False:
        failures.append("Observed periodic search must remain unauthorized")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        path = root / relative
        if not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"Hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_id": freeze.get("freeze_id"),
        "freeze_sha256": hash_file(freeze_path, "sha256"),
    }


def load_and_verify_source(data_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_path = data_root / SOURCE_RELATIVE
    if not source_path.is_file() or hash_file(source_path, "sha256") != SOURCE_SHA256:
        raise RuntimeError("Pilot 2 R1 source summary hash mismatch")
    summary = json.loads(source_path.read_text(encoding="utf-8"))
    artifacts = summary["synthetic_benchmark"]["case_artifacts"]
    if len(artifacts) != 50:
        raise RuntimeError("Pilot 2 R1 source does not contain 50 case artifacts")
    records: list[dict[str, Any]] = []
    for artifact in artifacts:
        path = data_root / artifact["logical_path"]
        if not path.is_file() or path.stat().st_size != int(artifact["bytes"]):
            raise RuntimeError(f"Case artifact missing or wrong size: {artifact['case_id']}")
        if hash_file(path, "sha256") != artifact["sha256"]:
            raise RuntimeError(f"Case artifact hash mismatch: {artifact['case_id']}")
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return summary, records


def evaluate_records(summary: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    audits = [record for record in records if "solver_comparison" in record]
    application_errors = [
        float(
            record["application"][
                "toa_adjustment_maximum_absolute_error_microseconds"
            ]
        )
        for record in audits
    ]
    residual_target_diagnostics = [
        float(
            record["application"][
                "uncentered_toa_residual_target_maximum_absolute_error_microseconds"
            ]
        )
        for record in audits
    ]
    audit_results: list[dict[str, Any]] = []
    for record in audits:
        primary = record["primary_solver"]
        full = record["full_covariance_solver"]
        comparison = record["solver_comparison"]
        application_error = float(
            record["application"][
                "toa_adjustment_maximum_absolute_error_microseconds"
            ]
        )
        tests = {
            "primary_returned_converged": bool(primary["returned_converged"]),
            "primary_fitter_converged": bool(primary["fitter_converged"]),
            "full_covariance_completed": bool(full["completed"]),
            "red_noise_preserved": bool(primary["release_red_noise_preserved"])
            and bool(full["release_red_noise_preserved"]),
            "wavex_absent": bool(primary["wavex_absent"])
            and bool(full["wavex_absent"]),
            "toa_application_error_within_limit": application_error
            <= APPLICATION_ERROR_MAXIMUM_MICROSECONDS,
            "amplitude_difference_within_limit": float(
                comparison["amplitude_difference_microseconds"]
            )
            <= AUDIT_AMPLITUDE_DIFFERENCE_MAXIMUM_MICROSECONDS,
            "phase_difference_within_limit": float(
                comparison["phase_difference_radians"]
            )
            <= AUDIT_PHASE_DIFFERENCE_MAXIMUM_RADIANS,
            "chi2_difference_within_limit": float(comparison["chi2_difference"])
            <= AUDIT_CHI2_DIFFERENCE_MAXIMUM,
        }
        audit_results.append(
            {
                "case_id": record["case"]["case_id"],
                "status": "PASS" if all(tests.values()) else "FAIL",
                "tests": tests,
                "application_error_microseconds": application_error,
                "comparison": comparison,
            }
        )
    warnings = summary["warnings"]
    unexpected = list(warnings["unexpected_warnings"])
    arecibo_matches = [line for line in unexpected if EXPECTED_ARECIBO_OVERRIDE in line]
    remaining_unexpected = [
        line for line in unexpected if EXPECTED_ARECIBO_OVERRIDE not in line
    ]
    warning_regrade = {
        "source_expected_warning_count": int(warnings["expected_warning_count"]),
        "arecibo_controlled_override_reclassified": len(arecibo_matches),
        "remaining_unexpected_warning_count": len(remaining_unexpected),
        "remaining_unexpected_warnings": remaining_unexpected,
        "status": "PASS"
        if len(arecibo_matches) == 1 and not remaining_unexpected
        else "FAIL",
    }
    benchmark_source = summary["synthetic_benchmark"]
    resources = summary["resources"]
    criteria = {
        "source_summary_hash_verified": True,
        "all_50_case_artifact_hashes_verified": len(records) == 50,
        "exactly_20_null_cases": sum(
            record["case"]["family"] == "null" for record in records
        )
        == 20,
        "exactly_30_injection_cases": sum(
            record["case"]["family"] == "injection" for record in records
        )
        == 30,
        "exactly_10_solver_audits": len(audits) == 10,
        "all_solver_audits_pass": all(
            result["status"] == "PASS" for result in audit_results
        ),
        "reproduction_passed": summary["reproduction"]["status"] == "pass",
        "expected_warning_hygiene": warning_regrade["status"] == "PASS",
        "projected_reference_calibration_under_six_hours": float(
            benchmark_source["runtime_projection"]["total_hours"]
        )
        <= 6.0,
        "wall_time_under_one_hour": float(resources["wall_hours"]) <= 1.0,
        "peak_memory_under_16_gib": float(resources["peak_memory_gib"]) <= 16.0,
        "data_root_under_1_5_gib": float(resources["complete_data_root_gib"])
        <= 1.5,
        "additional_download_bytes_zero": int(resources["additional_download_bytes"])
        == 0,
        "synthetic_scanner_used_no_observed_residual_vector": benchmark_source[
            "observed_residual_vector_used"
        ]
        is False,
        "observed_periodic_search_not_executed": summary[
            "observed_residual_global_search_executed"
        ]
        is False,
        "threshold_calibration_not_executed": summary[
            "threshold_calibration_executed"
        ]
        is False,
    }
    return {
        "status": "pass" if all(criteria.values()) else "fail",
        "criteria": criteria,
        "audit_results": audit_results,
        "warning_regrade": warning_regrade,
        "maximum_toa_application_error_microseconds": max(application_errors),
        "maximum_uncentered_residual_target_diagnostic_microseconds": max(
            residual_target_diagnostics
        ),
        "application_error_limit_microseconds": (
            APPLICATION_ERROR_MAXIMUM_MICROSECONDS
        ),
        "source_runtime_projection_hours": float(
            benchmark_source["runtime_projection"]["total_hours"]
        ),
        "source_resources": resources,
    }


def run_regrade(data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    freeze = verify_regrade_freeze()
    if freeze["status"] != "pass":
        raise RuntimeError(f"Pilot 2 regrade freeze failed: {freeze}")
    summary, records = load_and_verify_source(data_root)
    evaluation = evaluate_records(summary, records)
    recorded = datetime.now(UTC)
    result = {
        "schema_version": 1,
        "result_id": "pilot2-preflight-r1-deterministic-regrade-v0.2.1",
        "recorded_utc": recorded.isoformat().replace("+00:00", "Z"),
        "status": evaluation["status"],
        "target": "B1937+21",
        "operation": "json_only_regrade_no_science_execution",
        "freeze": freeze,
        "source_summary": {
            "logical_path": SOURCE_RELATIVE,
            "bytes": (data_root / SOURCE_RELATIVE).stat().st_size,
            "sha256": SOURCE_SHA256,
            "preserved_source_status": summary["status"],
        },
        "evaluation": evaluation,
        "scorecard": {
            "overall": evaluation["status"].upper(),
            "passed": sum(evaluation["criteria"].values()),
            "total": len(evaluation["criteria"]),
            "criteria": {
                key: "PASS" if value else "FAIL"
                for key, value in evaluation["criteria"].items()
            },
        },
        "new_science_cases_executed": 0,
        "new_random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
        "network_download_bytes": 0,
        "observed_periodic_search_authorized": False,
        "full_calibration_authorized": False,
    }
    output = (
        data_root
        / "run_records/pilot2/pilot2-preflight-r1-deterministic-regrade-v0.2.1.json"
    )
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    result["external_record"] = {
        "logical_path": logical_path(output, data_root),
        "bytes": output.stat().st_size,
        "sha256": hash_file(output, "sha256"),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-preflight-regrade")
    parser.add_argument("command", choices=("verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "verify-freeze":
        result = verify_regrade_freeze()
    else:
        if not args.data_root:
            parser.error("run requires --data-root")
        result = run_regrade(Path(args.data_root).expanduser().resolve())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result.get("status", "pass") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
