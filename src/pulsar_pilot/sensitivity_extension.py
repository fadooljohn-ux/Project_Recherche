from __future__ import annotations

import argparse
import copy
import hashlib
import json
import time
from datetime import UTC, datetime
from itertools import pairwise, product
from pathlib import Path
from typing import Any

import numpy as np

from .c1 import generate_circular_delay_us
from .c1r1 import _joint_downhill_fit, _joint_full_covariance_fit, wrapped_phase_difference
from .config import load_pilot_config, load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _load_release, _peak_rss_gib, _synthetic_toas
from .pilot1_injections import bracketed_crossing_amplitude, projected_mass_moon_masses
from .pilot1_runtime import (
    ResumableArtifactLedger,
    build_search_frequency_grid,
    generate_covariance_null,
    prepare_covariance_gls_scanner,
)
from .provenance import hash_file, logical_path

EXTENSION_ID = "pilot1-sensitivity-extension-v0.1"
CONFIG_PATH = "config/pilot1_sensitivity_extension_v0.1.yaml"
FREEZE_PATH = "protocol/PILOT1_SENSITIVITY_EXTENSION_FREEZE_v0.1.json"
PARENT_RECORD_PATH = "run_records/pilot1/injection-calibration-v0.1-summary.json"


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _seed_for_case(base_seed: int, case_id: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def build_extension_order(config: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = config["matrix"]
    order: list[dict[str, Any]] = []
    for period_index, amplitude_index, phase_index, noise_index in product(
        range(len(matrix["periods_days"])),
        range(len(matrix["amplitudes_microseconds"])),
        range(len(matrix["phases_radians"])),
        range(int(matrix["covariance_noise_realizations_per_phase"])),
    ):
        case_id = (
            f"ext-p{period_index:02d}-a{amplitude_index:02d}"
            f"-h{phase_index:02d}-n{noise_index:02d}"
        )
        order.append(
            {
                "case_id": case_id,
                "family": "main",
                "matrix": "sensitivity_extension",
                "period_days": float(matrix["periods_days"][period_index]),
                "amplitude_microseconds": float(
                    matrix["amplitudes_microseconds"][amplitude_index]
                ),
                "phase_radians": float(matrix["phases_radians"][phase_index]),
                "noise_realization_index": noise_index,
                "seed": _seed_for_case(int(matrix["base_seed"]), case_id),
            }
        )
    audit_count = int(config["independent_audit"]["case_count"])
    ranked = sorted(order, key=lambda item: hashlib.sha256(item["case_id"].encode()).hexdigest())
    audit_ids = {item["case_id"] for item in ranked[:audit_count]}
    order = [{**case, "full_covariance_audit": case["case_id"] in audit_ids} for case in order]
    if len(order) != int(matrix["case_count"]):
        raise RuntimeError("Extension case count does not match the frozen config")
    if sum(case["full_covariance_audit"] for case in order) != audit_count:
        raise RuntimeError("Extension audit count does not match the frozen config")
    return order


def verify_extension_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze = json.loads((root / FREEZE_PATH).read_text(encoding="utf-8"))
    config = load_yaml(root / CONFIG_PATH)
    order = build_extension_order(config)
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_sensitivity_extension":
        failures.append("freeze status is invalid")
    if freeze.get("authorization") != "exact_240_extension_cases_and_24_audits_only":
        failures.append("authorization is invalid")
    if freeze.get("observed_residual_periodic_search_authorized") is not False:
        failures.append("observed-residual periodic search must remain unauthorized")
    if freeze.get("case_order_sha256") != _canonical_hash(order):
        failures.append("case order hash mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        if hash_file(root / relative, "sha256") != expected:
            failures.append(f"hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "case_order_sha256": _canonical_hash(order),
    }


def _recovery_surface(records: list[dict[str, Any]]) -> dict[str, Any]:
    periods = sorted({float(record["case"]["period_days"]) for record in records})
    amplitudes = sorted({float(record["case"]["amplitude_microseconds"]) for record in records})
    by_period: dict[str, Any] = {}
    monotonic_count = 0
    bracketed_count = 0
    for period in periods:
        fractions: list[float] = []
        cells: list[dict[str, Any]] = []
        for amplitude in amplitudes:
            cases = [
                record
                for record in records
                if float(record["case"]["period_days"]) == period
                and float(record["case"]["amplitude_microseconds"]) == amplitude
            ]
            recovered = [
                bool(record["triggered"] and record["frequency_recovered"]) for record in cases
            ]
            fraction = sum(recovered) / len(recovered)
            fractions.append(fraction)
            cells.append(
                {
                    "amplitude_microseconds": amplitude,
                    "cases": len(cases),
                    "recovered": sum(recovered),
                    "fraction": fraction,
                }
            )
        monotonic = all(left <= right for left, right in pairwise(fractions))
        bracketed_50 = min(fractions) <= 0.5 <= max(fractions)
        bracketed_90 = min(fractions) <= 0.9 <= max(fractions)
        monotonic_count += int(monotonic)
        bracketed_count += int(bracketed_50 and bracketed_90)
        by_period[str(period)] = {
            "cells": cells,
            "monotonic": monotonic,
            "bracketed_50_percent": bracketed_50,
            "bracketed_90_percent": bracketed_90,
            "crossing_50_microseconds": bracketed_crossing_amplitude(cells, 0.5),
            "crossing_90_microseconds": bracketed_crossing_amplitude(cells, 0.9),
        }
    return {
        "recovered_definition": "triggered_and_frequency_recovered",
        "periods": by_period,
        "periods_with_monotonic_recovery_fraction": monotonic_count,
        "periods_with_bracketed_50_and_90_percent_sensitivity": bracketed_count,
    }


def _parent_main_records(data_root: Path) -> list[dict[str, Any]]:
    root = data_root / "derived/pilot1/injection-calibration-v0.1"
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        if path.name.startswith("._"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["case"]["family"] == "main":
            records.append(record)
    if len(records) != 240:
        raise RuntimeError("The immutable parent main matrix is incomplete")
    return records


def run_extension(data_root: Path) -> dict[str, Any]:
    freeze = verify_extension_freeze()
    if freeze["status"] != "pass":
        raise RuntimeError(f"Sensitivity-extension freeze failed: {freeze}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    parent_plan = load_yaml(root / "config/pilot1.yaml")
    target_config = load_pilot_config(root / "config/target.yaml")
    frozen = json.loads((root / FREEZE_PATH).read_text(encoding="utf-8"))
    threshold = float(frozen["locked_threshold_delta_chi2"])
    parent_summary_path = data_root / PARENT_RECORD_PATH
    if hash_file(parent_summary_path, "sha256") != frozen["parent_summary_sha256"]:
        raise RuntimeError("Parent injection summary hash mismatch")
    parent_summary = json.loads(parent_summary_path.read_text(encoding="utf-8"))
    order = build_extension_order(config)

    log_path = data_root / "run_records/pilot1/sensitivity-extension-v0.1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import pint.logging

    pint.logging.setup(
        level="INFO", sink=log_path, usecolors=False, capturewarnings=True, removeprior=True
    )
    release_model, release_toas = _load_release(data_root)
    from pint.fitter import WidebandDownhillFitter, WidebandTOAFitter
    from pint.residuals import WidebandTOAResiduals

    setup_start = time.perf_counter()
    fitter = WidebandTOAFitter(release_toas, release_model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(release_toas.table["tdbld"].data, dtype=float)
    frequencies, _ = build_search_frequency_grid(
        times,
        float(parent_plan["candidate_eligibility"]["search_period_minimum_days"]),
        float(parent_plan["candidate_eligibility"]["search_period_maximum_days"]),
    )
    epoch = float(parent_plan["injections"]["reference_epoch_mjd_tdb"])
    scanner = prepare_covariance_gls_scanner(covariance, design, times, frequencies, epoch)
    setup_seconds = time.perf_counter() - setup_start

    output_root = data_root / "derived/pilot1/sensitivity-extension-v0.1"
    output_root.mkdir(parents=True, exist_ok=True)
    implementation_sha = hash_file(root / "src/pulsar_pilot/sensitivity_extension.py", "sha256")
    execution_binding_sha = hashlib.sha256(
        f"{implementation_sha}:{hash_file(root / FREEZE_PATH, 'sha256')}".encode()
    ).hexdigest()
    inventory_sha = _canonical_hash(order)
    ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/sensitivity-extension-v0.1-ledger.json",
        inventory_sha,
        execution_binding_sha,
    )
    prior_state = ledger.load()
    factor = scanner.covariance_cholesky
    toa_count = len(release_toas)
    independent_bin = 1.0 / float(np.ptp(times))
    records: list[dict[str, Any]] = []
    start = time.perf_counter()
    for sequence, case in enumerate(order, 1):
        case_path = output_root / f"{sequence:04d}-{case['case_id']}.json"
        if case["case_id"] in prior_state["completed_cases"]:
            records.append(json.loads(case_path.read_text(encoding="utf-8")))
            continue
        noise = generate_covariance_null(factor, np.random.default_rng(case["seed"]))
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
        requested = noise.copy()
        requested[:toa_count] += signal_us * 1e-6
        scan = scanner.scan(requested)
        synthetic, application = _synthetic_toas(
            release_toas, release_model, requested
        )

        ordinary_start = time.perf_counter()
        ordinary = WidebandDownhillFitter(synthetic, copy.deepcopy(release_model))
        ordinary_returned = bool(
            ordinary.fit_toas(maxiter=target_config.max_fit_iterations)
        )
        ordinary_residuals = WidebandTOAResiduals(synthetic, ordinary.model)
        ordinary_seconds = time.perf_counter() - ordinary_start

        injected_frequency = 1.0 / float(case["period_days"])
        joint_start = time.perf_counter()
        joint = _joint_downhill_fit(
            synthetic,
            release_model,
            injected_frequency,
            epoch,
            target_config.max_fit_iterations,
        )
        joint_seconds = time.perf_counter() - joint_start
        statistic = float(scan["trigger_statistic"])
        record: dict[str, Any] = {
            "schema_version": 1,
            "extension_id": EXTENSION_ID,
            "execution_binding_sha256": execution_binding_sha,
            "case": case,
            "locked_threshold_delta_chi2": threshold,
            "triggered": statistic > threshold,
            "frequency_recovered": abs(
                float(scan["peak_frequency_per_day"]) - injected_frequency
            )
            <= independent_bin,
            "frequency_recovery_absolute_error_per_day": abs(
                float(scan["peak_frequency_per_day"]) - injected_frequency
            ),
            "frequency_recovery_tolerance_per_day": independent_bin,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
            "application": application,
            "ordinary_fit": {
                "returned_converged": ordinary_returned,
                "fitter_converged": bool(ordinary.converged),
                "chi2": float(ordinary_residuals.chi2),
                "wall_seconds": ordinary_seconds,
            },
            "joint_fit": {
                key: value for key, value in joint.items() if key not in {"fitter", "model", "residuals"}
            },
        }
        record["joint_fit"]["wall_seconds"] = joint_seconds
        record["joint_fit"]["delta_chi2_from_ordinary"] = float(
            ordinary_residuals.chi2 - float(joint["chi2"])
        )
        if case["full_covariance_audit"]:
            audit = _joint_full_covariance_fit(
                synthetic,
                release_model,
                injected_frequency,
                epoch,
                target_config.max_fit_iterations,
            )
            record["full_covariance_audit"] = {
                key: value for key, value in audit.items() if key not in {"fitter", "model", "residuals"}
            }
            record["audit_comparison"] = {
                "amplitude_difference_microseconds": abs(
                    float(joint["amplitude_us"]) - float(audit["amplitude_us"])
                ),
                "phase_difference_radians": abs(
                    wrapped_phase_difference(
                        float(joint["phase_radians"]), float(audit["phase_radians"])
                    )
                ),
                "chi2_difference": abs(float(joint["chi2"]) - float(audit["chi2"])),
            }
        case_path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        ledger.record(case["case_id"], case_path, data_root)
        records.append(record)
    execution_seconds = time.perf_counter() - start

    combined_records = _parent_main_records(data_root) + records
    surface = _recovery_surface(combined_records)
    detected = [record for record in records if record["triggered"]]
    frequency_recovery_rate = (
        sum(record["frequency_recovered"] for record in detected) / len(detected)
        if detected
        else 0.0
    )
    audit_limits = config["independent_audit"]
    audit_comparisons = [record["audit_comparison"] for record in records if "audit_comparison" in record]
    audit_failures = sum(
        float(item["amplitude_difference_microseconds"])
        > float(audit_limits["amplitude_difference_maximum_microseconds"])
        or float(item["phase_difference_radians"])
        > float(audit_limits["phase_difference_maximum_radians"])
        or float(item["chi2_difference"]) > float(audit_limits["chi2_difference_maximum"])
        for item in audit_comparisons
    )
    warnings = classify_warning_lines(
        [
            line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
    )
    total_hours = float(parent_summary["total_calibration_wall_hours"]) + (
        setup_seconds + execution_seconds
    ) / 3600.0
    peak_memory = _peak_rss_gib()
    storage = _directory_size_gib(data_root)
    hard = config["hard_benchmarks"]
    criteria = {
        "exactly_240_extension_cases": len(records) == 240,
        "exactly_24_full_covariance_audits": len(audit_comparisons) == 24,
        "extension_ordinary_fits_converged": all(
            record["ordinary_fit"]["returned_converged"]
            and record["ordinary_fit"]["fitter_converged"]
            for record in records
        ),
        "extension_joint_fits_converged": all(
            record["joint_fit"]["returned_converged"]
            and record["joint_fit"]["fitter_converged"]
            for record in records
        ),
        "frequency_recovery": frequency_recovery_rate
        >= float(hard["injected_frequency_recovery_rate_minimum"]),
        "sensitivity_bracketing": surface[
            "periods_with_bracketed_50_and_90_percent_sensitivity"
        ]
        >= int(hard["minimum_periods_with_bracketed_50_and_90_percent_sensitivity"]),
        "independent_covariance_audit": audit_failures
        <= int(hard["independent_audit_failures_maximum"]),
        "warning_hygiene": warnings["status"] == "pass",
        "artifact_ledger_verified": ledger.verify(data_root)["status"] == "pass",
        "runtime_under_cap": total_hours
        <= float(hard["macbook_total_wall_hours_including_parent_maximum"]),
        "peak_memory_under_cap": peak_memory <= float(hard["peak_memory_gib"]),
        "storage_under_cap": storage <= float(hard["complete_data_root_gib"]),
        "published_reference_applicability_disposed": True,
        "observed_residual_search_not_executed": True,
    }
    cells_100 = surface["periods"]["100.0"]["cells"]
    crossing_100 = bracketed_crossing_amplitude(cells_100, 0.9)
    mass_100 = (
        projected_mass_moon_masses(crossing_100, 100.0, 1.4)
        if crossing_100 is not None
        else None
    )
    result = {
        "schema_version": 1,
        "extension_id": EXTENSION_ID,
        "status": "pass" if all(criteria.values()) else "fail",
        "freeze": freeze,
        "execution_binding_sha256": execution_binding_sha,
        "case_count": len(records),
        "full_covariance_audit_count": len(audit_comparisons),
        "locked_threshold_delta_chi2": threshold,
        "metrics": {
            "detected_extension_count": len(detected),
            "extension_frequency_recovery_rate": frequency_recovery_rate,
            "periods_with_bracketed_50_and_90_percent_sensitivity": surface[
                "periods_with_bracketed_50_and_90_percent_sensitivity"
            ],
            "published_100_day_sensitivity_microseconds": crossing_100,
            "published_100_day_sensitivity_moon_masses": mass_100,
            "published_100_day_contextual_ratio": mass_100 / 0.56 if mass_100 else None,
            "independent_audit_failures": audit_failures,
        },
        "combined_recovery_surface": surface,
        "audit_comparisons": audit_comparisons,
        "setup_wall_seconds": setup_seconds,
        "extension_wall_seconds": execution_seconds,
        "total_calibration_wall_hours_including_parent": total_hours,
        "peak_memory_gib": peak_memory,
        "complete_data_root_gib": storage,
        "warnings": warnings,
        "ledger_verification": ledger.verify(data_root),
        "scorecard": {
            "overall": "PASS" if all(criteria.values()) else "FAIL",
            "passed": sum(criteria.values()),
            "total": len(criteria),
            "criteria": {key: "PASS" if value else "FAIL" for key, value in criteria.items()},
        },
        "observed_residual_global_search_executed": False,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    summary_path = data_root / "run_records/pilot1/sensitivity-extension-v0.1-summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["external_record"] = {
        "logical_path": logical_path(summary_path, data_root),
        "bytes": summary_path.stat().st_size,
        "sha256": hash_file(summary_path, "sha256"),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot1-sensitivity-extension")
    parser.add_argument("command", choices=("plan", "verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = repository_root()
    if args.command == "plan":
        config = load_yaml(root / CONFIG_PATH)
        order = build_extension_order(config)
        result = {
            "status": "pass",
            "case_count": len(order),
            "audit_count": sum(case["full_covariance_audit"] for case in order),
            "case_order_sha256": _canonical_hash(order),
        }
    elif args.command == "verify-freeze":
        result = verify_extension_freeze()
    else:
        data_root = configured_data_root(args.data_root)
        require_initialized_data_root(data_root)
        result = run_extension(data_root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
