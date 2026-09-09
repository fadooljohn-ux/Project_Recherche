from __future__ import annotations

import copy
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import load_yaml
from .injection_integrity import toa_adjustment_gate_value
from .paths import repository_root, require_initialized_data_root
from .pilot2_calibration_design import build_inventory
from .pilot2_calibration_revision_design import build_revision_inventory
from .provenance import hash_file

CONFIG_PATH = "config/pilot2_injection_remediation_v0.2.2.yaml"
BASE_CONFIG_PATH = "config/pilot2_calibration_v0.2.1.yaml"
FREEZE_PATH = "protocol/PILOT2_INJECTION_REMEDIATION_FREEZE_v0.2.2.json"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _case_seed(base_seed: int, case_id: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _nearest_rank(values: list[float], quantile: float) -> float:
    if not values:
        return math.inf
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    left = 0
    while left < len(order):
        right = left + 1
        while right < len(order) and values[order[right]] == values[order[left]]:
            right += 1
        rank = (left + right - 1) / 2.0 + 1.0
        for position in range(left, right):
            result[order[position]] = rank
        left = right
    return result


def _pearson(left: list[float], right: list[float]) -> float:
    left_mean = statistics.mean(left)
    right_mean = statistics.mean(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right, strict=True)
    )
    denominator = math.sqrt(
        sum((value - left_mean) ** 2 for value in left)
        * sum((value - right_mean) ** 2 for value in right)
    )
    return numerator / denominator if denominator else math.nan


def _spearman(left: list[float], right: list[float]) -> float:
    return _pearson(_ranks(left), _ranks(right))


