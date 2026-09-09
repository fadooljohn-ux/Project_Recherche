from __future__ import annotations

import argparse
import copy
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .c1r1 import _joint_downhill_fit, _joint_full_covariance_fit, wrapped_phase_difference
from .config import load_pilot_config, load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _load_release, _peak_rss_gib
from .pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner
from .preunblinding_validation import build_deletion_units
from .provenance import hash_file

SEARCH_ID = "pilot1-one-shot-observed-residual-search-v0.1"
CONFIG_PATH = "config/pilot1_one_shot_search_v0.1.yaml"
FREEZE_PATH = "protocol/PILOT1_ONE_SHOT_SEARCH_FREEZE_v0.1.json"
PACKAGE_MANIFEST_PATH = "manifests/pilot1_one_shot_final_review_v0.1.sha256"
IMPLEMENTATION_PATH = "src/pulsar_pilot/one_shot_search.py"
FABLE_SIGNOFF_PATH = "protocol/FABLE_FINAL_PREEXECUTION_SIGNOFF_v0.1.json"
USER_AUTHORIZATION_PATH = "protocol/USER_ONE_SHOT_EXECUTION_AUTHORIZATION_v0.1.json"
CANDIDATE_SCHEMA_PATH = "protocol/PILOT1_ONE_SHOT_CANDIDATE_REPORT_SCHEMA_v0.1.json"


def _canonical_hash(value: Any) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_annual_mask(
    frequencies_per_day: np.ndarray, target_periods_days: list[float]
) -> dict[str, Any]:
    frequencies = np.asarray(frequencies_per_day, dtype=float)
    periods = 1.0 / frequencies
    indices: list[int] = []
    for target in target_periods_days:
        distance = np.abs(periods - float(target))
        minimum = float(np.min(distance))
        tied = np.flatnonzero(np.isclose(distance, minimum, rtol=0.0, atol=1e-15))
        indices.append(int(np.min(tied)))
    if len(set(indices)) != len(target_periods_days):
        raise RuntimeError("Annual mask targets map to overlapping grid cells")
    return {
        "target_periods_days": [float(value) for value in target_periods_days],
        "masked_grid_indices": indices,
        "masked_grid_frequencies_per_day": [float(frequencies[index]) for index in indices],
        "masked_grid_periods_days": [float(periods[index]) for index in indices],
        "selection_semantics": "nearest_period_cell_ties_to_lowest_index",
    }


def select_strongest_unmasked(
    all_delta_chi2: np.ndarray,
    frequencies_per_day: np.ndarray,
    masked_indices: list[int],
) -> dict[str, Any]:
    statistics = np.asarray(all_delta_chi2, dtype=float)
    frequencies = np.asarray(frequencies_per_day, dtype=float)
    if statistics.shape != frequencies.shape or not np.all(np.isfinite(statistics)):
        raise ValueError("Search statistics and frequencies must be finite and aligned")
    eligible = np.ones(len(statistics), dtype=bool)
    eligible[np.asarray(masked_indices, dtype=int)] = False
    if not np.any(eligible):
        raise ValueError("Annual mask removed the complete search grid")
    eligible_indices = np.flatnonzero(eligible)
    index = int(eligible_indices[np.argmax(statistics[eligible])])
    return {
        "index": index,
        "statistic": float(statistics[index]),
        "frequency_per_day": float(frequencies[index]),
        "period_days": float(1.0 / frequencies[index]),
    }


