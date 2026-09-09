from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import resource
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .c1 import generate_circular_delay_us
from .c1r1 import (
    _joint_downhill_fit,
    _joint_full_covariance_fit,
    wrapped_phase_difference,
)
from .config import load_pilot_config, load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_runtime import (
    ResumableArtifactLedger,
    build_pilot1_case_inventory,
    build_search_frequency_grid,
    generate_covariance_null,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .provenance import hash_file, logical_path

BENCHMARK_ID = "pilot1-first-50-corrective-replay-v0.2"
BENCHMARK_SIZE = 50
FREEZE_PATH = "protocol/PILOT1_EXECUTION_FREEZE_v0.2.json"


def _sha_rank(case: dict[str, Any]) -> str:
    return hashlib.sha256(case["case_id"].encode()).hexdigest()


def _without_ids(cases: list[dict[str, Any]], used: set[str]) -> list[dict[str, Any]]:
    return [case for case in cases if case["case_id"] not in used]


def build_benchmark50_order(plan: dict[str, Any]) -> list[dict[str, Any]]:
    inventory = build_pilot1_case_inventory(plan)
    nulls = inventory["null_cases"]
    injections = inventory["injection_cases"]
    by_id = {case["case_id"]: case for case in injections}
    used: set[str] = set()
    selected: list[dict[str, Any]] = []

    calibration = sorted(
        (case for case in nulls if case["family"] == "calibration"), key=_sha_rank
    )[:10]
    selected.extend({**case, "benchmark_role": "calibration_null"} for case in calibration)

    audit_cases = [
        by_id[case_id] for case_id in inventory["independent_audit_case_ids"][:4]
    ]
    for case in audit_cases:
        used.add(case["case_id"])
        selected.append(
            {**case, "benchmark_role": "full_covariance_audit", "full_covariance_audit": True}
        )

    main = sorted(
        _without_ids([case for case in injections if case["family"] == "main"], used),
        key=_sha_rank,
    )[:28]
    for case in main:
        used.add(case["case_id"])
        selected.append({**case, "benchmark_role": "main_matrix"})

    annual_candidates = _without_ids(
        [
            case
            for case in injections
            if case["family"] == "annual" and case["period_days"] == 365.25
        ],
        used,
    )
    annual = sorted(annual_candidates, key=lambda case: case["phase_radians"])
    if len(annual) < 4:
        annual.extend(
            sorted(
                _without_ids(
                    [case for case in injections if case["family"] == "annual"],
                    used | {case["case_id"] for case in annual},
                ),
                key=_sha_rank,
            )[: 4 - len(annual)]
        )
    for case in annual[:4]:
        used.add(case["case_id"])
        selected.append({**case, "benchmark_role": "annual_identifiability"})

    boundary_candidates = _without_ids(
        [case for case in injections if case["family"] == "boundary"], used
    )
    boundary: list[dict[str, Any]] = []
    for period in sorted({case["period_days"] for case in boundary_candidates}):
        for amplitude in sorted(
            {case["amplitude_microseconds"] for case in boundary_candidates}
        ):
            matches = [
                case
                for case in boundary_candidates
                if case["period_days"] == period
                and case["amplitude_microseconds"] == amplitude
            ]
            boundary.append(min(matches, key=_sha_rank))
    for case in boundary:
        used.add(case["case_id"])
        selected.append({**case, "benchmark_role": "search_boundary"})

    if len(selected) != BENCHMARK_SIZE:
        raise RuntimeError(f"Benchmark order must contain exactly {BENCHMARK_SIZE} cases")
    case_ids = [case["case_id"] for case in selected]
    if len(set(case_ids)) != BENCHMARK_SIZE:
        raise RuntimeError("Benchmark order contains duplicate case IDs")
    for sequence, case in enumerate(selected, 1):
        case["sequence"] = sequence
        case.setdefault("full_covariance_audit", False)
    return selected


def benchmark50_plan(plan: dict[str, Any]) -> dict[str, Any]:
    order = build_benchmark50_order(plan)
    payload = {
        "schema_version": 1,
        "benchmark_id": BENCHMARK_ID,
        "execution_authorized": False,
        "sealed_evaluation_cases": 0,
        "case_count": len(order),
        "role_counts": {
            role: sum(case["benchmark_role"] == role for case in order)
            for role in sorted({case["benchmark_role"] for case in order})
        },
        "full_covariance_audits": sum(case["full_covariance_audit"] for case in order),
        "case_order": order,
    }
    payload["order_sha256"] = hashlib.sha256(
        json.dumps(order, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def verify_execution_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_first_pilot1_synthetic_realization":
        failures.append("Execution freeze status is invalid")
    if freeze.get("authorization") != "same_first_50_corrective_replay_only":
        failures.append("Execution authorization is not limited to the corrective replay")
    if freeze.get("sealed_evaluation_authorized") is not False:
        failures.append("Sealed evaluation must remain unauthorized")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        if hash_file(root / relative, "sha256") != expected:
            failures.append(f"Hash mismatch: {relative}")
    if hash_file(root / "pixi.lock", "sha256") != freeze.get("pixi_lock_sha256"):
        failures.append("Pixi lock hash mismatch")
    plan = load_yaml(root / "config" / "pilot1.yaml")
    actual_order_hash = benchmark50_plan(plan)["order_sha256"]
    if actual_order_hash != freeze.get("benchmark_order_sha256"):
        failures.append("Benchmark order hash mismatch")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_id": freeze.get("freeze_id"),
        "freeze_sha256": hash_file(freeze_path, "sha256"),
    }


def _peak_rss_gib() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**3 if platform.system() == "Darwin" else 1024**2
    return peak / divisor


def _directory_size_gib(path: Path) -> float:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) / 1024**3


def _load_release(data_root: Path) -> tuple[Any, Any]:
    controlled = data_root / "controlled" / "nanograv15yr-v2.1.0"
    clock = controlled / "clock"
    par = controlled / "wideband/par/J1744-1134_PINT_20230131.wb.par"
    tim = controlled / "wideband/tim/J1744-1134_PINT_20230131.wb.tim"
    os.environ["PINT_CLOCK_OVERRIDE"] = str(clock)
    os.environ["XDG_CACHE_HOME"] = str(data_root / "derived/cache")
    from pint.models import get_model_and_toas

    return get_model_and_toas(
        par,
        tim,
        ephem="DE440",
        include_bipm=True,
        bipm_version="BIPM2019",
        planets=True,
        usepickle=False,
        limits="warn",
    )


def _synthetic_toas(
    release_toas: Any,
    release_model: Any,
    requested_residuals: np.ndarray,
) -> tuple[Any, dict[str, float]]:
    import astropy.units as u
    from pint.residuals import WidebandTOAResiduals

    residual_options = {"toa_resid_args": {"subtract_mean": False}}
    baseline = WidebandTOAResiduals(
        release_toas, release_model, **residual_options
    ).calc_wideband_resids()
    count = len(release_toas)
    synthetic = copy.deepcopy(release_toas)
    requested_adjustment_seconds = requested_residuals[:count] - baseline[:count]
    original_mjds = synthetic.get_mjds(high_precision=True).copy()
    synthetic.adjust_TOAs(requested_adjustment_seconds * u.s)
    adjusted_mjds = synthetic.get_mjds(high_precision=True).copy()
    actual_adjustment_microseconds = np.asarray(
        [
            (adjusted - original).to_value(u.us)
            for adjusted, original in zip(adjusted_mjds, original_mjds)
        ]
    )
    for flags, adjustment in zip(
        synthetic.table["flags"], requested_residuals[count:] - baseline[count:]
    ):
        flags["pp_dm"] = repr(float(flags["pp_dm"]) + float(adjustment))
    achieved = WidebandTOAResiduals(
        synthetic, release_model, **residual_options
    ).calc_wideband_resids()
    return synthetic, {
        "toa_adjustment_maximum_absolute_error_microseconds": float(
            np.max(
                np.abs(
                    actual_adjustment_microseconds
                    - requested_adjustment_seconds * 1e6
                )
            )
        ),
        "uncentered_toa_residual_target_maximum_absolute_error_microseconds": float(
            np.max(np.abs(achieved[:count] - requested_residuals[:count])) * 1e6
        ),
        "dm_maximum_absolute_error": float(
            np.max(np.abs(achieved[count:] - requested_residuals[count:]))
        ),
    }


def run_benchmark50(data_root: Path) -> dict[str, Any]:
    freeze = verify_execution_freeze()
    if freeze["status"] != "pass":
        raise RuntimeError(f"Pilot 1 execution freeze failed: {freeze}")
    root = repository_root()
    plan = load_yaml(root / "config/pilot1.yaml")
    order = build_benchmark50_order(plan)
    config = load_pilot_config(root / "config/target.yaml")
    log_path = data_root / "run_records/pilot1/benchmark50-r1.log"
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

    from pint.fitter import WidebandDownhillFitter, WidebandTOAFitter

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
    epoch = float(plan["injections"]["reference_epoch_mjd_tdb"])
    scanner = prepare_covariance_gls_scanner(covariance, design, times, frequencies, epoch)
    setup_seconds = time.perf_counter() - setup_start

    output_root = data_root / "derived/pilot1/benchmark50-r1"
    output_root.mkdir(parents=True, exist_ok=True)
    implementation_sha = hash_file(root / "src/pulsar_pilot/pilot1_benchmark.py", "sha256")
    order_sha = benchmark50_plan(plan)["order_sha256"]
    execution_binding_sha = hashlib.sha256(
        f"{implementation_sha}:{order_sha}".encode()
    ).hexdigest()
    inventory_sha = build_pilot1_case_inventory(plan)["inventory_sha256"]
    ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/benchmark50-r1-ledger.json",
        inventory_sha,
        execution_binding_sha,
    )
    state = ledger.load()
    noise_realizations: list[np.ndarray] = []
    case_records: list[dict[str, Any]] = []
    count = len(release_toas)
    factor = scanner.covariance_cholesky
    start = time.perf_counter()
    for case in order:
        case_path = output_root / f"{case['sequence']:02d}-{case['case_id']}.json"
        noise = generate_covariance_null(factor, np.random.default_rng(case["seed"]))
        noise_realizations.append(noise)
        if case["case_id"] in state["completed_cases"]:
            case_records.append(json.loads(case_path.read_text(encoding="utf-8")))
            continue
        requested = noise.copy()
        signal_us = np.zeros(count)
        if case["benchmark_role"] != "calibration_null":
            signal_us = np.asarray(
                generate_circular_delay_us(
                    times.astype(np.longdouble),
                    float(case["period_days"]),
                    float(case["amplitude_microseconds"]),
                    float(case["phase_radians"]),
                    epoch,
                ),
                dtype=float,
            )
            requested[:count] += signal_us * 1e-6
        scan_start = time.perf_counter()
        scan = scanner.scan(requested)
        record: dict[str, Any] = {
            "schema_version": 1,
            "benchmark_id": BENCHMARK_ID,
            "execution_binding_sha256": execution_binding_sha,
            "case": case,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
            "scan_wall_seconds": time.perf_counter() - scan_start,
        }
        if case["benchmark_role"] != "calibration_null":
            synthetic, application = _synthetic_toas(release_toas, release_model, requested)
            ordinary_start = time.perf_counter()
            ordinary = WidebandDownhillFitter(synthetic, copy.deepcopy(release_model))
            ordinary_returned = bool(ordinary.fit_toas(maxiter=config.max_fit_iterations))
            ordinary_seconds = time.perf_counter() - ordinary_start
            joint_start = time.perf_counter()
            joint = _joint_downhill_fit(
                synthetic,
                release_model,
                1.0 / float(case["period_days"]),
                epoch,
                config.max_fit_iterations,
            )
            joint_seconds = time.perf_counter() - joint_start
            record["application"] = application
            record["ordinary_fit"] = {
                "returned_converged": ordinary_returned,
                "fitter_converged": bool(ordinary.converged),
                "wall_seconds": ordinary_seconds,
            }
            record["joint_fit"] = {
                key: value
                for key, value in joint.items()
                if key not in {"fitter", "model", "residuals"}
            }
            record["joint_fit"]["wall_seconds"] = joint_seconds
            record["injected_amplitude_microseconds"] = float(
                case["amplitude_microseconds"]
            )
            record["injected_phase_radians"] = float(case["phase_radians"])
            if case["full_covariance_audit"]:
                audit_start = time.perf_counter()
                audit = _joint_full_covariance_fit(
                    synthetic,
                    release_model,
                    1.0 / float(case["period_days"]),
                    epoch,
                    config.max_fit_iterations,
                )
                record["full_covariance_audit"] = {
                    key: value
                    for key, value in audit.items()
                    if key not in {"fitter", "model", "residuals"}
                }
                record["full_covariance_audit"]["wall_seconds"] = (
                    time.perf_counter() - audit_start
                )
                record["audit_comparison"] = {
                    "amplitude_difference_microseconds": abs(
                        float(joint["amplitude_us"]) - float(audit["amplitude_us"])
                    ),
                    "phase_difference_radians": abs(
                        wrapped_phase_difference(
                            float(joint["phase_radians"]),
                            float(audit["phase_radians"]),
                        )
                    ),
                    "chi2_difference": abs(float(joint["chi2"]) - float(audit["chi2"])),
                }
        case_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        ledger.record(case["case_id"], case_path, data_root)
        case_records.append(record)

    diagnostics = (
        null_ensemble_diagnostics(np.asarray(noise_realizations), factor)
        if noise_realizations
        else {"status": "not_recomputed_on_fully_resumed_run"}
    )
    total_seconds = time.perf_counter() - start
    scans = [float(item["scan_wall_seconds"]) for item in case_records]
    primary_fits = [
        float(fit["wall_seconds"])
        for item in case_records
        for fit in (item.get("ordinary_fit"), item.get("joint_fit"))
        if fit is not None
    ]
    audits = [
        float(item["full_covariance_audit"]["wall_seconds"])
        for item in case_records
        if "full_covariance_audit" in item
    ]
    planned = {
        "scan_seconds": float(np.mean(scans)) * 1784,
        "primary_fit_seconds": float(np.mean(primary_fits)) * 568,
        "audit_seconds": float(np.mean(audits)) * 29,
    }
    projected_seconds = setup_seconds + sum(planned.values())
    application_errors = [
        float(item["application"]["toa_adjustment_maximum_absolute_error_microseconds"])
        for item in case_records
        if "application" in item
    ]
    residual_target_errors = [
        float(
            item["application"][
                "uncentered_toa_residual_target_maximum_absolute_error_microseconds"
            ]
        )
        for item in case_records
        if "application" in item
    ]
    audit_comparisons = [
        item["audit_comparison"] for item in case_records if "audit_comparison" in item
    ]
    sanitized_log = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    warnings = classify_warning_lines(sanitized_log)
    peak_memory_gib = _peak_rss_gib()
    data_root_gib = _directory_size_gib(data_root)
    resources = plan["resource_caps"]
    thresholds = plan["promotion_benchmarks"]
    audit_limits = plan["independent_audit"]
    ledger_verification = ledger.verify(data_root)
    criteria = {
        "exactly_50_cases_completed": len(case_records) == 50,
        "sealed_evaluation_untouched": True,
        "observed_residual_search_not_executed": True,
        "null_whitened_variance": float(thresholds["null_whitened_variance_minimum"])
        <= float(diagnostics.get("whitened_variance", float("nan")))
        <= float(thresholds["null_whitened_variance_maximum"]),
        "null_pooled_lag_correlation": float(
            diagnostics.get("maximum_absolute_ensemble_correlation", float("inf"))
        )
        <= float(thresholds["null_maximum_absolute_ensemble_correlation"]),
        "toa_application_accuracy": max(application_errors, default=float("inf"))
        <= float(plan["injections"]["maximum_application_error_microseconds"]),
        "ordinary_fits_converged": all(
            item.get("ordinary_fit", {}).get("returned_converged", False)
            and item.get("ordinary_fit", {}).get("fitter_converged", False)
            for item in case_records
            if "ordinary_fit" in item
        ),
        "joint_fits_converged": all(
            item.get("joint_fit", {}).get("returned_converged", False)
            and item.get("joint_fit", {}).get("fitter_converged", False)
            for item in case_records
            if "joint_fit" in item
        ),
        "four_full_covariance_audits": len(audit_comparisons) == 4,
        "audit_amplitude_equivalence": all(
            float(item["amplitude_difference_microseconds"])
            <= float(audit_limits["amplitude_difference_maximum_microseconds"])
            for item in audit_comparisons
        ),
        "audit_phase_equivalence": all(
            float(item["phase_difference_radians"])
            <= float(audit_limits["phase_difference_maximum_radians"])
            for item in audit_comparisons
        ),
        "audit_chi2_equivalence": all(
            float(item["chi2_difference"])
            <= float(audit_limits["chi2_difference_maximum"])
            for item in audit_comparisons
        ),
        "warning_hygiene": warnings["status"] == "pass",
        "projected_runtime_under_cap": projected_seconds
        <= float(resources["macbook_total_wall_hours"]) * 3600.0,
        "peak_memory_under_cap": peak_memory_gib <= float(resources["peak_memory_gib"]),
        "storage_under_cap": data_root_gib <= float(resources["complete_data_root_gib"]),
        "artifact_ledger_verified": ledger_verification["status"] == "pass",
    }
    scorecard = {
        "overall": "PASS" if all(criteria.values()) else "FAIL",
        "passed": sum(criteria.values()),
        "total": len(criteria),
        "criteria": {key: "PASS" if value else "FAIL" for key, value in criteria.items()},
    }
    summary = {
        "schema_version": 1,
        "benchmark_id": BENCHMARK_ID,
        "execution_binding_sha256": execution_binding_sha,
        "status": "pass" if scorecard["overall"] == "PASS" else "fail",
        "case_count": len(case_records),
        "freeze": freeze,
        "frequency_grid": grid,
        "setup_wall_seconds": setup_seconds,
        "benchmark_wall_seconds": total_seconds,
        "projected_complete_wall_seconds": projected_seconds,
        "projected_complete_wall_hours": projected_seconds / 3600.0,
        "projection_components": planned,
        "peak_memory_gib": peak_memory_gib,
        "complete_data_root_gib": data_root_gib,
        "null_diagnostics": diagnostics,
        "maximum_toa_adjustment_error_microseconds": max(application_errors),
        "maximum_uncentered_toa_residual_target_error_microseconds": max(
            residual_target_errors
        ),
        "audit_comparisons": audit_comparisons,
        "warnings": warnings,
        "ledger_verification": ledger_verification,
        "scorecard": scorecard,
        "sealed_evaluation_cases_executed": 0,
        "observed_residual_global_search_executed": False,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    summary_path = data_root / "run_records/pilot1/benchmark50-r1-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    summary["external_record"] = {
        "logical_path": logical_path(summary_path, data_root),
        "sha256": hash_file(summary_path, "sha256"),
        "bytes": summary_path.stat().st_size,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot1-benchmark")
    parser.add_argument("command", choices=("plan", "verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "plan":
        result = benchmark50_plan(load_yaml(repository_root() / "config/pilot1.yaml"))
    elif args.command == "verify-freeze":
        result = verify_execution_freeze()
    else:
        data_root = configured_data_root(args.data_root)
        require_initialized_data_root(data_root)
        result = run_benchmark50(data_root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result.get("status", "pass") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
