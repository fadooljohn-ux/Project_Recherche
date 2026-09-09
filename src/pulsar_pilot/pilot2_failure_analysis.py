from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import beta, betabinom, binom, ks_2samp

from .paths import configured_data_root, require_initialized_data_root


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clopper_pearson(successes: int, trials: int) -> dict[str, float]:
    return {
        "lower": 0.0
        if successes == 0
        else float(beta.ppf(0.025, successes, trials - successes + 1)),
        "upper": 1.0
        if successes == trials
        else float(beta.ppf(0.975, successes + 1, trials - successes)),
    }


def analyze_statistics(
    calibration: list[float], sealed: list[float], threshold: float
) -> dict[str, Any]:
    calibration_values = np.asarray(calibration, dtype=float)
    sealed_values = np.asarray(sealed, dtype=float)
    if len(calibration_values) != 1000 or len(sealed_values) != 500:
        raise RuntimeError("Failure analysis requires the exact 1,000/500 frozen split")
    rank = math.ceil(0.99 * len(calibration_values))
    ordered = np.sort(calibration_values)
    if not math.isclose(float(ordered[rank - 1]), threshold, rel_tol=0, abs_tol=1e-12):
        raise RuntimeError("Locked threshold is not the frozen nearest-rank statistic")
    calibration_exceed = calibration_values[calibration_values > threshold]
    sealed_exceed = sealed_values[sealed_values > threshold]
    ks = ks_2samp(calibration_values, sealed_values, method="exact")
    beta_tail_a = len(calibration_values) + 1 - rank
    beta_tail_b = rank
    pass_cutoff = 5
    quantiles = [0.5, 0.9, 0.95, 0.99]
    return {
        "locked_threshold_reproduced": True,
        "calibration_nearest_rank": rank,
        "calibration_strict_exceedances": len(calibration_exceed),
        "sealed_strict_exceedances": len(sealed_exceed),
        "sealed_false_positive_rate": float(len(sealed_exceed) / len(sealed_values)),
        "sealed_clopper_pearson_95": _clopper_pearson(len(sealed_exceed), len(sealed_values)),
        "two_sample_ks": {
            "statistic": float(ks.statistic),
            "p_value": float(ks.pvalue),
            "method": "exact",
        },
        "distribution_quantiles": {
            "probabilities": quantiles,
            "calibration": [float(value) for value in np.quantile(calibration_values, quantiles)],
            "sealed": [float(value) for value in np.quantile(sealed_values, quantiles)],
        },
        "sealed_exceedance_margins_above_lock": sorted(
            float(value - threshold) for value in sealed_exceed
        ),
        "calibration_exceedance_margins_above_lock": sorted(
            float(value - threshold) for value in calibration_exceed
        ),
        "fixed_p_0p01_diagnostics": {
            "probability_of_7_or_more_in_500": float(binom.sf(6, 500, 0.01)),
            "probability_of_passing_at_most_5_in_500": float(binom.cdf(pass_cutoff, 500, 0.01)),
            "false_rejection_probability_at_true_p_0p01": float(binom.sf(pass_cutoff, 500, 0.01)),
        },
        "order_statistic_predictive_diagnostics": {
            "tail_probability_distribution": {
                "family": "beta",
                "alpha": beta_tail_a,
                "beta": beta_tail_b,
                "mean": beta_tail_a / (beta_tail_a + beta_tail_b),
                "central_95": [
                    float(beta.ppf(0.025, beta_tail_a, beta_tail_b)),
                    float(beta.ppf(0.975, beta_tail_a, beta_tail_b)),
                ],
            },
            "predictive_probability_of_7_or_more_in_500": float(
                betabinom.sf(6, 500, beta_tail_a, beta_tail_b)
            ),
            "predictive_probability_of_passing_at_most_5_in_500": float(
                betabinom.cdf(pass_cutoff, 500, beta_tail_a, beta_tail_b)
            ),
        },
    }


def analyze_frozen_records(data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(data_root)
    ledger_path = data_root / "run_records/pilot2/calibration-v0.2-ledger.json"
    lock_path = data_root / "run_records/pilot2/calibration-threshold-lock-v0.2.json"
    sealed_result_path = data_root / "run_records/pilot2/sealed-gaussian-evaluation-v0.2.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    before: dict[str, dict[str, Any]] = {}
    calibration_records: list[dict[str, Any]] = []
    sealed_records: list[dict[str, Any]] = []
    for case_id, item in sorted(ledger["completed_cases"].items()):
        path = data_root / item["logical_path"]
        before[case_id] = {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
        }
        if before[case_id]["sha256"] != item["sha256"] or before[case_id]["bytes"] != item["bytes"]:
            raise RuntimeError(f"Frozen case record integrity failure: {case_id}")
        record = json.loads(path.read_text(encoding="utf-8"))
        family = record["case"]["family"]
        if family == "calibration":
            calibration_records.append(record)
        elif family == "sealed_evaluation":
            sealed_records.append(record)
        else:
            raise RuntimeError(f"Unexpected completed family: {family}")
    calibration_ids = {item["case"]["case_id"] for item in calibration_records}
    sealed_ids = {item["case"]["case_id"] for item in sealed_records}
    calibration_seeds = {int(item["case"]["seed"]) for item in calibration_records}
    sealed_seeds = {int(item["case"]["seed"]) for item in sealed_records}
    statistics = analyze_statistics(
        [float(item["global_maximum_delta_chi2"]) for item in calibration_records],
        [float(item["global_maximum_delta_chi2"]) for item in sealed_records],
        float(lock["value_delta_chi2"]),
    )
    sealed_exceedance_periods = sorted(
        float(item["peak_period_days"])
        for item in sealed_records
        if float(item["global_maximum_delta_chi2"]) > float(lock["value_delta_chi2"])
    )
    after = {
        case_id: {
            "sha256": _sha256(data_root / ledger["completed_cases"][case_id]["logical_path"]),
            "bytes": (data_root / ledger["completed_cases"][case_id]["logical_path"])
            .stat()
            .st_size,
            "mtime_ns": (data_root / ledger["completed_cases"][case_id]["logical_path"])
            .stat()
            .st_mtime_ns,
        }
        for case_id in before
    }
    return {
        "schema_version": 1,
        "analysis_id": "pilot2-b1937-sealed-gaussian-deterministic-failure-analysis-v0.2",
        "status": "pass",
        "mode": "read_only_no_new_random_draws_fits_or_scans",
        "integrity": {
            "case_count": len(before),
            "calibration_case_count": len(calibration_records),
            "sealed_case_count": len(sealed_records),
            "case_ids_disjoint": calibration_ids.isdisjoint(sealed_ids),
            "seeds_disjoint": calibration_seeds.isdisjoint(sealed_seeds),
            "all_case_hashes_sizes_and_mtimes_unchanged_during_analysis": before == after,
            "ledger_sha256": _sha256(ledger_path),
            "threshold_lock_sha256": _sha256(lock_path),
            "sealed_result_sha256": _sha256(sealed_result_path),
        },
        "statistics": statistics,
        "sealed_exceedance_peak_periods_days": sealed_exceedance_periods,
        "interpretation_constraints": {
            "threshold_retuned": False,
            "sealed_cases_reused_for_calibration": False,
            "new_random_draws_generated": 0,
            "new_model_fits_executed": 0,
            "new_periodic_scans_executed": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-failure-analysis")
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    result = analyze_frozen_records(configured_data_root(args.data_root))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