def build_one_shot_plan(
    config: dict[str, Any], times: np.ndarray, utc_days: np.ndarray
) -> dict[str, Any]:
    detector = config["detector"]
    frequencies, grid = build_search_frequency_grid(
        np.asarray(times, dtype=float),
        float(detector["period_minimum_days"]),
        float(detector["period_maximum_days"]),
        int(detector["frequency_oversampling"]),
    )
    mask = build_annual_mask(
        frequencies, list(config["annual_mask"]["ineligible_period_targets_days"])
    )
    deletion_units = build_deletion_units(np.asarray(utc_days, dtype=int))
    return {
        "schema_version": 1,
        "search_id": SEARCH_ID,
        "frequency_grid": grid,
        "frequency_grid_sha256": _canonical_hash(frequencies.tolist()),
        "annual_mask": mask,
        "annual_mask_sha256": _canonical_hash(mask),
        "deletion_units": len(deletion_units),
        "deletion_unit_inventory_sha256": _canonical_hash(deletion_units),
        "locked_threshold_delta_chi2": float(detector["locked_threshold_delta_chi2"]),
        "observed_residual_access_authorized": False,
        "observed_periodic_search_authorized": False,
    }


def _verify_external(data_root: Path, freeze: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for relative, expected in freeze.get("external_prerequisites", {}).items():
        path = data_root / relative
        if not path.is_file() or path.stat().st_size != int(expected["bytes"]):
            failures.append(f"missing or wrong size: {relative}")
        elif hash_file(path, "sha256") != expected["sha256"]:
            failures.append(f"hash mismatch: {relative}")
    return {"status": "pass" if not failures else "fail", "failures": failures}


def _verify_manifest(root: Path, manifest_path: Path) -> list[str]:
    failures: list[str] = []
    for line_number, line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        try:
            expected, relative = line.split("  ", 1)
        except ValueError:
            failures.append(f"invalid manifest line: {line_number}")
            continue
        path = (root / relative).resolve()
        if root.resolve() not in path.parents:
            failures.append(f"manifest path escapes repository: {relative}")
        elif not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"manifest hash mismatch: {relative}")
    return failures


def verify_package(data_root: Path) -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    config = load_yaml(root / CONFIG_PATH)
    failures: list[str] = []
    if freeze.get("status") != "frozen_for_final_fable_review":
        failures.append("one-shot freeze status is invalid")
    if freeze.get("authorization") != "preparation_only_execution_locked":
        failures.append("one-shot freeze authorization is invalid")
    for field in (
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "threshold_retuning_authorized",
        "rerun_authorized",
        "deletion_checks_as_hard_vetoes",
        "robust_refit_included",
    ):
        if freeze.get(field) is not False:
            failures.append(f"{field} must be false")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        path = root / relative
        if not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"hash mismatch: {relative}")
    manifest_path = root / PACKAGE_MANIFEST_PATH
    if not manifest_path.is_file() or hash_file(manifest_path, "sha256") != freeze.get(
        "package_manifest_sha256"
    ):
        failures.append("package manifest mismatch")
    else:
        failures.extend(_verify_manifest(root, manifest_path))

    model, toas = _load_release(data_root)
    del model
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    utc_days = np.floor(np.asarray(toas.table["mjd_float"], dtype=float)).astype(int)
    plan = build_one_shot_plan(config, times, utc_days)
    if freeze.get("plan_sha256") != _canonical_hash(plan):
        failures.append("one-shot plan hash mismatch")
    if plan["deletion_unit_inventory_sha256"] != config["deletion_diagnostics"][
        "inventory_sha256"
    ]:
        failures.append("deletion-unit inventory mismatch")
    if len(plan["annual_mask"]["masked_grid_indices"]) != int(
        config["annual_mask"]["expected_masked_grid_cells"]
    ):
        failures.append("annual-mask cell count mismatch")
    external = _verify_external(data_root, freeze)
    if external["status"] != "pass":
        failures.extend(external["failures"])
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_sha256": hash_file(freeze_path, "sha256"),
        "package_manifest_sha256": hash_file(manifest_path, "sha256"),
        "implementation_sha256": hash_file(root / IMPLEMENTATION_PATH, "sha256"),
        "candidate_schema_sha256": hash_file(root / CANDIDATE_SCHEMA_PATH, "sha256"),
        "plan": plan,
        "external_prerequisites": external,
        "observed_residual_access_authorized": False,
        "observed_periodic_search_authorized": False,
    }


