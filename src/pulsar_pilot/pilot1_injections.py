from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import time
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np

from .c1 import generate_circular_delay_us
from .c1r1 import _joint_downhill_fit, _joint_full_covariance_fit, wrapped_phase_difference
from .c3 import extract_annual_correlation_diagnostic
from .config import load_pilot_config, load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _load_release, _peak_rss_gib, _synthetic_toas
from .pilot1_runtime import (
    ResumableArtifactLedger,
    build_pilot1_case_inventory,
    build_search_frequency_grid,
    generate_covariance_null,
    prepare_covariance_gls_scanner,
)
from .provenance import hash_file, logical_path

INJECTION_ID = "pilot1-injection-calibration-v0.1"
FREEZE_PATH = "protocol/PILOT1_INJECTION_FREEZE_v0.1.json"
THRESHOLD_LOCK_PATH = "protocol/PILOT1_THRESHOLD_LOCK_v0.1.json"
ASTROMETRIC_PARAMETERS = ("PX", "ELONG", "ELAT", "PMELONG", "PMELAT")


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_injection_order(plan: dict[str, Any]) -> list[dict[str, Any]]:
    inventory = build_pilot1_case_inventory(plan)
    audit_ids = set(inventory["independent_audit_case_ids"])
    order = [
        {**case, "full_covariance_audit": case["case_id"] in audit_ids}
        for case in inventory["injection_cases"]
    ]
    if len(order) != 284 or sum(case["full_covariance_audit"] for case in order) != 29:
        raise RuntimeError("Frozen injection inventory must contain 284 cases and 29 audits")
    if len({case["case_id"] for case in order}) != len(order):
        raise RuntimeError("Injection case IDs are not unique")
    return order


def injection_plan(plan: dict[str, Any], threshold_lock: dict[str, Any]) -> dict[str, Any]:
    order = build_injection_order(plan)
    return {
        "schema_version": 1,
        "injection_id": INJECTION_ID,
        "execution_authorized": False,
        "case_count": len(order),
        "full_covariance_audit_count": sum(case["full_covariance_audit"] for case in order),
        "case_order_sha256": _canonical_hash(order),
        "locked_threshold_delta_chi2": float(threshold_lock["value_delta_chi2"]),
        "frequency_recovery_tolerance": "one_independent_fourier_bin_inverse_span",
        "astrometric_parameters": list(ASTROMETRIC_PARAMETERS),
        "ordinary_absorption_measurement": (
            "one_minus_exact_frequency_covariance_gls_postfit_amplitude_fraction_clipped_0_1"
        ),
        "observed_residual_search_authorized": False,
    }


def verify_injection_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    threshold_path = root / THRESHOLD_LOCK_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    threshold_lock = json.loads(threshold_path.read_text(encoding="utf-8"))
    plan = injection_plan(load_yaml(root / "config/pilot1.yaml"), threshold_lock)
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_injection_calibration":
        failures.append("Injection freeze status is invalid")
    if freeze.get("authorization") != "exact_284_injections_and_29_audits_only":
        failures.append("Authorization is not limited to the frozen injection matrix")
    if freeze.get("case_order_sha256") != plan["case_order_sha256"]:
        failures.append("Injection case order mismatch")
    if freeze.get("observed_residual_search_authorized") is not False:
        failures.append("Observed-residual search must remain unauthorized")
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
    }


def detection_surface(records: list[dict[str, Any]]) -> dict[str, Any]:
    main = [record for record in records if record["case"]["family"] == "main"]
    periods = sorted({float(record["case"]["period_days"]) for record in main})
    amplitudes = sorted({float(record["case"]["amplitude_microseconds"]) for record in main})
    by_period: dict[str, Any] = {}
    monotonic_count = 0
    bracketed_count = 0
    for period in periods:
        fractions: list[float] = []
        cells: list[dict[str, Any]] = []
        for amplitude in amplitudes:
            cases = [
                record
                for record in main
                if float(record["case"]["period_days"]) == period
                and float(record["case"]["amplitude_microseconds"]) == amplitude
            ]
            fraction = sum(bool(record["triggered"]) for record in cases) / len(cases)
            fractions.append(fraction)
            cells.append({"amplitude_microseconds": amplitude, "cases": len(cases), "fraction": fraction})
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
        }
    return {
        "periods": by_period,
        "periods_with_monotonic_detection_fraction": monotonic_count,
        "periods_with_bracketed_50_and_90_percent_sensitivity": bracketed_count,
    }