def build_remediation_inventory(
    base_config: dict[str, Any], remediation: dict[str, Any]
) -> dict[str, Any]:
    prospective = remediation["prospective_inventory"]
    prefix = str(prospective["case_id_prefix"])
    overlay = copy.deepcopy(base_config)
    overlay["plan_id"] = remediation["plan_id"]
    overlay["authority"]["execution_authorized"] = False
    overlay["injections"]["main_base_seed"] = int(prospective["main_base_seed"])
    overlay["injections"]["annual_identifiability_map"]["base_seed"] = int(
        prospective["annual_base_seed"]
    )
    overlay["injections"]["search_boundary_map"]["base_seed"] = int(
        prospective["boundary_base_seed"]
    )
    inherited = build_inventory(overlay)["injection_cases"]
    family_seed = {
        "main": int(prospective["main_base_seed"]),
        "annual": int(prospective["annual_base_seed"]),
        "boundary": int(prospective["boundary_base_seed"]),
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in inherited:
        item = copy.deepcopy(source)
        item["case_id"] = item["case_id"].replace("p2-", f"{prefix}-", 1)
        item["seed"] = _case_seed(family_seed[item["family"]], item["case_id"])
        item["stratum"] = "detection_recovery"
        grouped[item["family"]].append(item)
    phase_reference: list[dict[str, Any]] = []
    reference = remediation["phase_reference_controls"]
    for period_index, cell in enumerate(reference["period_amplitudes"]):
        for phase_index, phase in enumerate(reference["phases_radians"]):
            for noise_index in range(
                int(reference["covariance_noise_realizations_per_phase"])
            ):
                case_id = (
                    f"{prefix}-inj-phase-reference-p{period_index:02d}"
                    f"-h{phase_index:02d}-n{noise_index:02d}"
                )
                phase_reference.append(
                    {
                        "case_id": case_id,
                        "family": "phase_reference",
                        "stratum": "phase_accuracy",
                        "period_days": float(cell["period_days"]),
                        "amplitude_microseconds": float(
                            cell["amplitude_microseconds"]
                        ),
                        "phase_radians": float(phase),
                        "noise_realization_index": noise_index,
                        "seed": _case_seed(
                            int(prospective["phase_reference_base_seed"]), case_id
                        ),
                    }
                )
    cases = grouped["main"] + phase_reference + grouped["annual"] + grouped["boundary"]
    audit_count = math.ceil(
        len(cases) * float(prospective["solver_audit_fraction"])
    )
    ranked = sorted(
        cases, key=lambda item: hashlib.sha256(item["case_id"].encode()).hexdigest()
    )
    payload = {
        "schema_version": 1,
        "plan_id": remediation["plan_id"],
        "execution_authorized": False,
        "cases": cases,
        "solver_audit_case_ids": [item["case_id"] for item in ranked[:audit_count]],
    }
    payload["inventory_sha256"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
    return payload


def validate_remediation_design(
    base_config: dict[str, Any],
    remediation: dict[str, Any],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    root = repository_root()
    failures: list[str] = []
    if remediation.get("status") != "remediation_design_execution_not_authorized":
        failures.append("Remediation design status is invalid")
    if any(bool(value) for value in remediation["authority"].values()):
        failures.append("Remediation design contains unauthorized authority")
    for binding in remediation["source_bindings"].values():
        logical_path = str(binding["logical_path"])
        if logical_path.startswith("run_records/"):
            continue
        path = root / logical_path
        if not path.is_file() or hash_file(path, "sha256") != binding["sha256"]:
            failures.append(f"Repository source binding mismatch: {logical_path}")
    cases = inventory["cases"]
    counts = {
        family: sum(item["family"] == family for item in cases)
        for family in ("main", "phase_reference", "annual", "boundary")
    }
    expected = {
        "main": 240,
        "phase_reference": 60,
        "annual": 28,
        "boundary": 16,
    }
    if counts != expected or len(cases) != 344:
        failures.append(f"Prospective inventory counts differ: {counts}")
    if len(inventory["solver_audit_case_ids"]) != 35:
        failures.append("Prospective solver-audit count differs")
    case_ids = {item["case_id"] for item in cases}
    seeds = {int(item["seed"]) for item in cases}
    if len(case_ids) != len(cases) or len(seeds) != len(cases):
        failures.append("Prospective case IDs or seeds are not unique")
    historical = build_revision_inventory(base_config)
    historical_ids = {item["case_id"] for item in historical["injection_cases"]}
    historical_seeds = {int(item["seed"]) for item in historical["injection_cases"]}
    if case_ids & historical_ids:
        failures.append("Prospective case IDs overlap v0.2.1")
    if seeds & historical_seeds:
        failures.append("Prospective seeds overlap v0.2.1")
    phase = remediation["phase_reference_controls"]
    if float(phase["phase_error_p90_maximum_radians"]) != float(
        base_config["injection_gates"]["phase_error_p90_maximum_radians"]
    ):
        failures.append("The numerical phase-accuracy limit changed")
    integrity = remediation["application_integrity"]
    if float(integrity["toa_adjustment_maximum_microseconds"]) != float(
        base_config["injections"]["maximum_toa_adjustment_error_microseconds"]
    ):
        failures.append("The numerical TOA-adjustment limit changed")
    projection = remediation["resource_projection"]
    projected_hours = (
        (
            int(projection["injection_scans"])
            * float(projection["measured_scan_seconds_each"])
            + int(projection["primary_injection_fits"])
            * float(projection["measured_primary_fit_seconds_each"])
            + int(projection["explicit_full_covariance_audits"])
            * float(projection["measured_audit_seconds_each"])
            + float(projection["measured_setup_seconds"])
        )
        * float(projection["contingency_multiplier"])
        / 3600.0
    )
    if not math.isclose(
        projected_hours,
        float(projection["projected_wall_hours_with_contingency"]),
        abs_tol=1e-15,
    ):
        failures.append("Resource projection is inconsistent")
    if projected_hours > float(
        remediation["resource_caps"]["macbook_wall_hours_maximum"]
    ):
        failures.append("Resource projection exceeds the MacBook cap")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "case_counts": counts,
        "total_cases": len(cases),
        "solver_audit_cases": len(inventory["solver_audit_case_ids"]),
        "case_ids_disjoint_from_v0.2.1": not bool(case_ids & historical_ids),
        "seeds_disjoint_from_v0.2.1": not bool(seeds & historical_seeds),
        "phase_limit_unchanged": not any(
            failure == "The numerical phase-accuracy limit changed"
            for failure in failures
        ),
        "toa_limit_unchanged": not any(
            failure == "The numerical TOA-adjustment limit changed"
            for failure in failures
        ),
        "projected_wall_hours_with_contingency": projected_hours,
        "inventory_sha256": inventory["inventory_sha256"],
        "execution_authorized": False,
    }


def load_verified_v021_injection_records(data_root: Path) -> list[dict[str, Any]]:
    require_initialized_data_root(data_root)
    root = repository_root()
    remediation = load_yaml(root / CONFIG_PATH)
    bindings = remediation["source_bindings"]
    for key in ("terminal_result", "final_ledger", "threshold_lock"):
        binding = bindings[key]
        path = data_root / str(binding["logical_path"])
        if not path.is_file() or hash_file(path, "sha256") != binding["sha256"]:
            raise RuntimeError(f"Immutable v0.2.1 source mismatch: {key}")
    ledger_path = data_root / str(bindings["final_ledger"]["logical_path"])
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if ledger["stage_status"].get("injection_recovery_and_annual_map") != "fail":
        raise RuntimeError("v0.2.1 injection stage is not the frozen failure")
    if ledger.get("hard_stop", {}).get("reason") != "stage_gate_failure":
        raise RuntimeError("v0.2.1 hard stop is absent or changed")
    entries = [
        item
        for item in ledger["completed_cases"].values()
        if item["stage"] == "injection_recovery_and_annual_map"
    ]
    if len(entries) != 284:
        raise RuntimeError("v0.2.1 injection artifact count differs")
    records: list[dict[str, Any]] = []
    for entry in sorted(entries, key=lambda item: item["logical_path"]):
        path = data_root / entry["logical_path"]
        if not path.is_file() or path.stat().st_size != int(entry["bytes"]):
            raise RuntimeError(f"v0.2.1 injection artifact missing: {entry['logical_path']}")
        if hash_file(path, "sha256") != entry["sha256"]:
            raise RuntimeError(f"v0.2.1 injection artifact mismatch: {entry['logical_path']}")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["observed_residual_vector_used"] is not False:
            raise RuntimeError("A source record crosses the observed-residual boundary")
        if record["observed_periodic_scan_executed"] is not False:
            raise RuntimeError("A source record crosses the observed-search boundary")
        records.append(record)
    return records


def analyze_v021_phase_failure(records: list[dict[str, Any]]) -> dict[str, Any]:
    main_all = [item for item in records if item["family"] == "main"]
    main = [item for item in main_all if bool(item["triggered"])]
    phase_errors = [abs(float(item["phase_error_radians"])) for item in main]
    if len(main_all) != 240 or not main:
        raise ValueError("Phase analysis requires the complete v0.2.1 main inventory")
    factors = {
        "amplitude_microseconds": [float(item["amplitude_microseconds"]) for item in main],
        "trigger_statistic": [float(item["global_maximum_delta_chi2"]) for item in main],
        "amplitude_bias_fraction": [
            abs(float(item["amplitude_bias_fraction"])) for item in main
        ],
        "ordinary_absorption_fraction": [
            float(item["ordinary_absorption_fraction"]) for item in main
        ],
        "period_days": [float(item["period_days"]) for item in main],
    }
    correlations = {
        name: _spearman(values, phase_errors) for name, values in factors.items()
    }
    ordered = sorted(main, key=lambda item: float(item["global_maximum_delta_chi2"]))
    quartiles: list[dict[str, Any]] = []
    for index in range(4):
        group = ordered[index * len(ordered) // 4 : (index + 1) * len(ordered) // 4]
        errors = [abs(float(item["phase_error_radians"])) for item in group]
        quartiles.append(
            {
                "quartile": index + 1,
                "count": len(group),
                "trigger_statistic_minimum": float(group[0]["global_maximum_delta_chi2"]),
                "trigger_statistic_maximum": float(group[-1]["global_maximum_delta_chi2"]),
                "median_phase_error_radians": statistics.median(errors),
                "p90_phase_error_radians": _nearest_rank(errors, 0.9),
                "fraction_over_0p1_radians": sum(value > 0.1 for value in errors)
                / len(errors),
            }
        )
    strongest: list[dict[str, Any]] = []
    for period in sorted({float(item["period_days"]) for item in main_all}):
        period_records = [
            item for item in main_all if float(item["period_days"]) == period
        ]
        amplitude = max(float(item["amplitude_microseconds"]) for item in period_records)
        controls = [
            item
            for item in period_records
            if float(item["amplitude_microseconds"]) == amplitude
        ]
        errors = [abs(float(item["phase_error_radians"])) for item in controls]
        strongest.append(
            {
                "period_days": period,
                "amplitude_microseconds": amplitude,
                "count": len(controls),
                "triggered": sum(bool(item["triggered"]) for item in controls),
                "median_phase_error_radians": statistics.median(errors),
                "p90_phase_error_radians": _nearest_rank(errors, 0.9),
                "cases_over_0p1_radians": sum(value > 0.1 for value in errors),
            }
        )
    phase_groups: list[dict[str, Any]] = []
    for phase in sorted({float(item["phase_radians"]) for item in main}):
        group = [item for item in main if float(item["phase_radians"]) == phase]
        errors = [abs(float(item["phase_error_radians"])) for item in group]
        phase_groups.append(
            {
                "injected_phase_radians": phase,
                "count": len(group),
                "median_phase_error_radians": statistics.median(errors),
                "p90_phase_error_radians": _nearest_rank(errors, 0.9),
                "fraction_over_0p1_radians": sum(value > 0.1 for value in errors)
                / len(errors),
            }
        )
    strong_errors = [
        abs(float(item["phase_error_radians"]))
        for item in main_all
        if float(item["amplitude_microseconds"])
        == max(
            float(candidate["amplitude_microseconds"])
            for candidate in main_all
            if float(candidate["period_days"]) == float(item["period_days"])
        )
    ]
    return {
        "schema_version": 1,
        "analysis_id": "pilot2-b1937-v0.2.1-record-only-phase-failure-analysis",
        "operation": "verified_json_artifact_analysis_only",
        "science_cases_executed": 0,
        "observed_residual_data_loaded": False,
        "triggered_main_cases": len(main),
        "phase_error": {
            "median_radians": statistics.median(phase_errors),
            "p90_radians": _nearest_rank(phase_errors, 0.9),
            "maximum_radians": max(phase_errors),
            "cases_over_0p1_radians": sum(value > 0.1 for value in phase_errors),
        },
        "spearman_correlations_with_absolute_phase_error": correlations,
        "trigger_strength_quartiles": quartiles,
        "strongest_controls_by_period": strongest,
        "strongest_controls": {
            "count": len(strong_errors),
            "p90_phase_error_radians": _nearest_rank(strong_errors, 0.9),
            "cases_over_0p1_radians": sum(value > 0.1 for value in strong_errors),
        },
        "injected_phase_groups": phase_groups,
        "causal_assessment": {
            "primary": "phase_precision_degrades_as_detection_strength_decreases",
            "secondary": "target_specific_covariance_and_cadence_limit_some_strong_controls",
            "not_supported": [
                "fit_nonconvergence",
                "solver_disagreement",
                "frequency_recovery_failure",
                "ordinary_model_absorption_as_dominant_driver",
                "single_injected_phase_orientation",
                "period_alone_as_dominant_driver",
            ],
            "unresolved": "signed_phase_bias_not_recoverable_from_retained_case_schema",
        },
        "design_disposition": {
            "v0.2.1_failure_preserved": True,
            "retroactive_regrade_authorized": False,
            "prospective_phase_accuracy_limit_radians": 0.1,
            "prospective_phase_accuracy_stratum": "dedicated_high_information_controls",
            "all_triggered_main_phase_role": "diagnostic_not_hard_gate",
        },
    }


def grade_remediation_integrity(
    records: list[dict[str, Any]], remediation: dict[str, Any]
) -> dict[str, Any]:
    failures: list[str] = []
    adjustment_values: list[float] = []
    for record in records:
        try:
            adjustment_values.append(toa_adjustment_gate_value(record))
        except (TypeError, ValueError) as error:
            failures.append(str(error))
    phase_reference = [item for item in records if item["family"] == "phase_reference"]
    phase_errors = [
        abs(float(item["phase_error_radians"])) for item in phase_reference
    ]
    reference_config = remediation["phase_reference_controls"]
    if len(phase_reference) != 60:
        failures.append("Phase-reference case count differs")
    if phase_reference and not all(bool(item["triggered"]) for item in phase_reference):
        failures.append("A phase-reference control did not trigger")
    p90_phase = _nearest_rank(phase_errors, 0.9)
    if p90_phase > float(reference_config["phase_error_p90_maximum_radians"]):
        failures.append("Phase-reference p90 exceeds the unchanged limit")
    maximum_adjustment = max(adjustment_values, default=math.inf)
    if maximum_adjustment > float(
        remediation["application_integrity"]["toa_adjustment_maximum_microseconds"]
    ):
        failures.append("Canonical TOA-adjustment metric exceeds its limit")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "canonical_toa_metrics_present": len(adjustment_values) == len(records),
        "maximum_toa_adjustment_error_microseconds": maximum_adjustment,
        "phase_reference_cases": len(phase_reference),
        "phase_reference_p90_radians": p90_phase,
        "all_triggered_main_phase_role": "diagnostic_not_hard_gate",
    }


def remediation_summary() -> dict[str, Any]:
    root = repository_root()
    base = load_yaml(root / BASE_CONFIG_PATH)
    remediation = load_yaml(root / CONFIG_PATH)
    inventory = build_remediation_inventory(base, remediation)
    validation = validate_remediation_design(base, remediation, inventory)
    return {
        "schema_version": 1,
        "plan_id": remediation["plan_id"],
        "status": validation["status"],
        "execution_authorized": False,
        "observed_periodic_search_authorized": False,
        "validation": validation,
        "next_gate": remediation["next_gate"],
    }


def verify_remediation_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / FREEZE_PATH
    if not path.is_file():
        return {"status": "locked", "failures": ["Remediation freeze is absent"]}
    freeze = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_zero_case_remediation_execution_locked":
        failures.append("Remediation freeze status is invalid")
    if freeze.get("science_cases_executed_during_remediation") != 0:
        failures.append("Remediation freeze is not zero-case")
    for key in (
        "execution_authorized",
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "promotion_grade_authorized",
        "discovery_claim_authorized",
    ):
        if freeze.get(key) is not False:
            failures.append(f"Remediation freeze authority is invalid: {key}")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"Remediation freeze hash mismatch: {relative}")
    base = load_yaml(root / BASE_CONFIG_PATH)
    remediation = load_yaml(root / CONFIG_PATH)
    inventory = build_remediation_inventory(base, remediation)
    if inventory["inventory_sha256"] != freeze.get("prospective_inventory_sha256"):
        failures.append("Remediation freeze inventory mismatch")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "execution_authorized": False,
        "inventory_sha256": inventory["inventory_sha256"],
        "freeze_sha256": hash_file(path, "sha256"),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--full-inventory", action="store_true")
    args = parser.parse_args()
    root = repository_root()
    base = load_yaml(root / BASE_CONFIG_PATH)
    remediation = load_yaml(root / CONFIG_PATH)
    inventory = build_remediation_inventory(base, remediation)
    result: dict[str, Any] = {
        "remediation": remediation_summary(),
        "freeze": verify_remediation_freeze(),
    }
    if args.data_root is not None:
        records = load_verified_v021_injection_records(args.data_root)
        result["phase_failure_analysis"] = analyze_v021_phase_failure(records)
    if args.full_inventory:
        result["prospective_inventory"] = inventory
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["remediation"]["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
