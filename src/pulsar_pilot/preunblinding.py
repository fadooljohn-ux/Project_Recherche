from __future__ import annotations

import json
from typing import Any

from .config import load_yaml
from .paths import repository_root
from .provenance import hash_file
from .tail_robustness import (
    _canonical_hash,
    _seed_for_case,
    build_recovery_order,
)
from .tail_robustness import build_null_orders as build_v0p1_null_orders
from .tail_robustness_r1 import build_null_orders as build_r1_null_orders

CONFIG_PATH = "config/pilot1_preunblinding_validation_v0.1.yaml"
FREEZE_PATH = "protocol/PILOT1_PREUNBLINDING_VALIDATION_FREEZE_v0.1.json"
THRESHOLD_PATH = "protocol/PILOT1_THRESHOLD_LOCK_v0.1.json"
V0P1_TAIL_CONFIG_PATH = "config/pilot1_tail_robustness_v0.1.yaml"
R1_TAIL_CONFIG_PATH = "config/pilot1_tail_robustness_r1_v0.1.yaml"


def build_structured_tail_inventory(config: dict[str, Any]) -> list[dict[str, Any]]:
    section = config["structured_tail_variants"]
    count = int(section["evaluation_cases_per_variant"])
    records: list[dict[str, Any]] = []
    for variant in section["variants"]:
        variant_id = str(variant["id"])
        base_seed = int(variant["base_seed"])
        for index in range(count):
            case_id = f"preunblind-{variant_id}-{index:04d}"
            records.append(
                {
                    "case_id": case_id,
                    "family": "structured_tail_evaluation",
                    "variant": variant_id,
                    "index": index,
                    "seed": _seed_for_case(base_seed, case_id),
                }
            )

    ids = {record["case_id"] for record in records}
    seeds = {record["seed"] for record in records}
    if len(ids) != len(records) or len(seeds) != len(records):
        raise RuntimeError("Pre-unblinding structured-tail inventory is not unique")

    root = repository_root()
    original = build_v0p1_null_orders(load_yaml(root / V0P1_TAIL_CONFIG_PATH))
    r1 = build_r1_null_orders(load_yaml(root / R1_TAIL_CONFIG_PATH))
    prior = [item for family in original.values() for item in family]
    prior.extend(item for family in r1.values() for item in family)
    if ids & {item["case_id"] for item in prior}:
        raise RuntimeError("Pre-unblinding case IDs overlap prior tail nulls")
    if seeds & {item["seed"] for item in prior}:
        raise RuntimeError("Pre-unblinding seeds overlap prior tail nulls")
    return records


def build_deletion_replay_inventory(config: dict[str, Any]) -> list[dict[str, Any]]:
    root = repository_root()
    source = build_recovery_order(load_yaml(root / V0P1_TAIL_CONFIG_PATH))
    deletion_units = list(config["deletion_stability_cost"]["deletion_units"])
    return [
        {
            "source_case_id": case["case_id"],
            "source_seed": case["seed"],
            "period_days": case["period_days"],
            "amplitude_microseconds": case["amplitude_microseconds"],
            "phase_radians": case["phase_radians"],
            "deletion_units": deletion_units,
        }
        for case in source
    ]


def inventory_hashes(config: dict[str, Any]) -> dict[str, str]:
    return {
        "structured_tail_evaluation": _canonical_hash(
            build_structured_tail_inventory(config)
        ),
        "deletion_replay": _canonical_hash(build_deletion_replay_inventory(config)),
    }


def verify_freeze() -> dict[str, Any]:
    root = repository_root()
    freeze_path = root / FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    config = load_yaml(root / CONFIG_PATH)
    threshold = json.loads((root / THRESHOLD_PATH).read_text(encoding="utf-8"))
    failures: list[str] = []

    if freeze.get("status") != "frozen_for_synthetic_preunblinding_validation":
        failures.append("freeze status is invalid")
    if freeze.get("authorization") != "synthetic_validation_only":
        failures.append("freeze authorization is invalid")
    for field in (
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "threshold_retuning_authorized",
        "further_tail_reroll_authorized",
    ):
        if freeze.get(field) is not False:
            failures.append(f"{field} must be false")
    if freeze.get("independent_final_signoff_required") is not True:
        failures.append("independent final sign-off must be required")
    if freeze.get("pipeline_operator_may_self_sign") is not False:
        failures.append("pipeline operator may not self-sign")
    if float(config["locked_detector"]["threshold_delta_chi2"]) != float(
        threshold["value_delta_chi2"]
    ):
        failures.append("locked threshold does not match the v0.1 threshold record")
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
        "structured_tail_cases": len(build_structured_tail_inventory(config)),
        "deletion_replay_cases": len(build_deletion_replay_inventory(config)),
        "observed_periodic_search_authorized": False,
        "independent_final_signoff_required": True,
    }