def bracketed_crossing_amplitude(cells: list[dict[str, Any]], target: float) -> float | None:
    ordered = sorted(cells, key=lambda cell: float(cell["amplitude_microseconds"]))
    fractions = [float(cell["fraction"]) for cell in ordered]
    if min(fractions) > target or max(fractions) < target:
        return None
    for index, cell in enumerate(ordered):
        fraction = float(cell["fraction"])
        amplitude = float(cell["amplitude_microseconds"])
        if fraction == target:
            return amplitude
        if fraction > target and index > 0:
            prior = ordered[index - 1]
            low_fraction = float(prior["fraction"])
            low_amplitude = float(prior["amplitude_microseconds"])
            if fraction == low_fraction:
                return amplitude
            weight = (target - low_fraction) / (fraction - low_fraction)
            return low_amplitude + weight * (amplitude - low_amplitude)
    return None


def projected_mass_moon_masses(
    timing_amplitude_microseconds: float, period_days: float, pulsar_mass_solar: float
) -> float:
    gravitational_constant = 6.67430e-11
    speed_of_light = 299792458.0
    solar_mass_kg = 1.98847e30
    moon_mass_kg = 7.342e22
    pulsar_mass = pulsar_mass_solar * solar_mass_kg
    period_seconds = period_days * 86400.0
    semi_major_axis = (
        gravitational_constant * pulsar_mass * period_seconds**2 / (4.0 * math.pi**2)
    ) ** (1.0 / 3.0)
    projected_planet_mass = (
        timing_amplitude_microseconds * 1e-6 * speed_of_light * pulsar_mass / semi_major_axis
    )
    return projected_planet_mass / moon_mass_kg


def _verify_prior_result(data_root: Path, record: dict[str, Any], label: str) -> None:
    path = data_root / record["logical_path"]
    if not path.is_file() or path.stat().st_size != int(record["bytes"]):
        raise RuntimeError(f"{label} record is missing or has the wrong size")
    if hash_file(path, "sha256") != record["sha256"]:
        raise RuntimeError(f"{label} record hash mismatch")


