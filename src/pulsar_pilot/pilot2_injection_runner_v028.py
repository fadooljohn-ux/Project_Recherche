from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from .paths import MARKER_PROJECT, configured_data_root, repository_root
from .pilot2_durable_ledger import SingleWriterLock, V028Ledger, durable_atomic_json, durable_mkdirs
from .pilot2_release_contract import (
    BASE_CONFIG_PATH,
    CURRENT_IMPLEMENTATION_PATHS,
    DESIGN_FREEZE_PATH,
    INVENTORY_SHA256,
    REMEDIATION_CONFIG_PATH,
    RUNNER_CONFIG_PATH,
    aggregate_sha256,
    verify_design_freeze,
    verify_repository_execution_authorization,
    verify_v023_remediation_freeze,
)
from .pilot2_runtime_core import execute
from .pilot2_trusted_data import load_json, load_yaml, require_exact_keys
from .provenance import logical_path

TEMPORARY_GENERATION = "temporary-zero-science-v0.2.8"
TEMP_ENVIRONMENT_SHA256 = hashlib.sha256(b"v0.2.8 temporary environment placeholder").hexdigest()
TEMP_RESOURCE_SHA256 = hashlib.sha256(b"v0.2.8 temporary resource placeholder").hexdigest()


def candidate_implementation_sha256(root: Path | None = None) -> str:
    root = root or repository_root()
    runner = load_yaml(root / RUNNER_CONFIG_PATH, "v0.2.8 runner configuration")
    paths = tuple(runner["implementation_paths"]) + CURRENT_IMPLEMENTATION_PATHS + (
        BASE_CONFIG_PATH,
        REMEDIATION_CONFIG_PATH,
        RUNNER_CONFIG_PATH,
        DESIGN_FREEZE_PATH,
        "pixi.lock",
        "pixi.toml",
        "pyproject.toml",
    )
    return aggregate_sha256(root, paths)


def candidate_science_control_sha256(root: Path | None = None) -> str:
    root = root or repository_root()
    return aggregate_sha256(root, (BASE_CONFIG_PATH, REMEDIATION_CONFIG_PATH, RUNNER_CONFIG_PATH))


def initialize_temporary_validation_root(root: Path, data_root_id: str = "v028-temp-root") -> None:
    resolved = root.resolve()
    system_temporary = Path(tempfile.gettempdir()).resolve()
    if not resolved.is_relative_to(system_temporary):
        raise RuntimeError(
            "v0.2.8 temporary validation root must be under the system temp directory"
        )
    durable_mkdirs(resolved)
    marker = {
        "schema_version": 2,
        "project": MARKER_PROJECT,
        "data_root_id": data_root_id,
        "generation": TEMPORARY_GENERATION,
    }
    durable_atomic_json(resolved / ".project-recherche-data-root.json", marker)


def _require_temporary_validation_root(root: Path) -> dict[str, Any]:
    resolved = root.resolve()
    if not resolved.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise RuntimeError("v0.2.8 dry run is restricted to a system temporary root")
    marker = require_exact_keys(
        load_json(resolved / ".project-recherche-data-root.json", "v0.2.8 temp marker"),
        {"schema_version", "project", "data_root_id", "generation"},
        "v0.2.8 temporary validation marker",
    )
    if marker != {
        "schema_version": 2,
        "project": MARKER_PROJECT,
        "data_root_id": marker.get("data_root_id"),
        "generation": TEMPORARY_GENERATION,
    }:
        raise RuntimeError("v0.2.8 temporary validation marker is invalid")
    if type(marker["data_root_id"]) is not str or not marker["data_root_id"]:
        raise RuntimeError("v0.2.8 temporary validation root ID is invalid")
    return marker