def _validate_exact_fields(
    record: dict[str, Any], expected: dict[str, Any], label: str
) -> list[str]:
    return [
        f"{label} field mismatch: {key}"
        for key, value in expected.items()
        if record.get(key) != value
    ]


def verify_execution_authority(data_root: Path) -> dict[str, Any]:
    root = repository_root()
    package = verify_package(data_root)
    failures = list(package["failures"])
    fable_path = root / FABLE_SIGNOFF_PATH
    user_path = root / USER_AUTHORIZATION_PATH
    if not fable_path.is_file():
        failures.append("final Fable sign-off is absent")
    if not user_path.is_file():
        failures.append("explicit user authorization is absent")
    if failures:
        return {
            "status": "locked",
            "failures": failures,
            "observed_residual_access_authorized": False,
            "observed_periodic_search_authorized": False,
        }

    fable = json.loads(fable_path.read_text(encoding="utf-8"))
    freeze_hash = package["freeze_sha256"]
    manifest_hash = package["package_manifest_sha256"]
    implementation_hash = package["implementation_sha256"]
    schema_hash = package["candidate_schema_sha256"]
    failures.extend(
        _validate_exact_fields(
            fable,
            {
                "reviewer": "Claude Fable 5",
                "verdict": "PASS",
                "no_conditions_remaining": True,
                "observed_periodic_content_inspected": False,
                "package_manifest_sha256": manifest_hash,
                "one_shot_freeze_sha256": freeze_hash,
                "implementation_sha256": implementation_hash,
                "candidate_schema_sha256": schema_hash,
            },
            "Fable sign-off",
        )
    )
    fable_hash = hash_file(fable_path, "sha256")
    user = json.loads(user_path.read_text(encoding="utf-8"))
    failures.extend(
        _validate_exact_fields(
            user,
            {
                "approved_by_user": True,
                "authorization": "execute_exactly_one_observed_residual_search_v0.1",
                "package_manifest_sha256": manifest_hash,
                "one_shot_freeze_sha256": freeze_hash,
                "implementation_sha256": implementation_hash,
                "fable_signoff_sha256": fable_hash,
            },
            "user authorization",
        )
    )
    return {
        "status": "authorized" if not failures else "locked",
        "failures": failures,
        "package": package,
        "fable_signoff_sha256": fable_hash,
        "user_authorization_sha256": hash_file(user_path, "sha256"),
        "observed_residual_access_authorized": not failures,
        "observed_periodic_search_authorized": not failures,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _candidate_deletion_diagnostics(
    observed: np.ndarray,
    covariance: np.ndarray,
    design: np.ndarray,
    times: np.ndarray,
    frequencies: np.ndarray,
    utc_days: np.ndarray,
    candidate_frequency: float,
    threshold: float,
    epoch: float,
) -> dict[str, Any]:
    units = build_deletion_units(utc_days)
    toa_count = len(times)
    independent_bin = 1.0 / float(np.ptp(times))
    summaries: dict[str, dict[str, Any]] = {}
    for mode in ("paired_wideband_toa_row", "all_rows_on_one_floor_mjd_utc_day"):
        summaries[mode] = {
            "unit_count": 0,
            "minimum_trigger_statistic": math.inf,
            "minimum_trigger_unit_id": None,
            "failed_stability_unit_count": 0,
            "maximum_frequency_error_independent_bin_units": 0.0,
            "mechanical_label": "DELETION_STABLE",
            "candidate_authority": "none_advisory_only",
        }
    calculation_cache: dict[tuple[int, ...], dict[str, Any]] = {}
    for unit in units:
        removed = tuple(int(row) for row in unit["removed_rows"])
        scan = calculation_cache.get(removed)
        if scan is None:
            row_keep = np.ones(toa_count, dtype=bool)
            row_keep[list(removed)] = False
            kept_rows = np.flatnonzero(row_keep)
            coordinate_keep = np.concatenate((kept_rows, toa_count + kept_rows))
            scanner = prepare_covariance_gls_scanner(
                covariance[np.ix_(coordinate_keep, coordinate_keep)],
                design[coordinate_keep],
                times[kept_rows],
                frequencies,
                epoch,
            )
            scan = scanner.scan(observed[coordinate_keep])
            calculation_cache[removed] = scan
        summary = summaries[unit["mode"]]
        statistic = float(scan["trigger_statistic"])
        frequency_error_bins = (
            abs(float(scan["peak_frequency_per_day"]) - candidate_frequency)
            / independent_bin
        )
        stable = statistic > threshold and frequency_error_bins <= 1.0
        summary["unit_count"] += 1
        if statistic < summary["minimum_trigger_statistic"]:
            summary["minimum_trigger_statistic"] = statistic
            summary["minimum_trigger_unit_id"] = unit["unit_id"]
        summary["maximum_frequency_error_independent_bin_units"] = max(
            summary["maximum_frequency_error_independent_bin_units"], frequency_error_bins
        )
        summary["failed_stability_unit_count"] += int(not stable)
    for summary in summaries.values():
        if summary["failed_stability_unit_count"]:
            summary["mechanical_label"] = "DELETION_FRAGILE"
    return {
        "deletion_checks_as_hard_vetoes": False,
        "inventory_sha256": _canonical_hash(units),
        **summaries,
    }


def _mandatory_context() -> dict[str, Any]:
    return {
        "original_tail_7_of_500": {"false_positives": 7, "cases": 500},
        "r1_tail_7_of_1000": {"false_positives": 7, "cases": 1000},
        "clustered_day_16_of_1000": {"false_positives": 16, "cases": 1000},
        "clustered_day_wilson_95": [0.009872242002277388, 0.02583206021173997],
        "paired_row_false_veto_5_of_125": {"false_vetoes": 5, "cases": 125},
        "paired_row_wilson_upper_95": 0.09022555313974442,
        "utc_day_false_veto_6_of_125": {"false_vetoes": 6, "cases": 125},
        "utc_day_wilson_upper_95": 0.10077111031703824,
        "all_deletion_failures_amplitude_microseconds": 0.2,
        "pooled_tail_role": "contextual_only_not_a_gate",
    }


def run_one_shot(data_root: Path) -> dict[str, Any]:
    authority = verify_execution_authority(data_root)
    if authority["status"] != "authorized":
        raise RuntimeError(f"Observed execution remains locked: {authority['failures']}")

    intent_path = data_root / "run_records/pilot1/one-shot-observed-search-v0.1-intent.json"
    result_path = data_root / "run_records/pilot1/one-shot-observed-search-v0.1-result.json"
    if intent_path.exists() or result_path.exists():
        raise RuntimeError("A prior one-shot intent or result exists; automatic retry is forbidden")
    started = datetime.now(UTC)
    intent = {
        "schema_version": 1,
        "search_id": SEARCH_ID,
        "status": "started_single_execution_consumed",
        "started_utc": started.isoformat().replace("+00:00", "Z"),
        "package_manifest_sha256": authority["package"]["package_manifest_sha256"],
        "freeze_sha256": authority["package"]["freeze_sha256"],
        "implementation_sha256": authority["package"]["implementation_sha256"],
        "fable_signoff_sha256": authority["fable_signoff_sha256"],
        "user_authorization_sha256": authority["user_authorization_sha256"],
    }
    _write_json(intent_path, intent)

    start = time.perf_counter()
    config = load_yaml(repository_root() / CONFIG_PATH)
    target = load_pilot_config(repository_root() / "config/target.yaml")
    log_path = data_root / "run_records/pilot1/one-shot-observed-search-v0.1.log"
    import pint.logging

    pint.logging.setup(
        level="INFO", sink=log_path, usecolors=False, capturewarnings=True, removeprior=True
    )
    model, toas = _load_release(data_root)
    from pint.fitter import WidebandDownhillFitter, WidebandTOAFitter
    from pint.residuals import WidebandTOAResiduals

    covariance_fitter = WidebandTOAFitter(toas, model)
    covariance = covariance_fitter.get_noise_covariancematrix().matrix
    design = covariance_fitter.get_designmatrix().matrix
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    utc_days = np.floor(np.asarray(toas.table["mjd_float"], dtype=float)).astype(int)
    detector = config["detector"]
    frequencies, grid = build_search_frequency_grid(
        times,
        float(detector["period_minimum_days"]),
        float(detector["period_maximum_days"]),
        int(detector["frequency_oversampling"]),
    )
    scanner = prepare_covariance_gls_scanner(
        covariance,
        design,
        times,
        frequencies,
        float(detector["reference_epoch_mjd_tdb"]),
    )
    observed = np.asarray(
        WidebandTOAResiduals(toas, model).calc_wideband_resids(), dtype=float
    )
    scan = scanner.scan(observed)
    mask = build_annual_mask(
        frequencies, list(config["annual_mask"]["ineligible_period_targets_days"])
    )
    selected = select_strongest_unmasked(
        scan["all_delta_chi2"], frequencies, mask["masked_grid_indices"]
    )
    threshold = float(detector["locked_threshold_delta_chi2"])
    candidate_present = selected["statistic"] > threshold
    full_index = int(scan["peak_index"])
    full_grid_maximum_masked = full_index in set(mask["masked_grid_indices"])

    refits: dict[str, Any] | None = None
    deletion: dict[str, Any] | None = None
    ordinary_converged: bool | None = None
    joint_converged: bool | None = None
    full_audit_passed: bool | None = None
    if candidate_present:
        ordinary = WidebandDownhillFitter(toas, copy.deepcopy(model))
        ordinary_returned = bool(ordinary.fit_toas(maxiter=target.max_fit_iterations))
        ordinary_residuals = WidebandTOAResiduals(toas, ordinary.model)
        joint = _joint_downhill_fit(
            toas,
            model,
            selected["frequency_per_day"],
            float(detector["reference_epoch_mjd_tdb"]),
            target.max_fit_iterations,
        )
        full = _joint_full_covariance_fit(
            toas,
            model,
            selected["frequency_per_day"],
            float(detector["reference_epoch_mjd_tdb"]),
            target.max_fit_iterations,
        )
        comparison = {
            "amplitude_difference_microseconds": abs(
                float(joint["amplitude_us"]) - float(full["amplitude_us"])
            ),
            "phase_difference_radians": abs(
                wrapped_phase_difference(
                    float(joint["phase_radians"]), float(full["phase_radians"])
                )
            ),
            "chi2_difference": abs(float(joint["chi2"]) - float(full["chi2"])),
        }
        tolerances = config["solver_tolerances"]
        ordinary_converged = bool(ordinary_returned and ordinary.converged)
        joint_converged = bool(joint["returned_converged"] and joint["fitter_converged"])
        full_audit_passed = bool(
            full["completed"]
            and comparison["amplitude_difference_microseconds"]
            <= float(tolerances["amplitude_difference_maximum_microseconds"])
            and comparison["phase_difference_radians"]
            <= float(tolerances["phase_difference_maximum_radians"])
            and comparison["chi2_difference"]
            <= float(tolerances["chi2_difference_maximum"])
        )
        refits = {
            "ordinary": {
                "returned_converged": ordinary_returned,
                "fitter_converged": bool(ordinary.converged),
                "chi2": float(ordinary_residuals.chi2),
            },
            "joint": {
                key: value
                for key, value in joint.items()
                if key not in {"fitter", "model", "residuals"}
            },
            "full_covariance": {
                key: value
                for key, value in full.items()
                if key not in {"fitter", "model", "residuals"}
            },
            "solver_comparison": comparison,
            "robust_refit_included": False,
        }
        deletion = _candidate_deletion_diagnostics(
            observed,
            covariance,
            design,
            times,
            frequencies,
            utc_days,
            selected["frequency_per_day"],
            threshold,
            float(detector["reference_epoch_mjd_tdb"]),
        )

    warnings = classify_warning_lines(
        [
            line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
    )
    elapsed_hours = (time.perf_counter() - start) / 3600.0
    peak_memory_gib = _peak_rss_gib()
    complete_data_root_gib = _directory_size_gib(data_root)
    resource_config = config["resources"]
    resource_envelope = {
        "wall_hours_within_limit": elapsed_hours
        <= float(resource_config["wall_hours_maximum"]),
        "peak_memory_within_limit": peak_memory_gib
        <= float(resource_config["peak_memory_gib_maximum"]),
        "complete_data_root_within_limit": complete_data_root_gib
        <= float(resource_config["complete_data_root_gib_maximum"]),
    }
    resource_envelope_passed = all(resource_envelope.values())
    valid = bool(
        warnings["status"] == "pass"
        and resource_envelope_passed
        and (
            not candidate_present
            or (ordinary_converged and joint_converged and full_audit_passed)
        )
    )
    run_status = "complete" if valid else "aborted_integrity_failure"
    report = {
        "schema_version": 1,
        "search_id": SEARCH_ID,
        "execution_identity": {
            "package_manifest_sha256": authority["package"]["package_manifest_sha256"],
            "freeze_sha256": authority["package"]["freeze_sha256"],
            "implementation_sha256": authority["package"]["implementation_sha256"],
            "fable_signoff_sha256": authority["fable_signoff_sha256"],
            "user_authorization_sha256": authority["user_authorization_sha256"],
        },
        "detector": {
            "locked_threshold_delta_chi2": threshold,
            "threshold_comparison": "strictly_greater_than",
            "period_minimum_days": float(detector["period_minimum_days"]),
            "period_maximum_days": float(detector["period_maximum_days"]),
            "frequency_count": len(frequencies),
            "scan_count": 1,
            "frequency_grid": grid,
        },
        "annual_mask": mask,
        "outcome": {
            "run_status": run_status,
            "candidate_present": candidate_present,
            "strongest_unmasked_statistic": selected["statistic"],
            "strongest_unmasked_frequency_per_day": selected["frequency_per_day"],
            "strongest_unmasked_period_days": selected["period_days"],
            "full_grid_maximum_statistic": float(scan["trigger_statistic"]),
            "full_grid_maximum_masked": full_grid_maximum_masked,
        },
        "candidate_refits": refits,
        "deletion_diagnostics": deletion,
        "mandatory_context": _mandatory_context(),
        "integrity": {
            "hashes_verified": True,
            "ordinary_refit_converged": ordinary_converged,
            "joint_refit_converged": joint_converged,
            "full_covariance_audit_passed": full_audit_passed,
            "warning_hygiene": warnings,
            "resource_envelope_passed": resource_envelope_passed,
            "observed_scan_count": 1,
        },
        "resources": {
            "wall_hours": elapsed_hours,
            "wall_hours_maximum": float(resource_config["wall_hours_maximum"]),
            "peak_memory_gib": peak_memory_gib,
            "peak_memory_gib_maximum": float(
                resource_config["peak_memory_gib_maximum"]
            ),
            "complete_data_root_gib": complete_data_root_gib,
            "complete_data_root_gib_maximum": float(
                resource_config["complete_data_root_gib_maximum"]
            ),
            "envelope_tests": resource_envelope,
        },
        "authorization_boundary": {
            "single_execution_consumed": True,
            "additional_observed_search_authorized": False,
            "discovery_claim_authorized": False,
        },
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    _write_json(result_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m pulsar_pilot.one_shot_search")
    parser.add_argument("--data-root")
    parser.add_argument("--verify-package", action="store_true")
    parser.add_argument("--verify-authority", action="store_true")
    parser.add_argument("--execute-one-shot", action="store_true")
    args = parser.parse_args()
    data_root = configured_data_root(args.data_root)
    require_initialized_data_root(data_root)
    if args.execute_one_shot:
        result = run_one_shot(data_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["outcome"]["run_status"] == "complete" else 2
    result = (
        verify_execution_authority(data_root)
        if args.verify_authority
        else verify_package(data_root)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"pass", "authorized"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
