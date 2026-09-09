from __future__ import annotations

import json
from typing import Any

from .config import load_yaml
from .paths import repository_root
from .pilot2_injection_remediation import (
    BASE_CONFIG_PATH,
    build_remediation_inventory,
    validate_remediation_design,
)
from .provenance import hash_file

CONFIG_PATH = "config/pilot2_injection_remediation_v0.2.3.yaml"
V022_CONFIG_PATH = "config/pilot2_injection_remediation_v0.2.2.yaml"
FREEZE_PATH = "protocol/PILOT2_INJECTION_REMEDIATION_FREEZE_v0.2.3.json"


def load_design() -> tuple[dict[str, Any], dict[str, Any]]:
    root = repository_root()
    return load_yaml(root / BASE_CONFIG_PATH), load_yaml(root / CONFIG_PATH)


def build_v023_inventory() -> dict[str, Any]:
    base, remediation = load_design()
    return build_remediation_inventory(base, remediation)


def validate_v023_design() -> dict[str, Any]:
    root = repository_root()
    base, remediation = load_design()
    inventory = build_remediation_inventory(base, remediation)
    common = validate_remediation_design(base, remediation, inventory)
    failures = list(common["failures"])
    v022 = build_remediation_inventory(base, load_yaml(root / V022_CONFIG_PATH))
    ids = {item["case_id"] for item in inventory["cases"]}
    seeds = {int(item["seed"]) for item in inventory["cases"]}
    v022_ids = {item["case_id"] for item in v022["cases"]}
    v022_seeds = {int(item["seed"]) for item in v022["cases"]}
    consumed = remediation["consumed_v0.2.2_case"]
    if ids & v022_ids:
        failures.append("v0.2.3 case IDs overlap v0.2.2")
    if seeds & v022_seeds:
        failures.append("v0.2.3 seeds overlap v0.2.2")
    if consumed["case_id"] in ids or int(consumed["seed"]) in seeds:
        failures.append("The consumed v0.2.2 first case was reused")
    if remediation["authority"].get("v0.2.2_resume_authorized") is not False:
        failures.append("v0.2.2 resume is not locked")
    if remediation["authority"].get("v0.2.2_case_rerun_authorized") is not False:
        failures.append("v0.2.2 case rerun is not locked")
    return {
        **common,
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "case_ids_disjoint_from_v0.2.2": not bool(ids & v022_ids),
        "seeds_disjoint_from_v0.2.2": not bool(seeds & v022_seeds),
        "consumed_v0.2.2_case_excluded": (
            consumed["case_id"] not in ids and int(consumed["seed"]) not in seeds
        ),
        "v0.2.2_inventory_sha256": v022["inventory_sha256"],
    }


def verify_remediation_freeze() -> dict[str, Any]:
    root = repository_root()
    path = root / FREEZE_PATH
    if not path.is_file():
        return {"status": "locked", "failures": ["v0.2.3 remediation freeze is absent"]}
    freeze = json.loads(path.read_text(encoding="utf-8"))
    validation = validate_v023_design()
    failures = list(validation["failures"])
    if freeze.get("status") != "remediation_design_frozen_execution_not_authorized":
        failures.append("v0.2.3 remediation freeze status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append("v0.2.3 remediation freeze authorizes execution")
    if freeze.get("inventory_sha256") != validation["inventory_sha256"]:
        failures.append("v0.2.3 remediation inventory mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        item = root / relative
        if not item.is_file() or hash_file(item, "sha256") != expected:
            failures.append(f"v0.2.3 remediation hash mismatch: {relative}")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "execution_authorized": False,
        "inventory_sha256": validation["inventory_sha256"],
        "freeze_sha256": hash_file(path, "sha256"),
    }