def run_injections(data_root: Path) -> dict[str, Any]:
    freeze_verification = verify_injection_freeze()
    if freeze_verification["status"] != "pass":
        raise RuntimeError(f"Pilot 1 injection freeze failed: {freeze_verification}")
    root = repository_root()
    freeze = json.loads((root / FREEZE_PATH).read_text(encoding="utf-8"))
    plan = load_yaml(root / "config/pilot1.yaml")
    config = load_pilot_config(root / "config/target.yaml")
    threshold = float(freeze["locked_threshold_delta_chi2"])
    for label, source in freeze["prior_result_records"].items():
        _verify_prior_result(data_root, source, label)
    order = build_injection_order(plan)

    log_path = data_root / "run_records/pilot1/injection-calibration-v0.1.log"
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
    from pint.residuals import WidebandTOAResiduals

    setup_start = time.perf_counter()
    fitter = WidebandTOAFitter(release_toas, release_model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(release_toas.table["tdbld"].data, dtype=float)
    frequencies, _grid = build_search_frequency_grid(
        times,
        float(plan["candidate_eligibility"]["search_period_minimum_days"]),
        float(plan["candidate_eligibility"]["search_period_maximum_days"]),
    )
    epoch = float(plan["injections"]["reference_epoch_mjd_tdb"])
    scanner = prepare_covariance_gls_scanner(covariance, design, times, frequencies, epoch)
    exact_scanners = {
        float(period): prepare_covariance_gls_scanner(
            covariance, design, times, np.asarray([1.0 / float(period)]), epoch
        )
        for period in sorted({float(case["period_days"]) for case in order})
    }
    setup_seconds = time.perf_counter() - setup_start

    output_root = data_root / "derived/pilot1/injection-calibration-v0.1"
    output_root.mkdir(parents=True, exist_ok=True)
    implementation_sha = hash_file(root / "src/pulsar_pilot/pilot1_injections.py", "sha256")
    execution_binding_sha = hashlib.sha256(
        f"{implementation_sha}:{freeze_verification['freeze_sha256']}".encode()
    ).hexdigest()
    inventory_sha = build_pilot1_case_inventory(plan)["inventory_sha256"]
    ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/injection-calibration-v0.1-ledger.json",
        inventory_sha,
        execution_binding_sha,
    )
    prior_state = ledger.load()
    records: list[dict[str, Any]] = []
    factor = scanner.covariance_cholesky
    count = len(release_toas)
    independent_bin = 1.0 / float(np.ptp(times))
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
        requested[:count] += signal_us * 1e-6
        scan_start = time.perf_counter()
        scan = scanner.scan(requested)
        scan_seconds = time.perf_counter() - scan_start
        synthetic, application = _synthetic_toas(release_toas, release_model, requested)

        ordinary_start = time.perf_counter()
        ordinary = WidebandDownhillFitter(synthetic, copy.deepcopy(release_model))
        ordinary_returned = bool(ordinary.fit_toas(maxiter=config.max_fit_iterations))
        ordinary_residuals = WidebandTOAResiduals(synthetic, ordinary.model)
        ordinary_seconds = time.perf_counter() - ordinary_start
        exact_postfit = exact_scanners[float(case["period_days"])].scan(
            ordinary_residuals.calc_wideband_resids()
        )
        postfit_amplitude = float(exact_postfit["amplitude_us"])
        absorption = float(
            np.clip(1.0 - postfit_amplitude / float(case["amplitude_microseconds"]), 0.0, 1.0)
        )

        joint_start = time.perf_counter()
        joint = _joint_downhill_fit(
            synthetic,
            release_model,
            1.0 / float(case["period_days"]),
            epoch,
            config.max_fit_iterations,
        )
        joint_seconds = time.perf_counter() - joint_start
        amplitude_bias_fraction = abs(
            float(joint["amplitude_us"]) - float(case["amplitude_microseconds"])
        ) / float(case["amplitude_microseconds"])
        phase_error = abs(
            wrapped_phase_difference(float(joint["phase_radians"]), float(case["phase_radians"]))
        )
        statistic = float(scan["trigger_statistic"])
        injected_frequency = 1.0 / float(case["period_days"])
        record: dict[str, Any] = {
            "schema_version": 1,
            "injection_id": INJECTION_ID,
            "execution_binding_sha256": execution_binding_sha,
            "case": case,
            "locked_threshold_delta_chi2": threshold,
            "triggered": statistic > threshold,
            "frequency_recovered": abs(float(scan["peak_frequency_per_day"]) - injected_frequency)
            <= independent_bin,
            "frequency_recovery_absolute_error_per_day": abs(
                float(scan["peak_frequency_per_day"]) - injected_frequency
            ),
            "frequency_recovery_tolerance_per_day": independent_bin,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
            "scan_wall_seconds": scan_seconds,
            "application": application,
            "ordinary_fit": {
                "returned_converged": ordinary_returned,
                "fitter_converged": bool(ordinary.converged),
                "chi2": float(ordinary_residuals.chi2),
                "wall_seconds": ordinary_seconds,
                "exact_frequency_postfit_amplitude_microseconds": postfit_amplitude,
                "absorption_fraction": absorption,
            },
            "joint_fit": {
                key: value for key, value in joint.items() if key not in {"fitter", "model", "residuals"}
            },
            "amplitude_bias_fraction": amplitude_bias_fraction,
            "phase_error_radians": phase_error,
        }
        record["joint_fit"]["wall_seconds"] = joint_seconds
        record["joint_fit"]["delta_chi2_from_ordinary"] = float(
            ordinary_residuals.chi2 - float(joint["chi2"])
        )
        if case["family"] == "annual":
            record["astrometric_correlation"] = extract_annual_correlation_diagnostic(
                joint["fitter"], list(ASTROMETRIC_PARAMETERS)
            )
        if case["full_covariance_audit"]:
            audit_start = time.perf_counter()
            audit = _joint_full_covariance_fit(
                synthetic,
                release_model,
                injected_frequency,
                epoch,
                config.max_fit_iterations,
            )
            record["full_covariance_audit"] = {
                key: value for key, value in audit.items() if key not in {"fitter", "model", "residuals"}
            }
            record["full_covariance_audit"]["wall_seconds"] = time.perf_counter() - audit_start
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
        case_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        ledger.record(case["case_id"], case_path, data_root)
        records.append(record)
    injection_wall_seconds = time.perf_counter() - start

    correlation_limit = float(plan["candidate_eligibility"]["maximum_signal_astrometry_correlation"])
    absorption_limit = float(plan["candidate_eligibility"]["maximum_ordinary_model_absorption_fraction"])
    annual_records = [record for record in records if record["case"]["family"] == "annual"]
    annual_map: dict[str, Any] = {}
    annual_eligible: dict[float, bool] = {}
    for period in sorted({float(record["case"]["period_days"]) for record in annual_records}):
        cases = [record for record in annual_records if float(record["case"]["period_days"]) == period]
        maximum_correlation = max(
            float(record["astrometric_correlation"]["maximum_absolute_correlation"])
            for record in cases
        )
        maximum_absorption = max(float(record["ordinary_fit"]["absorption_fraction"]) for record in cases)
        eligible = maximum_correlation < correlation_limit and maximum_absorption < absorption_limit
        annual_eligible[period] = eligible
        annual_map[str(period)] = {
            "maximum_absolute_correlation": maximum_correlation,
            "maximum_absorption_fraction": maximum_absorption,
            "eligible": eligible,
            "case_count": len(cases),
        }

    def is_eligible(record: dict[str, Any]) -> bool:
        case = record["case"]
        return case["family"] != "annual" or annual_eligible[float(case["period_days"])]

    eligible_records = [record for record in records if is_eligible(record)]
    detected_eligible = [record for record in eligible_records if record["triggered"]]
    strong = [
        record
        for record in eligible_records
        if float(record["case"]["amplitude_microseconds"])
        == float(plan["promotion_benchmarks"]["strong_control_amplitude_microseconds"])
    ]
    strong_recovery_rate = sum(record["triggered"] for record in strong) / len(strong)
    frequency_recovery_rate = (
        sum(record["frequency_recovered"] for record in detected_eligible) / len(detected_eligible)
    )
    median_bias = float(np.median([record["amplitude_bias_fraction"] for record in detected_eligible]))
    phase_p90 = float(np.quantile([record["phase_error_radians"] for record in detected_eligible], 0.9))
    surface = detection_surface(records)
    cells_100 = surface["periods"]["100.0"]["cells"]
    sensitivity_100_us = bracketed_crossing_amplitude(cells_100, 0.9)
    reference = float(plan["promotion_benchmarks"]["published_100_day_reference_moon_masses"])
    sensitivity_mass = (
        projected_mass_moon_masses(
            sensitivity_100_us,
            100.0,
            float(plan["promotion_benchmarks"]["projected_mass_pulsar_mass_solar"]),
        )
        if sensitivity_100_us is not None
        else None
    )
    reference_ratio = sensitivity_mass / reference if sensitivity_mass is not None else None
    audit_limits = plan["independent_audit"]
    audit_comparisons = [record["audit_comparison"] for record in records if "audit_comparison" in record]
    audit_failures = sum(
        float(item["amplitude_difference_microseconds"])
        > float(audit_limits["amplitude_difference_maximum_microseconds"])
        or float(item["phase_difference_radians"])
        > float(audit_limits["phase_difference_maximum_radians"])
        or float(item["chi2_difference"]) > float(audit_limits["chi2_difference_maximum"])
        for item in audit_comparisons
    )
    annual_violations = sum(
        annual_eligible[float(record["case"]["period_days"])]
        and (
            float(record["astrometric_correlation"]["maximum_absolute_correlation"])
            >= correlation_limit
            or float(record["ordinary_fit"]["absorption_fraction"]) >= absorption_limit
        )
        for record in annual_records
    )
    application_errors = [
        float(record["application"]["toa_adjustment_maximum_absolute_error_microseconds"])
        for record in records
    ]
    sanitized_log = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    warnings = classify_warning_lines(sanitized_log)
    ledger_verification = ledger.verify(data_root)
    peak_memory_gib = _peak_rss_gib()
    data_root_gib = _directory_size_gib(data_root)
    limits = plan["promotion_benchmarks"]
    resources = plan["resource_caps"]
    prior_wall_seconds = sum(float(value) for value in freeze["prior_wall_seconds"].values())
    total_wall_hours = (prior_wall_seconds + setup_seconds + injection_wall_seconds) / 3600.0
    criteria = {
        "exactly_284_injections": len(records) == 284,
        "exactly_29_full_covariance_audits": len(audit_comparisons) == 29,
        "toa_application_accuracy": max(application_errors)
        <= float(plan["injections"]["maximum_application_error_microseconds"]),
        "ordinary_fits_converged": all(
            record["ordinary_fit"]["returned_converged"]
            and record["ordinary_fit"]["fitter_converged"]
            for record in records
        ),
        "joint_fits_converged": all(
            record["joint_fit"]["returned_converged"]
            and record["joint_fit"]["fitter_converged"]
            for record in records
        ),
        "strong_control_recovery": strong_recovery_rate
        >= float(limits["strong_control_recovery_rate_minimum"]),
        "frequency_recovery": frequency_recovery_rate
        >= float(limits["injected_frequency_recovery_rate_minimum"]),
        "amplitude_bias": median_bias <= float(limits["median_amplitude_bias_fraction_maximum"]),
        "phase_error": phase_p90 <= float(limits["phase_error_p90_maximum_radians"]),
        "monotonic_detection_fraction": surface["periods_with_monotonic_detection_fraction"]
        >= int(limits["minimum_periods_with_monotonic_detection_fraction"]),
        "sensitivity_bracketing": surface[
            "periods_with_bracketed_50_and_90_percent_sensitivity"
        ]
        >= int(limits["minimum_periods_with_bracketed_50_and_90_percent_sensitivity"]),
        "annual_eligibility_mask": annual_violations
        <= int(limits["annual_eligibility_violations_maximum"]),
        "independent_covariance_audit": audit_failures
        <= int(limits["independent_audit_failures_maximum"]),
        "published_reference_reconciliation": reference_ratio is not None
        and float(limits["published_100_day_sensitivity_ratio_minimum"])
        <= reference_ratio
        <= float(limits["published_100_day_sensitivity_ratio_maximum"]),
        "warning_hygiene": warnings["status"] == "pass",
        "artifact_ledger_verified": ledger_verification["status"] == "pass"
        and ledger_verification["completed_cases"] == 284,
        "runtime_under_cap": total_wall_hours <= float(resources["macbook_total_wall_hours"]),
        "peak_memory_under_cap": peak_memory_gib <= float(resources["peak_memory_gib"]),
        "storage_under_cap": data_root_gib <= float(resources["complete_data_root_gib"]),
        "observed_residual_search_not_executed": True,
    }
    scorecard = {
        "overall": "PASS" if all(criteria.values()) else "FAIL",
        "passed": sum(criteria.values()),
        "total": len(criteria),
        "criteria": {key: "PASS" if value else "FAIL" for key, value in criteria.items()},
    }
    summary = {
        "schema_version": 1,
        "injection_id": INJECTION_ID,
        "status": "pass" if scorecard["overall"] == "PASS" else "fail",
        "freeze": freeze_verification,
        "execution_binding_sha256": execution_binding_sha,
        "case_count": len(records),
        "full_covariance_audit_count": len(audit_comparisons),
        "locked_threshold_delta_chi2": threshold,
        "frequency_recovery_tolerance_per_day": independent_bin,
        "metrics": {
            "eligible_injection_count": len(eligible_records),
            "detected_eligible_injection_count": len(detected_eligible),
            "strong_control_count": len(strong),
            "strong_control_recovery_rate": strong_recovery_rate,
            "injected_frequency_recovery_rate": frequency_recovery_rate,
            "median_amplitude_bias_fraction": median_bias,
            "phase_error_p90_radians": phase_p90,
            "periods_with_monotonic_detection_fraction": surface[
                "periods_with_monotonic_detection_fraction"
            ],
            "periods_with_bracketed_50_and_90_percent_sensitivity": surface[
                "periods_with_bracketed_50_and_90_percent_sensitivity"
            ],
            "annual_eligibility_violations": annual_violations,
            "independent_audit_failures": audit_failures,
            "maximum_toa_adjustment_error_microseconds": max(application_errors),
            "published_100_day_sensitivity_microseconds": sensitivity_100_us,
            "published_100_day_sensitivity_moon_masses": sensitivity_mass,
            "published_100_day_sensitivity_ratio": reference_ratio,
        },
        "annual_identifiability_map": annual_map,
        "detection_surface": surface,
        "audit_comparisons": audit_comparisons,
        "setup_wall_seconds": setup_seconds,
        "injection_wall_seconds": injection_wall_seconds,
        "total_calibration_wall_hours": total_wall_hours,
        "peak_memory_gib": peak_memory_gib,
        "complete_data_root_gib": data_root_gib,
        "warnings": warnings,
        "ledger_verification": ledger_verification,
        "scorecard": scorecard,
        "observed_residual_global_search_executed": False,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    summary_path = data_root / "run_records/pilot1/injection-calibration-v0.1-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["external_record"] = {
        "logical_path": logical_path(summary_path, data_root),
        "sha256": hash_file(summary_path, "sha256"),
        "bytes": summary_path.stat().st_size,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot1-injections")
    parser.add_argument("command", choices=("plan", "verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = repository_root()
    if args.command == "plan":
        result = injection_plan(
            load_yaml(root / "config/pilot1.yaml"),
            json.loads((root / THRESHOLD_LOCK_PATH).read_text(encoding="utf-8")),
        )
    elif args.command == "verify-freeze":
        result = verify_injection_freeze()
    else:
        data_root = configured_data_root(args.data_root)
        require_initialized_data_root(data_root)
        result = run_injections(data_root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result.get("status", "pass") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