def zero_case_dry_run(data_root: Path) -> dict[str, Any]:
    marker = _require_temporary_validation_root(data_root)
    design = verify_design_freeze()
    remediation = verify_v023_remediation_freeze()
    repository_gate = verify_repository_execution_authorization()
    implementation_hash = candidate_implementation_sha256()
    science_hash = candidate_science_control_sha256()
    with SingleWriterLock(data_root):
        ledger = V028Ledger(
            data_root,
            inventory_sha256=INVENTORY_SHA256,
            implementation_sha256=implementation_hash,
            science_control_sha256=science_hash,
            environment_manifest_sha256=TEMP_ENVIRONMENT_SHA256,
            resource_manifest_sha256=TEMP_RESOURCE_SHA256,
        )
        state = ledger.load()
        ledger.save(state)
        verification = ledger.verify_artifacts()
    case_root = data_root / "derived/pilot2/calibration-v0.2.8/injections"
    criteria = {
        "temporary_root_marker_valid": marker["generation"] == TEMPORARY_GENERATION,
        "design_freeze_passes": design["status"] == "pass",
        "remediation_freeze_passes": remediation["status"] == "pass",
        "repository_gate_fail_closed": repository_gate["status"] in {"locked", "fail"},
        "execution_freeze_absent": any(
            "execution freeze is absent" in failure for failure in repository_gate["failures"]
        ),
        "predecessors_not_loaded": repository_gate["predecessors_loaded"] is False,
        "ledger_schema_and_artifacts_pass": verification["status"] == "pass",
        "ledger_stage_pending": state["stage_status"]["injection_remediation_evaluation"]
        == "pending",
        "ledger_cases_zero": len(state["completed_cases"]) == 0,
        "ledger_stage_results_zero": len(state["stage_results"]) == 0,
        "ledger_active_attempt_absent": state["active_attempt"] is None,
        "ledger_hard_stop_absent": state["hard_stop"] is None,
        "case_root_not_created": not case_root.exists(),
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "v0.2.8_repository_and_temporary_root_zero_science_dry_run",
        "criteria": criteria,
        "candidate_implementation_sha256": implementation_hash,
        "candidate_science_control_sha256": science_hash,
        "temporary_environment_placeholder_sha256": TEMP_ENVIRONMENT_SHA256,
        "temporary_resource_placeholder_sha256": TEMP_RESOURCE_SHA256,
        "temporary_placeholders_have_execution_authority": False,
        "science_cases_executed": 0,
        "random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
        "predecessor_artifacts_loaded": 0,
        "external_data_root_accessed": False,
        "observed_residual_accessed": False,
        "execution_gate_status": repository_gate["status"],
        "health_record": logical_path(ledger.health_path, data_root),
    }


def implementation_candidate_report() -> dict[str, Any]:
    design = verify_design_freeze()
    remediation = verify_v023_remediation_freeze()
    runner = load_yaml(repository_root() / RUNNER_CONFIG_PATH, "v0.2.8 runner configuration")
    missing_manifests = [
        relative
        for relative in runner["manifests"].values()
        if not (repository_root() / relative).is_file()
    ]
    return {
        "schema_version": 1,
        "status": "implementation_candidate"
        if design["status"] == remediation["status"] == "pass"
        else "fail",
        "design_freeze": design,
        "remediation_freeze": remediation,
        "candidate_implementation_sha256": candidate_implementation_sha256(),
        "candidate_science_control_sha256": candidate_science_control_sha256(),
        "runtime_manifests_pending_real_root_preflight": missing_manifests,
        "implementation_freeze_created": False,
        "readiness_freeze_created": False,
        "execution_authorized": False,
        "science_cases_executed": 0,
        "next_gate": "repository_and_temporary_root_zero_science_validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-injection-runner-v028")
    parser.add_argument("command", choices=("verify-design", "verify-gate", "dry-run", "run"))
    parser.add_argument("--data-root")
    args = parser.parse_args()
    if args.command == "verify-design":
        result = implementation_candidate_report()
    elif args.command == "verify-gate":
        result = verify_repository_execution_authorization()
    else:
        data_root = configured_data_root(args.data_root)
        result = zero_case_dry_run(data_root) if args.command == "dry-run" else execute(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") not in {"fail"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
