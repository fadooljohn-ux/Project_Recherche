from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import time
from datetime import UTC, datetime
from itertools import pairwise, product
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import kurtosis

from .c1 import generate_circular_delay_us
from .c1r1 import _joint_downhill_fit, _joint_full_covariance_fit, wrapped_phase_difference
from .config import load_pilot_config, load_yaml
from .g2 import classify_warning_lines
from .paths import configured_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _directory_size_gib, _load_release, _peak_rss_gib, _synthetic_toas
from .pilot1_evaluation import wilson_interval_95
from .pilot1_injections import bracketed_crossing_amplitude
from .pilot1_runtime import (
    ResumableArtifactLedger,
    build_search_frequency_grid,
    conservative_nearest_rank,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .provenance import hash_file, logical_path

GATE_ID = "pilot1-tail-robustness-v0.1"
CONFIG_PATH = "config/pilot1_tail_robustness_v0.1.yaml"
PROTOCOL_PATH = "protocol/PILOT1_TAIL_ROBUSTNESS_PROTOCOL_v0.1.md"
FREEZE_PATH = "protocol/PILOT1_TAIL_ROBUSTNESS_FREEZE_v0.1.json"
INITIAL_THRESHOLD_PATH = "protocol/PILOT1_THRESHOLD_LOCK_v0.1.json"


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _seed_for_case(base_seed: int, case_id: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def theoretical_mixture_excess_kurtosis(probability: float, multiplier: float) -> float:
    if not 0.0 < probability < 1.0 or multiplier <= 1.0:
        raise ValueError("Invalid scale-mixture parameters")
    variance = (1.0 - probability) + probability * multiplier**2
    fourth_moment = 3.0 * ((1.0 - probability) + probability * multiplier**4)
    return fourth_moment / variance**2 - 3.0


def generate_contaminated_null(
    covariance_cholesky: np.ndarray,
    generator: np.random.Generator,
    probability: float,
    multiplier: float,
) -> tuple[np.ndarray, int]:
    factor = np.asarray(covariance_cholesky, dtype=float)
    if factor.ndim != 2 or factor.shape[0] != factor.shape[1]:
        raise ValueError("Covariance Cholesky factor must be square")
    innovations = generator.standard_normal(factor.shape[0])
    contaminated = generator.random(factor.shape[0]) < probability
    innovations[contaminated] *= multiplier
    analytic_scale = math.sqrt((1.0 - probability) + probability * multiplier**2)
    innovations /= analytic_scale
    return factor @ innovations, int(np.sum(contaminated))


def build_null_orders(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    nulls = config["nulls"]
    orders: dict[str, list[dict[str, Any]]] = {}
    for family, count_key, seed_key in (
        ("calibration", "calibration_count", "calibration_base_seed"),
        ("evaluation", "evaluation_count", "evaluation_base_seed"),
    ):
        orders[family] = []
        for index in range(int(nulls[count_key])):
            case_id = f"tail-null-{family}-{index:04d}"
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
    if {case["case_id"] for case in calibration} & {case["case_id"] for case in evaluation}:
        raise RuntimeError("Tail calibration and evaluation case IDs overlap")
    if {case["seed"] for case in calibration} & {case["seed"] for case in evaluation}:
        raise RuntimeError("Tail calibration and evaluation seeds overlap")
    return orders


def build_recovery_order(config: dict[str, Any]) -> list[dict[str, Any]]:
    recovery = config["recovery"]
    order: list[dict[str, Any]] = []
    for period_index, amplitude_index, phase_index, noise_index in product(
        range(len(recovery["periods_days"])),
        range(len(recovery["amplitudes_microseconds"])),
        range(len(recovery["phases_radians"])),
        range(int(recovery["contaminated_noise_realizations_per_phase"])),
    ):
        case_id = (
            f"tail-inj-p{period_index:02d}-a{amplitude_index:02d}"
            f"-h{phase_index:02d}-n{noise_index:02d}"
        )
        order.append(
            {
                "case_id": case_id,
                "period_days": float(recovery["periods_days"][period_index]),
                "amplitude_microseconds": float(
                    recovery["amplitudes_microseconds"][amplitude_index]
                ),
                "phase_radians": float(recovery["phases_radians"][phase_index]),
                "noise_realization_index": noise_index,
                "seed": _seed_for_case(int(recovery["base_seed"]), case_id),
            }
        )
    ranked = sorted(order, key=lambda item: hashlib.sha256(item["case_id"].encode()).hexdigest())
    refit_ids = {
        case["case_id"] for case in ranked[: int(recovery["complete_refit_audit_count"])]
    }
    full_ids = {
        case["case_id"] for case in ranked[: int(recovery["full_covariance_audit_count"])]
    }
    order = [
        {
            **case,
            "complete_refit_audit": case["case_id"] in refit_ids,
            "full_covariance_audit": case["case_id"] in full_ids,
        }
        for case in order
    ]
    if len(order) != int(recovery["case_count"]):
        raise RuntimeError("Tail recovery case count does not match config")
    if not full_ids <= refit_ids:
        raise RuntimeError("Full covariance audits must be a subset of complete refits")
    return order


def inventory_hashes(config: dict[str, Any]) -> dict[str, str]:
    nulls = build_null_orders(config)
    return {
        "calibration": _canonical_hash(nulls["calibration"]),
        "evaluation": _canonical_hash(nulls["evaluation"]),
        "recovery": _canonical_hash(build_recovery_order(config)),
    }


def verify_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    config = load_yaml(root / CONFIG_PATH)
    failures: list[str] = []
    if freeze.get("status") != "frozen_before_tail_robustness_execution":
        failures.append("freeze status is invalid")
    if freeze.get("authorization") != "nonperiodic_localization_and_exact_frozen_synthetic_stress_only":
        failures.append("freeze authorization is invalid")
    if freeze.get("observed_residual_periodic_search_authorized") is not False:
        failures.append("observed periodic search must remain unauthorized")
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


def _absolute_excess_kurtosis(values: np.ndarray) -> float:
    return abs(float(kurtosis(np.asarray(values, dtype=float), fisher=True, bias=False)))


def _metadata_for_rows(toas: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in toas.table:
        flags = row["flags"]
        rows.append(
            {
                "mjd_utc": float(row["mjd_float"]),
                "utc_day": math.floor(float(row["mjd_float"])),
                "observing_frequency_mhz": float(row["freq"]),
                "backend": str(flags.get("be", "unknown")),
                "frontend": str(flags.get("fe", "unknown")),
                "observing_system": str(flags.get("f", "unknown")),
            }
        )
    return rows


def _block_metrics(values: np.ndarray, toa_count: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, block in (("toa", values[:toa_count]), ("dm", values[toa_count:])):
        result[name] = {
            "count": len(block),
            "absolute_excess_kurtosis": _absolute_excess_kurtosis(block),
            "maximum_absolute": float(np.max(np.abs(block))),
            "squared_energy": float(block @ block),
        }
    return result


def _influence_localization(
    values: np.ndarray,
    metadata: list[dict[str, Any]],
    toa_count: int,
    top_count: int,
    groupings: list[str],
) -> dict[str, Any]:
    vector = np.asarray(values, dtype=float)
    full_kurtosis = _absolute_excess_kurtosis(vector)
    energy = float(vector @ vector)
    ranking = np.argsort(np.abs(vector))[::-1]
    top_rows: list[dict[str, Any]] = []
    for coordinate in ranking[:top_count]:
        row_index = int(coordinate if coordinate < toa_count else coordinate - toa_count)
        top_rows.append(
            {
                "coordinate": int(coordinate),
                "block": "toa" if coordinate < toa_count else "dm",
                "row_index": row_index,
                "value": float(vector[coordinate]),
                "absolute_value": float(abs(vector[coordinate])),
                "squared_energy_fraction": float(vector[coordinate] ** 2 / energy),
                **metadata[row_index],
            }
        )
    leave_one: list[dict[str, Any]] = []
    for coordinate in ranking[:top_count]:
        reduced = np.delete(vector, coordinate)
        reduced_kurtosis = _absolute_excess_kurtosis(reduced)
        leave_one.append(
            {
                "coordinate": int(coordinate),
                "absolute_excess_kurtosis_without_coordinate": reduced_kurtosis,
                "reduction": full_kurtosis - reduced_kurtosis,
                "reduction_fraction": (
                    (full_kurtosis - reduced_kurtosis) / full_kurtosis
                    if full_kurtosis > 0
                    else 0.0
                ),
            }
        )
    group_influence: dict[str, Any] = {}
    expanded_metadata = metadata + metadata
    for grouping in groupings:
        labels = [item[grouping] for item in expanded_metadata]
        candidates: list[dict[str, Any]] = []
        for label in sorted(set(labels), key=str):
            keep = np.asarray([value != label for value in labels], dtype=bool)
            if int(np.sum(keep)) < 8:
                continue
            reduced_kurtosis = _absolute_excess_kurtosis(vector[keep])
            candidates.append(
                {
                    "label": label,
                    "removed_coordinates": int(np.sum(~keep)),
                    "absolute_excess_kurtosis_without_group": reduced_kurtosis,
                    "reduction": full_kurtosis - reduced_kurtosis,
                    "reduction_fraction": (
                        (full_kurtosis - reduced_kurtosis) / full_kurtosis
                        if full_kurtosis > 0
                        else 0.0
                    ),
                }
            )
        group_influence[grouping] = max(
            candidates,
            key=lambda item: float(item["reduction"]),
            default=None,
        )
    return {
        "absolute_excess_kurtosis": full_kurtosis,
        "squared_energy": energy,
        "top_one_squared_energy_fraction": float(vector[ranking[0]] ** 2 / energy),
        "top_five_squared_energy_fraction": float(
            np.sum(vector[ranking[:5]] ** 2) / energy
        ),
        "top_coordinates": top_rows,
        "leave_one_top_coordinate_influence": leave_one,
        "maximum_leave_one_reduction_fraction": max(
            (float(item["reduction_fraction"]) for item in leave_one), default=0.0
        ),
        "maximum_group_reduction": group_influence,
    }


def observed_nonperiodic_localization(
    model: Any,
    toas: Any,
    covariance: np.ndarray,
    scanner: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    from pint.residuals import WidebandTOAResiduals

    observed = np.asarray(
        WidebandTOAResiduals(toas, model).calc_wideband_resids(), dtype=float
    )
    projected = scanner.whiten_and_project(observed)
    raw_standardized = observed / np.sqrt(np.diag(covariance))
    metadata = _metadata_for_rows(toas)
    localization = config["localization"]
    return {
        "status": "complete",
        "observed_residual_periodic_search_executed": False,
        "observed_frequency_grid_scanned": False,
        "toa_count": len(toas),
        "combined_dimension": len(observed),
        "projected": {
            "blocks": _block_metrics(projected, len(toas)),
            "influence": _influence_localization(
                projected,
                metadata,
                len(toas),
                int(localization["top_influence_coordinates"]),
                list(localization["groupings"]),
            ),
        },
        "raw_standardized": {
            "blocks": _block_metrics(raw_standardized, len(toas)),
            "absolute_excess_kurtosis": _absolute_excess_kurtosis(raw_standardized),
        },
        "coordinate_mapping_limitation": (
            "whitening_and_timing_projection_mix_coordinates; metadata_is_an_influence_locator"
        ),
    }


def _write_case(
    path: Path,
    record: dict[str, Any],
    ledger: ResumableArtifactLedger,
    data_root: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ledger.record(record["case"]["case_id"], path, data_root)


def _recovery_surface(records: list[dict[str, Any]]) -> dict[str, Any]:
    periods = sorted({float(record["case"]["period_days"]) for record in records})
    amplitudes = sorted(
        {float(record["case"]["amplitude_microseconds"]) for record in records}
    )
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
                bool(record["triggered"] and record["frequency_recovered"])
                for record in cases
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


def run_gate(data_root: Path) -> dict[str, Any]:
    freeze = verify_freeze()
    if freeze["status"] != "pass":
        raise RuntimeError(f"Tail-robustness freeze failed: {freeze}")
    external_prerequisites = verify_external_prerequisites(data_root)
    if external_prerequisites["status"] != "pass":
        raise RuntimeError(
            f"Tail-robustness external prerequisites failed: {external_prerequisites}"
        )
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    parent_plan = load_yaml(root / "config/pilot1.yaml")
    target_config = load_pilot_config(root / "config/target.yaml")
    initial_threshold_record = json.loads(
        (root / INITIAL_THRESHOLD_PATH).read_text(encoding="utf-8")
    )
    initial_threshold = float(initial_threshold_record["value_delta_chi2"])
    contamination = config["contamination_model"]
    probability = float(contamination["contaminated_coordinate_probability"])
    multiplier = float(contamination["contaminated_standard_deviation_multiplier"])
    orders = build_null_orders(config)
    recovery_order = build_recovery_order(config)

    log_path = data_root / "run_records/pilot1/tail-robustness-v0.1.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import pint.logging

    pint.logging.setup(
        level="INFO", sink=log_path, usecolors=False, capturewarnings=True, removeprior=True
    )
    start = time.perf_counter()
    release_model, release_toas = _load_release(data_root)
    from pint.fitter import WidebandDownhillFitter, WidebandTOAFitter
    from pint.residuals import WidebandTOAResiduals

    fitter = WidebandTOAFitter(release_toas, release_model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(release_toas.table["tdbld"].data, dtype=float)
    frequencies, grid = build_search_frequency_grid(
        times,
        float(parent_plan["candidate_eligibility"]["search_period_minimum_days"]),
        float(parent_plan["candidate_eligibility"]["search_period_maximum_days"]),
    )
    epoch = float(parent_plan["injections"]["reference_epoch_mjd_tdb"])
    scanner = prepare_covariance_gls_scanner(covariance, design, times, frequencies, epoch)
    factor = scanner.covariance_cholesky
    localization = observed_nonperiodic_localization(
        release_model, release_toas, covariance, scanner, config
    )

    execution_binding = hashlib.sha256(
        (
            hash_file(root / "src/pulsar_pilot/tail_robustness.py", "sha256")
            + ":"
            + freeze["freeze_sha256"]
        ).encode()
    ).hexdigest()
    output_root = data_root / "derived/pilot1/tail-robustness-v0.1"

    calibration_ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/tail-robustness-calibration-v0.1-ledger.json",
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
        case_path = output_root / "calibration" / f"{sequence:04d}-{case['case_id']}.json"
        if case["case_id"] in calibration_state["completed_cases"]:
            calibration_records.append(json.loads(case_path.read_text(encoding="utf-8")))
            continue
        scan = scanner.scan(noise)
        record = {
            "schema_version": 1,
            "gate_id": GATE_ID,
            "case": case,
            "contaminated_coordinate_count": contaminated_count,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
        }
        _write_case(case_path, record, calibration_ledger, data_root)
        calibration_records.append(record)

    contamination_threshold = conservative_nearest_rank(
        np.asarray(
            [record["trigger"]["trigger_statistic"] for record in calibration_records]
        ),
        float(config["nulls"]["threshold_quantile"]),
    )
    robust_threshold = max(initial_threshold, contamination_threshold)

    evaluation_ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/tail-robustness-evaluation-v0.1-ledger.json",
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
        case_path = output_root / "evaluation" / f"{sequence:04d}-{case['case_id']}.json"
        if case["case_id"] in evaluation_state["completed_cases"]:
            evaluation_records.append(json.loads(case_path.read_text(encoding="utf-8")))
            continue
        scan = scanner.scan(noise)
        statistic = float(scan["trigger_statistic"])
        record = {
            "schema_version": 1,
            "gate_id": GATE_ID,
            "case": case,
            "contaminated_coordinate_count": contaminated_count,
            "initial_threshold_triggered": statistic > initial_threshold,
            "robust_threshold_triggered": statistic > robust_threshold,
            "robust_threshold_delta_chi2": robust_threshold,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
        }
        _write_case(case_path, record, evaluation_ledger, data_root)
        evaluation_records.append(record)

    robust_false_positives = sum(
        bool(record["robust_threshold_triggered"]) for record in evaluation_records
    )
    initial_false_positives = sum(
        bool(record["initial_threshold_triggered"]) for record in evaluation_records
    )
    robust_interval = wilson_interval_95(robust_false_positives, len(evaluation_records))
    initial_interval = wilson_interval_95(initial_false_positives, len(evaluation_records))

    recovery_ledger = ResumableArtifactLedger(
        data_root / "run_records/pilot1/tail-robustness-recovery-v0.1-ledger.json",
        freeze["inventory_sha256"]["recovery"],
        execution_binding,
    )
    recovery_state = recovery_ledger.load()
    recovery_records: list[dict[str, Any]] = []
    independent_bin = 1.0 / float(np.ptp(times))
    toa_count = len(release_toas)
    for sequence, case in enumerate(recovery_order, 1):
        case_path = output_root / "recovery" / f"{sequence:04d}-{case['case_id']}.json"
        if case["case_id"] in recovery_state["completed_cases"]:
            recovery_records.append(json.loads(case_path.read_text(encoding="utf-8")))
            continue
        noise, contaminated_count = generate_contaminated_null(
            factor, np.random.default_rng(case["seed"]), probability, multiplier
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
        injected_frequency = 1.0 / float(case["period_days"])
        record: dict[str, Any] = {
            "schema_version": 1,
            "gate_id": GATE_ID,
            "case": case,
            "contaminated_coordinate_count": contaminated_count,
            "robust_threshold_delta_chi2": robust_threshold,
            "triggered": float(scan["trigger_statistic"]) > robust_threshold,
            "frequency_recovered": abs(
                float(scan["peak_frequency_per_day"]) - injected_frequency
            )
            <= independent_bin,
            "frequency_recovery_tolerance_per_day": independent_bin,
            "trigger": {key: value for key, value in scan.items() if not key.startswith("all_")},
        }
        if case["complete_refit_audit"]:
            synthetic, application = _synthetic_toas(
                release_toas, release_model, requested
            )
            ordinary = WidebandDownhillFitter(synthetic, copy.deepcopy(release_model))
            ordinary_returned = bool(
                ordinary.fit_toas(maxiter=target_config.max_fit_iterations)
            )
            ordinary_residuals = WidebandTOAResiduals(synthetic, ordinary.model)
            joint = _joint_downhill_fit(
                synthetic,
                release_model,
                injected_frequency,
                epoch,
                target_config.max_fit_iterations,
            )
            record["application"] = application
            record["ordinary_fit"] = {
                "returned_converged": ordinary_returned,
                "fitter_converged": bool(ordinary.converged),
                "chi2": float(ordinary_residuals.chi2),
            }
            record["joint_fit"] = {
                key: value
                for key, value in joint.items()
                if key not in {"fitter", "model", "residuals"}
            }
            if case["full_covariance_audit"]:
                audit = _joint_full_covariance_fit(
                    synthetic,
                    release_model,
                    injected_frequency,
                    epoch,
                    target_config.max_fit_iterations,
                )
                record["full_covariance_audit"] = {
                    key: value
                    for key, value in audit.items()
                    if key not in {"fitter", "model", "residuals"}
                }
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
        _write_case(case_path, record, recovery_ledger, data_root)
        recovery_records.append(record)

    surface = _recovery_surface(recovery_records)
    detected = [record for record in recovery_records if record["triggered"]]
    frequency_recovery_rate = (
        sum(bool(record["frequency_recovered"]) for record in detected) / len(detected)
        if detected
        else 0.0
    )
    refit_records = [record for record in recovery_records if "ordinary_fit" in record]
    full_audits = [record for record in recovery_records if "audit_comparison" in record]
    hard = config["hard_benchmarks"]
    refit_failures = sum(
        not (
            record["ordinary_fit"]["returned_converged"]
            and record["ordinary_fit"]["fitter_converged"]
            and record["joint_fit"]["returned_converged"]
            and record["joint_fit"]["fitter_converged"]
        )
        for record in refit_records
    )
    audit_failures = sum(
        float(record["audit_comparison"]["amplitude_difference_microseconds"])
        > float(hard["full_covariance_amplitude_difference_maximum_microseconds"])
        or float(record["audit_comparison"]["phase_difference_radians"])
        > float(hard["full_covariance_phase_difference_maximum_radians"])
        or float(record["audit_comparison"]["chi2_difference"])
        > float(hard["full_covariance_chi2_difference_maximum"])
        for record in full_audits
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
        "recovery": recovery_ledger.verify(data_root),
    }
    null_diagnostics = {
        "calibration": null_ensemble_diagnostics(
            np.asarray(calibration_samples), factor
        ),
        "evaluation": null_ensemble_diagnostics(np.asarray(evaluation_samples), factor),
    }
    criteria = {
        "freeze_verified": freeze["status"] == "pass",
        "external_prerequisites_verified": external_prerequisites["status"] == "pass",
        "observed_nonperiodic_localization_complete": localization["status"] == "complete",
        "exactly_1000_contamination_calibration_nulls": len(calibration_records) == 1000,
        "exactly_500_disjoint_contamination_evaluation_nulls": len(evaluation_records) == 500,
        "robust_threshold_not_below_initial_v0p1": robust_threshold >= initial_threshold,
        "contamination_evaluation_false_positive_rate": robust_interval["proportion"]
        <= float(hard["evaluation_false_positive_rate_maximum"]),
        "contamination_evaluation_false_positive_upper_95": robust_interval["upper"]
        <= float(hard["evaluation_false_positive_rate_upper_95_maximum"]),
        "exactly_160_contaminated_recovery_cases": len(recovery_records) == 160,
        "frequency_recovery": frequency_recovery_rate
        >= float(hard["injected_frequency_recovery_rate_minimum"]),
        "monotonic_recovery": surface["periods_with_monotonic_recovery_fraction"]
        >= int(hard["minimum_periods_with_monotonic_detection_fraction"]),
        "sensitivity_bracketing": surface[
            "periods_with_bracketed_50_and_90_percent_sensitivity"
        ]
        >= int(hard["minimum_periods_with_bracketed_50_and_90_percent_sensitivity"]),
        "exactly_16_complete_refit_audits": len(refit_records) == 16,
        "complete_refit_audits": refit_failures
        <= int(hard["complete_refit_failures_maximum"]),
        "exactly_4_full_covariance_audits": len(full_audits) == 4,
        "independent_full_covariance_audits": audit_failures
        <= int(hard["independent_full_covariance_audit_failures_maximum"]),
        "warning_hygiene": warnings["status"] == "pass",
        "artifact_ledgers_verified": all(item["status"] == "pass" for item in ledgers.values()),
        "runtime_under_cap": elapsed_hours <= float(hard["incremental_wall_hours_maximum"]),
        "peak_memory_under_cap": _peak_rss_gib() <= float(hard["peak_memory_gib"]),
        "storage_under_cap": _directory_size_gib(data_root)
        <= float(hard["complete_data_root_gib"]),
        "observed_residual_periodic_search_not_executed": True,
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
        "external_prerequisites": external_prerequisites,
        "execution_binding_sha256": execution_binding,
        "contamination_model": {
            **contamination,
            "verified_theoretical_excess_kurtosis": theoretical_mixture_excess_kurtosis(
                probability, multiplier
            ),
        },
        "observed_nonperiodic_localization": localization,
        "thresholds": {
            "initial_v0p1_delta_chi2": initial_threshold,
            "contamination_calibration_delta_chi2": contamination_threshold,
            "robust_locked_delta_chi2": robust_threshold,
        },
        "contamination_evaluation": {
            "robust_threshold_false_positives": robust_false_positives,
            "robust_threshold_interval": robust_interval,
            "initial_threshold_false_positives_context_only": initial_false_positives,
            "initial_threshold_interval_context_only": initial_interval,
        },
        "recovery": {
            "surface": surface,
            "frequency_recovery_rate_among_triggers": frequency_recovery_rate,
            "detected_count": len(detected),
            "complete_refit_audit_count": len(refit_records),
            "complete_refit_failures": refit_failures,
            "full_covariance_audit_count": len(full_audits),
            "full_covariance_audit_failures": audit_failures,
            "audit_comparisons": [record["audit_comparison"] for record in full_audits],
        },
        "synthetic_frequency_grid": grid,
        "null_diagnostics": null_diagnostics,
        "ledgers": ledgers,
        "warnings": warnings,
        "incremental_wall_hours": elapsed_hours,
        "peak_memory_gib": _peak_rss_gib(),
        "complete_data_root_gib": _directory_size_gib(data_root),
        "scorecard": scorecard,
        "observed_residual_periodic_search_executed": False,
        "next_gate": (
            "separately_reviewed_one_shot_observed_residual_search_freeze"
            if scorecard["overall"] == "PASS"
            else "detector_or_threshold_rebaseline"
        ),
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    summary_path = data_root / "run_records/pilot1/tail-robustness-v0.1-summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["external_record"] = {
        "logical_path": logical_path(summary_path, data_root),
        "bytes": summary_path.stat().st_size,
        "sha256": hash_file(summary_path, "sha256"),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot1-tail-robustness")
    parser.add_argument("command", choices=("plan", "verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = repository_root()
    if args.command == "plan":
        config = load_yaml(root / CONFIG_PATH)
        result = {
            "schema_version": 1,
            "gate_id": GATE_ID,
            "status": "planned",
            "inventory_sha256": inventory_hashes(config),
            "null_counts": {
                key: len(value) for key, value in build_null_orders(config).items()
            },
            "recovery_count": len(build_recovery_order(config)),
            "observed_residual_periodic_search_authorized": False,
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
