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
from scipy.stats import kurtosis

from .c1 import generate_circular_delay_us
from .config import load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _load_release, _peak_rss_gib
from .pilot1_evaluation import wilson_interval_95
from .pilot1_runtime import (
    ResumableArtifactLedger,
    build_search_frequency_grid,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .preunblinding import (
    CONFIG_PATH,
    build_structured_tail_inventory,
    inventory_hashes,
)
from .preunblinding import verify_freeze as verify_preparation_freeze
from .provenance import hash_file, logical_path
from .tail_robustness import (
    _canonical_hash,
    build_recovery_order,
    generate_contaminated_null,
)

VALIDATION_ID = "pilot1-preunblinding-validation-v0.1"
EXECUTION_FREEZE_PATH = "protocol/PILOT1_PREUNBLINDING_EXECUTION_FREEZE_v0.1.json"
PREPARATION_FREEZE_PATH = "protocol/PILOT1_PREUNBLINDING_VALIDATION_FREEZE_v0.1.json"
V0P1_TAIL_CONFIG_PATH = "config/pilot1_tail_robustness_v0.1.yaml"
IMPLEMENTATION_PATH = "src/pulsar_pilot/preunblinding_validation.py"


def _mixture_scale(probability: float, multiplier: float) -> float:
    return math.sqrt((1.0 - probability) + probability * multiplier**2)


def generate_structured_null(
    covariance_cholesky: np.ndarray,
    generator: np.random.Generator,
    variant: dict[str, Any],
    toa_count: int,
    utc_days: np.ndarray,
) -> tuple[np.ndarray, int]:
    factor = np.asarray(covariance_cholesky, dtype=float)
    if factor.shape != (2 * toa_count, 2 * toa_count):
        raise ValueError("Structured null requires paired timing and DM coordinates")
    days = np.asarray(utc_days, dtype=int)
    if days.shape != (toa_count,):
        raise ValueError("UTC-day inventory does not match the TOA count")

    innovations = generator.standard_normal(factor.shape[0])
    multiplier = float(variant["contaminated_standard_deviation_multiplier"])
    contaminated = np.zeros(factor.shape[0], dtype=bool)

    if "selected_native_innovation_block" in variant:
        probability = float(variant["contaminated_probability"])
        block = str(variant["selected_native_innovation_block"])
        start, stop = (0, toa_count) if block == "timing" else (toa_count, 2 * toa_count)
        block_mask = generator.random(toa_count) < probability
        contaminated[start:stop] = block_mask
        innovations[start:stop][block_mask] *= multiplier
        innovations[start:stop] /= _mixture_scale(probability, multiplier)
    else:
        probability = float(variant["selected_day_probability"])
        unique_days = np.asarray(sorted(set(days.tolist())), dtype=int)
        selected_days = unique_days[generator.random(len(unique_days)) < probability]
        row_mask = np.isin(days, selected_days)
        contaminated[:toa_count] = row_mask
        contaminated[toa_count:] = row_mask
        innovations[contaminated] *= multiplier
        innovations /= _mixture_scale(probability, multiplier)

    return factor @ innovations, int(np.sum(contaminated))


def build_deletion_units(utc_days: np.ndarray) -> list[dict[str, Any]]:
    days = np.asarray(utc_days, dtype=int)
    units = [
        {
            "unit_id": f"paired-row-{row:04d}",
            "mode": "paired_wideband_toa_row",
            "removed_rows": [row],
        }
        for row in range(len(days))
    ]
    units.extend(
        {
            "unit_id": f"utc-day-{day}",
            "mode": "all_rows_on_one_floor_mjd_utc_day",
            "removed_rows": np.flatnonzero(days == day).astype(int).tolist(),
        }
        for day in sorted(set(days.tolist()))
    )
    return units


def execution_inventory_hashes(config: dict[str, Any], utc_days: np.ndarray) -> dict[str, str]:
    prepared = inventory_hashes(config)
    return {
        **prepared,
        "deletion_units": _canonical_hash(build_deletion_units(utc_days)),
    }


def _external_prerequisites(data_root: Path, freeze: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for relative, expected in freeze.get("external_prerequisites", {}).items():
        path = data_root / relative
        if not path.is_file() or path.stat().st_size != int(expected["bytes"]):
            failures.append(f"missing or wrong size: {relative}")
        elif hash_file(path, "sha256") != expected["sha256"]:
            failures.append(f"hash mismatch: {relative}")
    return {"status": "pass" if not failures else "fail", "failures": failures}


def verify_execution_freeze(data_root: Path) -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / EXECUTION_FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    config = load_yaml(root / CONFIG_PATH)
    failures: list[str] = []

    preparation = verify_preparation_freeze()
    if preparation["status"] != "pass":
        failures.append("preparation freeze verification failed")
    if freeze.get("status") != "frozen_before_synthetic_execution":
        failures.append("execution freeze status is invalid")
    if freeze.get("authorization") != "exact_frozen_synthetic_validation_only":
        failures.append("execution authorization is invalid")
    for field in (
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "threshold_retuning_authorized",
        "new_recovery_randomness_authorized",
        "further_tail_reroll_authorized",
    ):
        if freeze.get(field) is not False:
            failures.append(f"{field} must be false")
    if freeze.get("preparation_freeze_sha256") != hash_file(
        root / PREPARATION_FREEZE_PATH, "sha256"
    ):
        failures.append("preparation freeze hash mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        path = root / relative
        if not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"hash mismatch: {relative}")

    model, toas = _load_release(data_root)
    del model
    utc_days = np.floor(np.asarray(toas.table["mjd_float"], dtype=float)).astype(int)
    observed_inventory = execution_inventory_hashes(config, utc_days)
    if freeze.get("inventory_sha256") != observed_inventory:
        failures.append("execution inventory hash mismatch")
    external = _external_prerequisites(data_root, freeze)
    if external["status"] != "pass":
        failures.extend(external["failures"])
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_sha256": hash_file(freeze_path, "sha256"),
        "inventory_sha256": observed_inventory,
        "deletion_units": len(build_deletion_units(utc_days)),
        "external_prerequisites": external,
        "observed_periodic_search_authorized": False,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_verified_recovery_records(data_root: Path) -> list[dict[str, Any]]:
    ledger_path = data_root / "run_records/pilot1/tail-robustness-recovery-v0.1-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for case_id, artifact in sorted(ledger["completed_cases"].items()):
        path = data_root / artifact["logical_path"]
        if not path.is_file() or hash_file(path, "sha256") != artifact["sha256"]:
            raise RuntimeError(f"Immutable recovery artifact failed verification: {case_id}")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["case"]["case_id"] != case_id:
            raise RuntimeError(f"Recovery artifact case mismatch: {case_id}")
        records.append(record)
    if len(records) != 160:
        raise RuntimeError("Exactly 160 immutable recovery artifacts are required")
    return records


def _projected_metrics(samples: list[np.ndarray], toa_count: int) -> dict[str, float]:
    values = np.asarray(samples, dtype=float)
    return {
        "combined_absolute_excess_kurtosis": abs(
            float(kurtosis(values.reshape(-1), fisher=True, bias=False))
        ),
        "timing_block_absolute_excess_kurtosis": abs(
            float(kurtosis(values[:, :toa_count].reshape(-1), fisher=True, bias=False))
        ),
        "dm_block_absolute_excess_kurtosis": abs(
            float(kurtosis(values[:, toa_count:].reshape(-1), fisher=True, bias=False))
        ),
        "variance": float(np.var(values, ddof=1)),
    }


def _run_structured_tail(
    data_root: Path,
    config: dict[str, Any],
    factor: np.ndarray,
    scanner: Any,
    toa_count: int,
    utc_days: np.ndarray,
    execution_binding: str,
) -> dict[str, Any]:
    output_root = data_root / "derived/pilot1/preunblinding-validation-v0.1/structured-tail"
    records = build_structured_tail_inventory(config)
    by_variant = {
        str(variant["id"]): variant
        for variant in config["structured_tail_variants"]["variants"]
    }
    common = config["structured_tail_variants"]["common"]
    threshold = float(common["threshold_delta_chi2"])
    summaries: dict[str, Any] = {}

    for variant_id, variant in by_variant.items():
        cases = [record for record in records if record["variant"] == variant_id]
        inventory_hash = _canonical_hash(cases)
        ledger = ResumableArtifactLedger(
            data_root
            / f"run_records/pilot1/preunblinding-{variant_id}-v0.1-ledger.json",
            inventory_hash,
            execution_binding,
        )
        state = ledger.load()
        variant_records: list[dict[str, Any]] = []
        noise_samples: list[np.ndarray] = []
        projected_samples: list[np.ndarray] = []
        for sequence, case in enumerate(cases, 1):
            noise, contaminated_count = generate_structured_null(
                factor,
                np.random.default_rng(int(case["seed"])),
                {
                    **variant,
                    "contaminated_probability": common["contaminated_probability"],
                },
                toa_count,
                utc_days,
            )
            noise_samples.append(noise)
            projected_samples.append(scanner.whiten_and_project(noise))
            path = output_root / variant_id / f"{sequence:04d}-{case['case_id']}.json"
            if case["case_id"] in state["completed_cases"]:
                variant_records.append(json.loads(path.read_text(encoding="utf-8")))
                continue
            scan = scanner.scan(noise)
            record = {
                "schema_version": 1,
                "validation_id": VALIDATION_ID,
                "case": case,
                "contaminated_coordinate_count": contaminated_count,
                "triggered": float(scan["trigger_statistic"]) > threshold,
                "locked_threshold_delta_chi2": threshold,
                "trigger": {
                    key: value for key, value in scan.items() if not key.startswith("all_")
                },
            }
            _write_json(path, record)
            ledger.record(case["case_id"], path, data_root)
            variant_records.append(record)

        false_positives = sum(bool(record["triggered"]) for record in variant_records)
        interval = wilson_interval_95(false_positives, len(variant_records))
        summaries[variant_id] = {
            "cases": len(variant_records),
            "false_positives": false_positives,
            "false_positive_rate": interval["proportion"],
            "wilson_95": interval,
            "rebaseline_tripwire_crossed": interval["lower"] > 0.01,
            "projected_metrics": _projected_metrics(projected_samples, toa_count),
            "native_whitened_diagnostics": null_ensemble_diagnostics(
                np.asarray(noise_samples), factor
            ),
            "ledger": ledger.verify(data_root),
        }
    return summaries


def _regenerate_recovery_vectors(
    config: dict[str, Any],
    factor: np.ndarray,
    times: np.ndarray,
    scanner: Any,
    source_records: list[dict[str, Any]],
) -> tuple[dict[str, np.ndarray], list[str]]:
    root = repository_root()
    tail_config = load_yaml(root / V0P1_TAIL_CONFIG_PATH)
    contamination = tail_config["contamination_model"]
    probability = float(contamination["contaminated_coordinate_probability"])
    multiplier = float(contamination["contaminated_standard_deviation_multiplier"])
    epoch = float(load_yaml(root / "config/pilot1.yaml")["injections"]["reference_epoch_mjd_tdb"])
    toa_count = len(times)
    by_id = {record["case"]["case_id"]: record for record in source_records}
    vectors: dict[str, np.ndarray] = {}
    failures: list[str] = []
    for case in build_recovery_order(tail_config):
        noise, _ = generate_contaminated_null(
            factor, np.random.default_rng(int(case["seed"])), probability, multiplier
        )
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
        source = by_id[case["case_id"]]
        if not math.isclose(
            float(scan["trigger_statistic"]),
            float(source["trigger"]["trigger_statistic"]),
            rel_tol=0.0,
            abs_tol=1e-9,
        ) or not math.isclose(
            float(scan["peak_frequency_per_day"]),
            float(source["trigger"]["peak_frequency_per_day"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            failures.append(case["case_id"])
        vectors[case["case_id"]] = requested
    return vectors, failures


def _run_deletion_cost(
    data_root: Path,
    config: dict[str, Any],
    covariance: np.ndarray,
    design: np.ndarray,
    times: np.ndarray,
    frequencies: np.ndarray,
    utc_days: np.ndarray,
    full_scanner: Any,
    execution_binding: str,
) -> dict[str, Any]:
    source_records = _load_verified_recovery_records(data_root)
    vectors, replay_failures = _regenerate_recovery_vectors(
        config, full_scanner.covariance_cholesky, times, full_scanner, source_records
    )
    eligible = [
        record
        for record in source_records
        if bool(record["triggered"] and record["frequency_recovered"])
    ]
    eligible_ids = [record["case"]["case_id"] for record in eligible]
    injected_frequency = {
        record["case"]["case_id"]: 1.0 / float(record["case"]["period_days"])
        for record in eligible
    }
    threshold = float(config["locked_detector"]["threshold_delta_chi2"])
    independent_bin = 1.0 / float(np.ptp(times))
    units = build_deletion_units(utc_days)
    unit_hash = _canonical_hash(units)
    ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/preunblinding-deletion-cost-v0.1-ledger.json",
        unit_hash,
        execution_binding,
    )
    state = ledger.load()
    output_root = data_root / "derived/pilot1/preunblinding-validation-v0.1/deletion"
    unit_records: list[dict[str, Any]] = []
    calculation_cache: dict[tuple[int, ...], list[dict[str, Any]]] = {}
    toa_count = len(times)
    epoch = float(
        load_yaml(repository_root() / "config/pilot1.yaml")["injections"]
        ["reference_epoch_mjd_tdb"]
    )

    for sequence, unit in enumerate(units, 1):
        path = output_root / unit["mode"] / f"{sequence:04d}-{unit['unit_id']}.json"
        if unit["unit_id"] in state["completed_cases"]:
            unit_records.append(json.loads(path.read_text(encoding="utf-8")))
            continue
        removed = tuple(int(row) for row in unit["removed_rows"])
        results = calculation_cache.get(removed)
        if results is None:
            row_keep = np.ones(toa_count, dtype=bool)
            row_keep[list(removed)] = False
            kept_rows = np.flatnonzero(row_keep)
            coordinate_keep = np.concatenate((kept_rows, toa_count + kept_rows))
            reduced_scanner = prepare_covariance_gls_scanner(
                covariance[np.ix_(coordinate_keep, coordinate_keep)],
                design[coordinate_keep],
                times[kept_rows],
                frequencies,
                epoch,
            )
            results = []
            for case_id in eligible_ids:
                scan = reduced_scanner.scan(vectors[case_id][coordinate_keep])
                frequency_error = abs(
                    float(scan["peak_frequency_per_day"]) - injected_frequency[case_id]
                )
                results.append(
                    {
                        "case_id": case_id,
                        "trigger_statistic": float(scan["trigger_statistic"]),
                        "peak_frequency_per_day": float(scan["peak_frequency_per_day"]),
                        "frequency_error_per_day": frequency_error,
                        "stable": bool(
                            float(scan["trigger_statistic"]) > threshold
                            and frequency_error <= independent_bin
                        ),
                    }
                )
            calculation_cache[removed] = results
        record = {
            "schema_version": 1,
            "validation_id": VALIDATION_ID,
            "unit": unit,
            "eligible_source_cases": len(eligible_ids),
            "results": results,
        }
        _write_json(path, record)
        ledger.record(unit["unit_id"], path, data_root)
        unit_records.append(record)
        if sequence % 25 == 0 or sequence == len(units):
            print(
                json.dumps(
                    {
                        "stage": "deletion_stability",
                        "completed_units": sequence,
                        "total_units": len(units),
                    }
                ),
                flush=True,
            )

    summaries: dict[str, Any] = {}
    gate = config["deletion_stability_cost"]["hard_veto_adoption_gate"]
    for mode in config["deletion_stability_cost"]["deletion_units"]:
        mode_records = [record for record in unit_records if record["unit"]["mode"] == mode]
        stable_by_case = {case_id: True for case_id in eligible_ids}
        minimum_statistic = {case_id: math.inf for case_id in eligible_ids}
        for record in mode_records:
            for result in record["results"]:
                case_id = result["case_id"]
                stable_by_case[case_id] &= bool(result["stable"])
                minimum_statistic[case_id] = min(
                    minimum_statistic[case_id], float(result["trigger_statistic"])
                )
        false_vetoes = sum(not stable for stable in stable_by_case.values())
        interval = wilson_interval_95(false_vetoes, len(eligible_ids))
        passed = bool(
            interval["proportion"]
            <= float(gate["observed_false_veto_rate_maximum"])
            and interval["upper"] <= float(gate["wilson_upper_95_maximum"])
            and not replay_failures
        )
        summaries[mode] = {
            "deletion_units": len(mode_records),
            "eligible_source_cases": len(eligible_ids),
            "false_vetoes": false_vetoes,
            "false_veto_rate": interval["proportion"],
            "wilson_95": interval,
            "hard_veto_adoption_gate": "PASS" if passed else "FAIL",
            "minimum_trigger_statistic_by_case": minimum_statistic,
        }
    return {
        "source_cases": len(source_records),
        "eligible_source_cases": len(eligible_ids),
        "exact_replay_failures": replay_failures,
        "unit_inventory_sha256": unit_hash,
        "modes": summaries,
        "ledger": ledger.verify(data_root),
    }


def run_validation(data_root: Path) -> dict[str, Any]:
    verification = verify_execution_freeze(data_root)
    if verification["status"] != "pass":
        raise RuntimeError(f"Execution freeze failed: {verification}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    freeze_hash = verification["freeze_sha256"]
    execution_binding = hashlib.sha256(
        (hash_file(root / IMPLEMENTATION_PATH, "sha256") + ":" + freeze_hash).encode()
    ).hexdigest()

    log_path = data_root / "run_records/pilot1/preunblinding-validation-v0.1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
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
    utc_days = np.floor(
        np.asarray(release_toas.table["mjd_float"], dtype=float)
    ).astype(int)
    locked = config["locked_detector"]
    frequencies, grid = build_search_frequency_grid(
        times,
        float(locked["search_period_minimum_days"]),
        float(locked["search_period_maximum_days"]),
    )
    epoch = float(
        load_yaml(root / "config/pilot1.yaml")["injections"]["reference_epoch_mjd_tdb"]
    )
    scanner = prepare_covariance_gls_scanner(covariance, design, times, frequencies, epoch)

    structured = _run_structured_tail(
        data_root,
        config,
        scanner.covariance_cholesky,
        scanner,
        len(times),
        utc_days,
        execution_binding,
    )
    deletion = _run_deletion_cost(
        data_root,
        config,
        covariance,
        design,
        times,
        frequencies,
        utc_days,
        scanner,
        execution_binding,
    )
    elapsed_hours = (time.perf_counter() - start) / 3600.0
    warning_lines = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    warnings = classify_warning_lines(warning_lines)
    resources = config["resources"]
    structured_pass = all(
        not bool(summary["rebaseline_tripwire_crossed"])
        and summary["ledger"]["status"] == "pass"
        for summary in structured.values()
    )
    deletion_pass = all(
        mode["hard_veto_adoption_gate"] == "PASS"
        for mode in deletion["modes"].values()
    )
    criteria = {
        "execution_freeze_verified": verification["status"] == "pass",
        "external_prerequisites_verified": verification["external_prerequisites"]["status"]
        == "pass",
        "exactly_3000_structured_tail_cases": sum(
            int(summary["cases"]) for summary in structured.values()
        )
        == 3000,
        "structured_tail_tripwires_clear": structured_pass,
        "exactly_160_deterministic_source_cases": deletion["source_cases"] == 160,
        "deterministic_replay_exact": not deletion["exact_replay_failures"],
        "deletion_ledgers_verified": deletion["ledger"]["status"] == "pass",
        "deletion_hard_veto_cost_gates": deletion_pass,
        "warning_hygiene": warnings["status"] == "pass",
        "runtime_under_cap": elapsed_hours
        <= float(resources["macbook_wall_hours_maximum"]),
        "peak_memory_under_cap": _peak_rss_gib()
        <= float(resources["peak_memory_gib_maximum"]),
        "storage_under_cap": _directory_size_gib(data_root)
        <= float(resources["complete_data_root_gib_maximum"]),
        "observed_residual_access_not_executed": True,
        "observed_periodic_search_not_executed": True,
        "independent_fable_signoff_still_required": True,
    }
    score = {
        "overall": "PASS" if all(criteria.values()) else "FAIL",
        "passed": sum(criteria.values()),
        "total": len(criteria),
        "criteria": {key: "PASS" if value else "FAIL" for key, value in criteria.items()},
    }
    result = {
        "schema_version": 1,
        "validation_id": VALIDATION_ID,
        "status": "pass" if score["overall"] == "PASS" else "fail",
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "execution_freeze_sha256": freeze_hash,
        "execution_binding_sha256": execution_binding,
        "locked_threshold_delta_chi2": float(locked["threshold_delta_chi2"]),
        "search_grid": grid,
        "structured_tail": structured,
        "deletion_stability_cost": deletion,
        "warnings": warnings,
        "resources": {
            "wall_hours": elapsed_hours,
            "peak_memory_gib": _peak_rss_gib(),
            "complete_data_root_gib": _directory_size_gib(data_root),
        },
        "score": score,
        "authorization": {
            "independent_fable_signoff_required": True,
            "observed_residual_access_authorized": False,
            "observed_periodic_search_authorized": False,
        },
        "next_gate": (
            "prepare_hash_bound_fable_reviewer_packet"
            if score["overall"] == "PASS"
            else "detector_rebaseline_or_independent_disposition"
        ),
    }
    summary_path = data_root / "run_records/pilot1/preunblinding-validation-v0.1-summary.json"
    _write_json(summary_path, result)
    compact = {
        **result,
        "deletion_stability_cost": {
            key: value
            for key, value in deletion.items()
            if key != "modes"
        }
        | {
            "modes": {
                mode: {
                    key: value
                    for key, value in summary.items()
                    if key != "minimum_trigger_statistic_by_case"
                }
                for mode, summary in deletion["modes"].items()
            }
        },
        "external_record": {
            "logical_path": logical_path(summary_path, data_root),
            "bytes": summary_path.stat().st_size,
            "sha256": hash_file(summary_path, "sha256"),
        },
    }
    return compact


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m pulsar_pilot.preunblinding_validation")
    parser.add_argument("--data-root")
    parser.add_argument("--verify-freeze", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--execute-synthetic", action="store_true")
    args = parser.parse_args()
    data_root = configured_data_root(args.data_root)
    require_initialized_data_root(data_root)
    if args.execute_synthetic:
        result = run_validation(data_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 2
    verification = verify_execution_freeze(data_root)
    if args.plan_only:
        verification["execution_requested"] = False
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0 if verification["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
