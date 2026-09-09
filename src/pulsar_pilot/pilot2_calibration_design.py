from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .config import load_yaml
from .paths import repository_root
from .provenance import hash_file

CONFIG_PATH = "config/pilot2_calibration_v0.2.yaml"
FREEZE_PATH = "protocol/PILOT2_CALIBRATION_DESIGN_FREEZE_v0.2.json"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _case_seed(base_seed: int, case_id: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def build_inventory(config: dict[str, Any]) -> dict[str, Any]:
    gaussian: list[dict[str, Any]] = []
    nulls = config["gaussian_nulls"]
    for family, count_key, seed_key in (
        ("calibration", "calibration_cases", "calibration_base_seed"),
        ("sealed_evaluation", "sealed_evaluation_cases", "sealed_evaluation_base_seed"),
    ):
        for index in range(int(nulls[count_key])):
            case_id = f"p2-null-{family}-{index:04d}"
            gaussian.append(
                {
                    "case_id": case_id,
                    "family": family,
                    "index": index,
                    "seed": _case_seed(int(nulls[seed_key]), case_id),
                }
            )

    structured: list[dict[str, Any]] = []
    tail = config["structured_tail_evaluation"]
    for variant in tail["variants"]:
        for index in range(int(tail["cases_per_variant"])):
            case_id = f"p2-tail-{variant['id']}-{index:04d}"
            structured.append(
                {
                    "case_id": case_id,
                    "family": "structured_tail_evaluation",
                    "variant": variant["id"],
                    "index": index,
                    "seed": _case_seed(int(variant["base_seed"]), case_id),
                }
            )

    injections: list[dict[str, Any]] = []
    injection_config = config["injections"]
    phases = [float(value) for value in injection_config["phases_radians"]]
    main_noise_count = int(injection_config["covariance_noise_realizations_per_phase"])
    for period_index, ladder in enumerate(injection_config["main_period_ladders"]):
        for amplitude_index, amplitude in enumerate(ladder["amplitudes_microseconds"]):
            for phase_index, phase in enumerate(phases):
                for noise_index in range(main_noise_count):
                    case_id = (
                        f"p2-inj-main-p{period_index:02d}-a{amplitude_index:02d}"
                        f"-h{phase_index:02d}-n{noise_index:02d}"
                    )
                    injections.append(
                        {
                            "case_id": case_id,
                            "family": "main",
                            "period_days": float(ladder["period_days"]),
                            "amplitude_microseconds": float(amplitude),
                            "phase_radians": phase,
                            "noise_realization_index": noise_index,
                            "seed": _case_seed(
                                int(injection_config["main_base_seed"]), case_id
                            ),
                        }
                    )

    annual = injection_config["annual_identifiability_map"]
    for period_index, period in enumerate(annual["periods_days"]):
        for phase_index, phase in enumerate(phases):
            for noise_index in range(int(annual["noise_realizations_per_phase"])):
                case_id = (
                    f"p2-inj-annual-p{period_index:02d}-h{phase_index:02d}"
                    f"-n{noise_index:02d}"
                )
                injections.append(
                    {
                        "case_id": case_id,
                        "family": "annual",
                        "period_days": float(period),
                        "amplitude_microseconds": float(
                            annual["amplitude_microseconds"]
                        ),
                        "phase_radians": phase,
                        "noise_realization_index": noise_index,
                        "seed": _case_seed(int(annual["base_seed"]), case_id),
                    }
                )

    boundary = injection_config["search_boundary_map"]
    boundary_noise_count = int(boundary["noise_realizations_per_phase"])
    for period_index, ladder in enumerate(boundary["period_ladders"]):
        for amplitude_index, amplitude in enumerate(ladder["amplitudes_microseconds"]):
            for phase_index, phase in enumerate(phases):
                for noise_index in range(boundary_noise_count):
                    case_id = (
                        f"p2-inj-boundary-p{period_index:02d}-a{amplitude_index:02d}"
                        f"-h{phase_index:02d}-n{noise_index:02d}"
                    )
                    injections.append(
                        {
                            "case_id": case_id,
                            "family": "boundary",
                            "period_days": float(ladder["period_days"]),
                            "amplitude_microseconds": float(amplitude),
                            "phase_radians": phase,
                            "noise_realization_index": noise_index,
                            "seed": _case_seed(int(boundary["base_seed"]), case_id),
                        }
                    )

    audit_count = math.ceil(
        len(injections) * float(config["solver_audit"]["deterministic_fraction"])
    )
    ranked = sorted(
        injections,
        key=lambda item: hashlib.sha256(item["case_id"].encode()).hexdigest(),
    )
    audit_ids = [item["case_id"] for item in ranked[:audit_count]]
    payload = {
        "schema_version": 1,
        "plan_id": config["plan_id"],
        "execution_authorized": bool(config["authority"]["execution_authorized"]),
        "gaussian_null_cases": gaussian,
        "structured_tail_cases": structured,
        "injection_cases": injections,
        "solver_audit_case_ids": audit_ids,
    }
    payload["inventory_sha256"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
    return payload


def validate_design(config: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    gaussian = inventory["gaussian_null_cases"]
    structured = inventory["structured_tail_cases"]
    injections = inventory["injection_cases"]
    all_cases = gaussian + structured + injections
    if config["status"] != "frozen_design_execution_not_authorized":
        failures.append("Design status is not execution-locked")
    authority = config["authority"]
    if authority["execution_authorized"] is not False:
        failures.append("Calibration execution is authorized in a design package")
    if authority["observed_residual_access_authorized"] is not False:
        failures.append("Observed residual access is not locked")
    if authority["observed_periodic_search_authorized"] is not False:
        failures.append("Observed periodic search is not locked")
    expected_counts = {
        "gaussian": 1500,
        "structured": 3000,
        "injections": 284,
        "audits": 29,
    }
    observed_counts = {
        "gaussian": len(gaussian),
        "structured": len(structured),
        "injections": len(injections),
        "audits": len(inventory["solver_audit_case_ids"]),
    }
    if observed_counts != expected_counts:
        failures.append(f"Workload counts differ: {observed_counts}")
    case_ids = [item["case_id"] for item in all_cases]
    seeds = [int(item["seed"]) for item in all_cases]
    if len(set(case_ids)) != len(case_ids):
        failures.append("Case IDs are not unique")
    if len(set(seeds)) != len(seeds):
        failures.append("Case seeds are not unique")
    calibration_ids = {
        item["case_id"] for item in gaussian if item["family"] == "calibration"
    }
    evaluation_ids = {
        item["case_id"]
        for item in gaussian
        if item["family"] == "sealed_evaluation"
    }
    if calibration_ids & evaluation_ids:
        failures.append("Gaussian calibration and evaluation IDs overlap")
    if len(set(inventory["solver_audit_case_ids"])) != 29:
        failures.append("Solver audit IDs are not unique")
    injection_ids = {item["case_id"] for item in injections}
    if not set(inventory["solver_audit_case_ids"]).issubset(injection_ids):
        failures.append("Solver audit selection includes a non-injection case")
    projection = config["resource_projection"]
    calculated_seconds = (
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
    ) * float(projection["contingency_multiplier"])
    projected_hours = calculated_seconds / 3600.0
    if not math.isclose(
        projected_hours,
        float(projection["projected_wall_hours_with_contingency"]),
        rel_tol=0,
        abs_tol=1e-12,
    ):
        failures.append("Resource projection is not self-consistent")
    if projected_hours > float(config["resource_caps"]["macbook_wall_hours_maximum"]):
        failures.append("Projected runtime exceeds the MacBook cap")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "counts": observed_counts,
        "unique_case_ids": len(set(case_ids)),
        "unique_seeds": len(set(seeds)),
        "inventory_sha256": inventory["inventory_sha256"],
        "projected_wall_hours_with_contingency": projected_hours,
    }


def plan_summary(config: dict[str, Any]) -> dict[str, Any]:
    inventory = build_inventory(config)
    validation = validate_design(config, inventory)
    injection_families = {
        family: sum(item["family"] == family for item in inventory["injection_cases"])
        for family in ("main", "annual", "boundary")
    }
    structured_variants = {
        variant["id"]: sum(
            item["variant"] == variant["id"]
            for item in inventory["structured_tail_cases"]
        )
        for variant in config["structured_tail_evaluation"]["variants"]
    }
    return {
        "schema_version": 1,
        "plan_id": config["plan_id"],
        "status": validation["status"],
        "execution_authorized": False,
        "target": config["target"],
        "inventory_sha256": inventory["inventory_sha256"],
        "case_counts": {
            "gaussian_threshold_calibration": 1000,
            "sealed_gaussian_evaluation": 500,
            "structured_tail_variants": structured_variants,
            "injections": injection_families,
            "solver_audits": len(inventory["solver_audit_case_ids"]),
            "total_unique_science_cases": (
                len(inventory["gaussian_null_cases"])
                + len(inventory["structured_tail_cases"])
                + len(inventory["injection_cases"])
            ),
        },
        "solver_audit_case_ids": inventory["solver_audit_case_ids"],
        "resource_projection": config["resource_projection"],
        "validation": validation,
        "observed_periodic_search_authorized": False,
        "next_gate": "implementation_and_separate_execution_freeze",
    }


def verify_design_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if freeze.get("status") != "frozen_calibration_design_execution_locked":
        failures.append("Calibration design freeze status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append("Calibration execution is not locked")
    if freeze.get("observed_periodic_search_authorized") is not False:
        failures.append("Observed periodic search is not locked")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        path = root / relative
        if not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"Hash mismatch: {relative}")
    config = load_yaml(root / CONFIG_PATH)
    inventory_hash = build_inventory(config)["inventory_sha256"]
    if inventory_hash != freeze.get("inventory_sha256"):
        failures.append("Calibration inventory hash mismatch")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_id": freeze.get("freeze_id"),
        "freeze_sha256": hash_file(freeze_path, "sha256"),
        "inventory_sha256": inventory_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-calibration-design")
    parser.add_argument("command", choices=("plan", "inventory", "verify-freeze"))
    parser.add_argument("--config", default=str(repository_root() / CONFIG_PATH))
    args = parser.parse_args()
    if args.command == "verify-freeze":
        result = verify_design_freeze()
    else:
        config = load_yaml(Path(args.config))
        result = (
            plan_summary(config) if args.command == "plan" else build_inventory(config)
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status", "pass") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
