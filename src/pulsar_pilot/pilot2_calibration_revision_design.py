from __future__ import annotations

import argparse
import hashlib
import json
import math
from typing import Any

from scipy.stats import binom

from .config import load_yaml
from .paths import repository_root
from .pilot1_evaluation import wilson_interval_95
from .pilot2_calibration_design import build_inventory as build_v02_inventory
from .provenance import hash_file

CONFIG_PATH = "config/pilot2_calibration_v0.2.1.yaml"
FREEZE_PATH = "protocol/PILOT2_CALIBRATION_DESIGN_FREEZE_v0.2.1.json"
V02_CONFIG_PATH = "config/pilot2_calibration_v0.2.yaml"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _case_seed(base_seed: int, case_id: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def build_revision_inventory(config: dict[str, Any]) -> dict[str, Any]:
    inventory = build_v02_inventory(config)
    prefix = str(config["case_id_prefix"])
    structured_seeds = {
        item["id"]: int(item["base_seed"])
        for item in config["structured_tail_evaluation"]["variants"]
    }
    injection_seeds = {
        "main": int(config["injections"]["main_base_seed"]),
        "annual": int(config["injections"]["annual_identifiability_map"]["base_seed"]),
        "boundary": int(config["injections"]["search_boundary_map"]["base_seed"]),
    }
    for item in inventory["gaussian_null_cases"]:
        item["case_id"] = item["case_id"].replace("p2-", f"{prefix}-", 1)
        seed_key = (
            "calibration_base_seed"
            if item["family"] == "calibration"
            else "sealed_evaluation_base_seed"
        )
        item["seed"] = _case_seed(int(config["gaussian_nulls"][seed_key]), item["case_id"])
    for item in inventory["structured_tail_cases"]:
        item["case_id"] = item["case_id"].replace("p2-", f"{prefix}-", 1)
        item["seed"] = _case_seed(structured_seeds[item["variant"]], item["case_id"])
    for item in inventory["injection_cases"]:
        item["case_id"] = item["case_id"].replace("p2-", f"{prefix}-", 1)
        item["seed"] = _case_seed(injection_seeds[item["family"]], item["case_id"])
    ranked = sorted(
        inventory["injection_cases"],
        key=lambda item: hashlib.sha256(item["case_id"].encode()).hexdigest(),
    )
    audit_count = math.ceil(len(ranked) * float(config["solver_audit"]["deterministic_fraction"]))
    inventory["solver_audit_case_ids"] = [item["case_id"] for item in ranked[:audit_count]]
    inventory["inventory_sha256"] = hashlib.sha256(
        _canonical_json(
            {key: value for key, value in inventory.items() if key != "inventory_sha256"}
        )
    ).hexdigest()
    return inventory


def validate_revision(config: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    root = repository_root()
    prior = build_v02_inventory(load_yaml(root / V02_CONFIG_PATH))
    all_cases = (
        inventory["gaussian_null_cases"]
        + inventory["structured_tail_cases"]
        + inventory["injection_cases"]
    )
    prior_cases = (
        prior["gaussian_null_cases"] + prior["structured_tail_cases"] + prior["injection_cases"]
    )
    counts = {
        "gaussian_calibration": sum(
            item["family"] == "calibration" for item in inventory["gaussian_null_cases"]
        ),
        "gaussian_sealed": sum(
            item["family"] == "sealed_evaluation" for item in inventory["gaussian_null_cases"]
        ),
        "structured": len(inventory["structured_tail_cases"]),
        "injections": len(inventory["injection_cases"]),
        "audits": len(inventory["solver_audit_case_ids"]),
    }
    expected = {
        "gaussian_calibration": 5000,
        "gaussian_sealed": 2000,
        "structured": 3000,
        "injections": 284,
        "audits": 29,
    }
    if counts != expected:
        failures.append(f"Revision counts differ: {counts}")
    if config["status"] != "frozen_revision_design_execution_not_authorized":
        failures.append("Revision design status is invalid")
    if any(
        config["authority"][key]
        for key in (
            "execution_authorized",
            "observed_residual_access_authorized",
            "observed_periodic_search_authorized",
            "discovery_claim_authorized",
        )
    ):
        failures.append("Revision design contains unauthorized authority")
    case_ids = {item["case_id"] for item in all_cases}
    seeds = {int(item["seed"]) for item in all_cases}
    if len(case_ids) != len(all_cases) or len(seeds) != len(all_cases):
        failures.append("Revision case IDs or seeds are not unique")
    if case_ids & {item["case_id"] for item in prior_cases}:
        failures.append("Revision case IDs overlap v0.2")
    if seeds & {int(item["seed"]) for item in prior_cases}:
        failures.append("Revision seeds overlap v0.2")
    nulls = config["gaussian_nulls"]
    calibration_cases = int(nulls["calibration_cases"])
    rank = int(nulls["threshold_order_statistic_rank"])
    quantile = float(nulls["threshold_target_population_quantile"])
    confidence = float(binom.cdf(rank - 1, calibration_cases, quantile))
    if not math.isclose(confidence, float(nulls["threshold_one_sided_confidence"]), abs_tol=1e-15):
        failures.append("Threshold tolerance confidence is inconsistent")
    if binom.cdf(rank - 2, calibration_cases, quantile) >= 0.95 or confidence < 0.95:
        failures.append("Threshold rank is not the least rank meeting 95% confidence")
    sealed_cases = int(nulls["sealed_evaluation_cases"])
    maximum_fp = max(
        count
        for count in range(sealed_cases + 1)
        if wilson_interval_95(count, sealed_cases)["upper"]
        <= float(nulls["evaluation_wilson_upper_95_maximum"])
    )
    if maximum_fp != int(nulls["evaluation_maximum_false_positives"]):
        failures.append("Sealed Wilson cutoff is inconsistent")
    pass_probability = float(binom.cdf(maximum_fp, sealed_cases, 0.01))
    if not math.isclose(
        pass_probability,
        float(nulls["evaluation_pass_probability_at_true_0p01"]),
        abs_tol=1e-15,
    ):
        failures.append("Sealed pass probability is inconsistent")
    projection = config["resource_projection"]
    projected_hours = (
        (
            (
                int(projection["gaussian_null_scans"])
                + int(projection["structured_tail_scans"])
                + int(projection["injection_scans"])
            )
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
        failures.append("Revision resource projection is inconsistent")
    if projected_hours > float(config["resource_caps"]["macbook_wall_hours_maximum"]):
        failures.append("Revision exceeds MacBook wall-time cap")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "counts": counts,
        "total_unique_cases": len(all_cases),
        "case_ids_disjoint_from_v0.2": not bool(
            case_ids & {item["case_id"] for item in prior_cases}
        ),
        "seeds_disjoint_from_v0.2": not bool(seeds & {int(item["seed"]) for item in prior_cases}),
        "threshold_one_sided_confidence": confidence,
        "sealed_maximum_false_positives": maximum_fp,
        "sealed_pass_probability_at_true_0p01": pass_probability,
        "projected_wall_hours_with_contingency": projected_hours,
        "inventory_sha256": inventory["inventory_sha256"],
    }


def revision_summary(config: dict[str, Any]) -> dict[str, Any]:
    inventory = build_revision_inventory(config)
    validation = validate_revision(config, inventory)
    return {
        "schema_version": 1,
        "plan_id": config["plan_id"],
        "status": validation["status"],
        "execution_authorized": False,
        "observed_periodic_search_authorized": False,
        "inventory_sha256": inventory["inventory_sha256"],
        "validation": validation,
        "next_gate": "implementation_revision_and_separate_execution_authorization",
    }


def verify_revision_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / FREEZE_PATH
    if not path.is_file():
        return {"status": "fail", "failures": ["Revision design freeze is absent"]}
    freeze = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_revision_design_execution_locked":
        failures.append("Revision freeze status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append("Revision execution is not locked")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        file_path = root / relative
        if not file_path.is_file() or hash_file(file_path, "sha256") != expected:
            failures.append(f"Revision freeze hash mismatch: {relative}")
    config = load_yaml(root / CONFIG_PATH)
    inventory = build_revision_inventory(config)
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("Revision inventory hash mismatch")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "inventory_sha256": inventory["inventory_sha256"],
        "freeze_sha256": hash_file(path, "sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-calibration-revision-design")
    parser.add_argument("command", choices=("plan", "inventory", "verify-freeze"))
    args = parser.parse_args()
    if args.command == "verify-freeze":
        result = verify_revision_freeze()
    else:
        config = load_yaml(repository_root() / CONFIG_PATH)
        result = (
            revision_summary(config) if args.command == "plan" else build_revision_inventory(config)
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status", "pass") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
