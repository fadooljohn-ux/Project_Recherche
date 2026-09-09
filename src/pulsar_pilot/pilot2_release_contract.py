from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .paths import MARKER_PROJECT, repository_root
from .pilot2_offline_resources import (
    load_resource_manifest,
    validate_environment_manifest,
)
from .pilot2_trusted_data import (
    TrustedDataError,
    canonical_sha256,
    load_json,
    load_yaml,
    require_exact_keys,
    require_nonempty_string,
    require_sha256,
    require_type,
    validate_hash_map,
)
from .provenance import hash_file

VERSION = "v0.2.8"
RUN_ID = "pilot2-b1937-injection-remediation-v0.2.8"
INVENTORY_SHA256 = "811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b"
DESIGN_FREEZE_PATH = "protocol/PILOT2_INJECTION_REMEDIATION_DESIGN_FREEZE_v0.2.8.json"
IMPLEMENTATION_FREEZE_PATH = "protocol/PILOT2_INJECTION_RUNNER_FREEZE_v0.2.8.json"
READINESS_FREEZE_PATH = "protocol/PILOT2_INJECTION_EXECUTION_READINESS_FREEZE_v0.2.8.json"
EXECUTION_FREEZE_PATH = "protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.8.json"
RUNNER_CONFIG_PATH = "config/pilot2_injection_runner_v0.2.8.yaml"
BASE_CONFIG_PATH = "config/pilot2_calibration_v0.2.1.yaml"
REMEDIATION_CONFIG_PATH = "config/pilot2_injection_remediation_v0.2.3.yaml"
REMEDIATION_FREEZE_PATH = "protocol/PILOT2_INJECTION_REMEDIATION_FREEZE_v0.2.3.json"
EXPECTED_CASE_COUNTS = {
    "main": 240,
    "phase_reference": 60,
    "annual": 28,
    "boundary": 16,
    "solver_audits": 35,
}

IOC_SCIENCE_BINDING_SCHEMA = "pilot2-science-execution-binding-v1"
IOC_MODULE_ID = "pilot2-b1937-injection-science"
IOC_MODULE_RELEASE_ID = "pilot2-b1937-injection-science-ioc-v1"
IOC_SCIENCE_RUN_ID = RUN_ID
IOC_EXPECTED_ACCOUNTING = {
    "cases": 344,
    "primary_fits": 688,
    "solver_audits": 35,
}
CURRENT_IMPLEMENTATION_PATHS = (
    "src/pulsar_pilot/spin_phase.py",
    "src/pulsar_pilot/circular_signal.py",
    "src/pulsar_pilot/pilot2_case_contract.py",
    "src/pulsar_pilot/runtime_limits.py",
)
IOC_EXECUTION_FREEZE_PATH = "protocol/PILOT2_IOC_SCIENCE_EXECUTION_FREEZE_v1.json"
IOC_EXECUTION_FREEZE_SCHEMA = "pilot2-ioc-science-execution-freeze-v1"
IOC_EXECUTION_FREEZE_ID = "pilot2-b1937-injection-science-execution-freeze-ioc-v1"
IOC_EXECUTION_FREEZE_STATUS = "frozen_before_first_ioc_science_case"
IOC_LAUNCH_CONTRACT = {
    "foreground": True,
    "harness_module": "pulsar_pilot.pilot2_ioc_harness",
    "harness_command": "run",
    "adapter_path": "pulsar_pilot.pilot2_science_module:SCIENCE_MODULE.run",
    "science_entry": "pulsar_pilot.pilot2_runtime_core.execute",
}
IOC_STOP_RULE = "any_stop_or_failure_consumes_outer_and_inner_identity_without_resume"

IOC_SCIENCE_BINDING_KEYS = {
    "schema",
    "ioc_run_id",
    "module_release_id",
    "science_run_id",
    "execution_freeze_sha256",
    "inventory_sha256",
    "expected_accounting",
    "science_data_root",
    "fresh_only",
    "resume_authorized",
}
IOC_EXECUTION_FREEZE_KEYS = {
    "schema",
    "freeze_id",
    "recorded_utc",
    "status",
    "scope",
    "user_authorization",
    "execution_authorized",
    "ioc_run_id",
    "module_id",
    "module_release_id",
    "science_run_id",
    "inventory_sha256",
    "expected_accounting",
    "science_data_root",
    "implementation_sha256",
    "science_control_sha256",
    "environment_manifest_sha256",
    "resource_manifest_sha256",
    "threshold_lock_sha256",
    "launch_contract",
    "fresh_only",
    "resume_authorized",
    "observed_residual_access_authorized",
    "observed_periodic_search_authorized",
    "promotion_grade_authorized",
    "discovery_claim_authorized",
    "frozen_sha256",
    "stop_rule",
}

DESIGN_FREEZE_KEYS = {
    "schema_version",
    "freeze_id",
    "recorded_utc",
    "status",
    "scope",
    "user_authorization",
    "rebaseline_commit",
    "inventory_policy",
    "inventory_sha256",
    "authorized_case_counts_if_separately_approved_later",
    "v0.2.2_namespace_retired",
    "v0.2.7_terminal_failure_preserved",
    "v0.2.7_resume_authorized",
    "implementation_authorized",
    "real_root_context_preflight_authorized",
    "science_execution_authorized",
    "observed_residual_access_authorized",
    "observed_periodic_search_authorized",
    "promotion_grade_authorized",
    "discovery_claim_authorized",
    "assembly_finding_design_disposition",
    "milestone_status",
    "science_boundary",
    "frozen_sha256",
    "next_gate",
}
IMPLEMENTATION_FREEZE_KEYS = {
    "schema_version",
    "freeze_id",
    "recorded_utc",
    "status",
    "scope",
    "inventory_sha256",
    "implementation_sha256",
    "science_control_sha256",
    "environment_manifest_sha256",
    "resource_manifest_sha256",
    "design_freeze_sha256",
    "execution_authorized",
    "real_root_context_preflight_authorized",
    "observed_residual_access_authorized",
    "observed_periodic_search_authorized",
    "promotion_grade_authorized",
    "discovery_claim_authorized",
    "validation",
    "frozen_sha256",
    "next_gate",
}
READINESS_FREEZE_KEYS = {
    "schema_version",
    "freeze_id",
    "recorded_utc",
    "status",
    "execution_readiness",
    "inventory_sha256",
    "implementation_sha256",
    "science_control_sha256",
    "environment_manifest_sha256",
    "resource_manifest_sha256",
    "implementation_freeze_sha256",
    "repository_validation_sha256",
    "temporary_root_validation_sha256",
    "real_root_context_preflight_sha256",
    "execution_authorized",
    "observed_residual_access_authorized",
    "observed_periodic_search_authorized",
    "promotion_grade_authorized",
    "discovery_claim_authorized",
    "frozen_sha256",
    "next_gate",
}
EXECUTION_FREEZE_KEYS = {
    "schema_version",
    "freeze_id",
    "recorded_utc",
    "status",
    "scope",
    "user_authorization",
    "execution_authorized",
    "authorized_case_counts",
    "authorized_primary_fits",
    "inventory_sha256",
    "implementation_sha256",
    "science_control_sha256",
    "environment_manifest_sha256",
    "resource_manifest_sha256",
    "design_freeze_sha256",
    "remediation_freeze_sha256",
    "implementation_freeze_sha256",
    "readiness_freeze_sha256",
    "audit",
    "data_root",
    "predecessor_sha256",
    "threshold_lock_sha256",
    "launch_contract",
    "supervision_policy",
    "no_reroll",
    "threshold_retuning_authorized",
    "observed_residual_access_authorized",
    "observed_periodic_search_authorized",
    "promotion_grade_authorized",
    "discovery_claim_authorized",
    "stop_rule",
    "frozen_sha256",
    "next_gate_if_pass",
    "next_gate_if_fail",
}


def aggregate_sha256(root: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        path = root / relative
        if not path.is_file():
            raise TrustedDataError(f"aggregate input is missing: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_exact_repository_hashes(
    root: Path,
    value: Any,
    expected_paths: Iterable[str] | None,
    label: str,
) -> list[str]:
    failures: list[str] = []
    try:
        frozen = validate_hash_map(value, f"{label}.frozen_sha256")
    except TrustedDataError as error:
        return [str(error)]
    if expected_paths is not None and set(frozen) != set(expected_paths):
        failures.append(f"{label} frozen path set is not exact")
    resolved_root = root.resolve()
    for relative, expected in frozen.items():
        path = root / relative
        try:
            if Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise OSError("path is not confined")
            if path.is_symlink() or not path.is_file():
                raise OSError("path is not a regular file")
            if not path.resolve(strict=True).is_relative_to(resolved_root):
                raise OSError("path escapes repository")
            if hash_file(path, "sha256") != expected:
                failures.append(f"{label} hash mismatch: {relative}")
        except OSError as error:
            failures.append(f"{label} path invalid: {relative}: {error}")
    return failures


def verify_design_freeze(root: Path | None = None) -> dict[str, Any]:
    root = root or repository_root()
    path = root / DESIGN_FREEZE_PATH
    if not path.is_file():
        return {"status": "locked", "failures": ["v0.2.8 design freeze is absent"]}
    failures: list[str] = []
    try:
        freeze = require_exact_keys(
            load_json(path, "v0.2.8 design freeze"), DESIGN_FREEZE_KEYS, "v0.2.8 design freeze"
        )
        if freeze["schema_version"] != 1 or type(freeze["schema_version"]) is not int:
            failures.append("v0.2.8 design-freeze schema is invalid")
        if freeze["freeze_id"] != "pilot2-b1937-injection-remediation-design-freeze-v0.2.8":
            failures.append("v0.2.8 design-freeze ID is invalid")
        if freeze["status"] != "frozen_zero_science_design_before_implementation":
            failures.append("v0.2.8 design-freeze status is invalid")
        if freeze["inventory_sha256"] != INVENTORY_SHA256:
            failures.append("v0.2.8 design inventory mismatch")
        if freeze["authorized_case_counts_if_separately_approved_later"] != EXPECTED_CASE_COUNTS:
            failures.append("v0.2.8 design case-count contract is invalid")
        for key in (
            "v0.2.7_resume_authorized",
            "implementation_authorized",
            "real_root_context_preflight_authorized",
            "science_execution_authorized",
            "observed_residual_access_authorized",
            "observed_periodic_search_authorized",
            "promotion_grade_authorized",
            "discovery_claim_authorized",
        ):
            if freeze[key] is not False:
                failures.append(f"v0.2.8 design boundary invalid: {key}")
        if (
            freeze["v0.2.2_namespace_retired"] is not True
            or freeze["v0.2.7_terminal_failure_preserved"] is not True
        ):
            failures.append("v0.2.8 predecessor preservation boundary is invalid")
        failures.extend(
            verify_exact_repository_hashes(root, freeze["frozen_sha256"], None, "design")
        )
    except TrustedDataError as error:
        failures.append(str(error))
        freeze = {}
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_sha256": hash_file(path, "sha256"),
        "freeze": freeze,
    }


def verify_v023_remediation_freeze(root: Path | None = None) -> dict[str, Any]:
    root = root or repository_root()
    path = root / REMEDIATION_FREEZE_PATH
    failures: list[str] = []
    if not path.is_file():
        return {"status": "fail", "failures": ["v0.2.3 remediation freeze is absent"]}
    try:
        freeze = load_json(path, "v0.2.3 remediation freeze")
        require_type(freeze, dict, "v0.2.3 remediation freeze")
        if freeze.get("status") != "remediation_design_frozen_execution_not_authorized":
            failures.append("v0.2.3 remediation-freeze status is invalid")
        if freeze.get("inventory_sha256") != INVENTORY_SHA256:
            failures.append("v0.2.3 remediation inventory mismatch")
        if freeze.get("execution_authorized") is not False:
            failures.append("v0.2.3 remediation authorization boundary is invalid")
        if freeze.get("consumed_case_id") != "p2r2-inj-main-p00-a00-h00-n00":
            failures.append("v0.2.2 consumed case mismatch")
        if freeze.get("consumed_seed") != 2691995251659989168:
            failures.append("v0.2.2 consumed seed mismatch")
        failures.extend(
            verify_exact_repository_hashes(root, freeze.get("frozen_sha256"), None, "remediation")
        )
    except TrustedDataError as error:
        failures.append(str(error))
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_sha256": hash_file(path, "sha256"),
    }


def load_science_controls(
    root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = root or repository_root()
    return (
        load_yaml(root / BASE_CONFIG_PATH, "v0.2.8 base science configuration"),
        load_yaml(root / REMEDIATION_CONFIG_PATH, "v0.2.8 remediation science configuration"),
        load_yaml(root / RUNNER_CONFIG_PATH, "v0.2.8 runner configuration"),
    )


def science_control_sha256(root: Path | None = None) -> str:
    root = root or repository_root()
    _, _, runner = load_science_controls(root)
    paths = (
        BASE_CONFIG_PATH,
        REMEDIATION_CONFIG_PATH,
        RUNNER_CONFIG_PATH,
        runner["manifests"]["resource"],
        runner["manifests"]["environment"],
    )
    return aggregate_sha256(root, paths)


def implementation_sha256(root: Path | None = None) -> str:
    root = root or repository_root()
    _, _, runner = load_science_controls(root)
    paths = tuple(runner["implementation_paths"]) + CURRENT_IMPLEMENTATION_PATHS + (
        BASE_CONFIG_PATH,
        REMEDIATION_CONFIG_PATH,
        RUNNER_CONFIG_PATH,
        runner["manifests"]["resource"],
        runner["manifests"]["environment"],
        "pixi.lock",
        "pixi.toml",
        "pyproject.toml",
    )
    return aggregate_sha256(root, paths)


def _verify_freeze(
    *,
    root: Path,
    path_name: str,
    keys: set[str],
    freeze_id: str,
    expected_status: str,
    label: str,
) -> dict[str, Any]:
    path = root / path_name
    if not path.is_file():
        return {"status": "locked", "failures": [f"v0.2.8 {label} freeze is absent"]}
    failures: list[str] = []
    try:
        freeze = require_exact_keys(
            load_json(path, f"v0.2.8 {label} freeze"), keys, f"v0.2.8 {label} freeze"
        )
        if freeze["schema_version"] != 1 or type(freeze["schema_version"]) is not int:
            failures.append(f"v0.2.8 {label} schema is invalid")
        if freeze["freeze_id"] != freeze_id:
            failures.append(f"v0.2.8 {label} ID is invalid")
        if freeze["status"] != expected_status:
            failures.append(f"v0.2.8 {label} status is invalid")
        if freeze["inventory_sha256"] != INVENTORY_SHA256:
            failures.append(f"v0.2.8 {label} inventory mismatch")
        for boundary in (
            "execution_authorized",
            "observed_residual_access_authorized",
            "observed_periodic_search_authorized",
            "promotion_grade_authorized",
            "discovery_claim_authorized",
        ):
            if freeze[boundary] is not False:
                failures.append(f"v0.2.8 {label} boundary invalid: {boundary}")
        if freeze["implementation_sha256"] != implementation_sha256(root):
            failures.append(f"v0.2.8 {label} implementation mismatch")
        if freeze["science_control_sha256"] != science_control_sha256(root):
            failures.append(f"v0.2.8 {label} science-control mismatch")
        _, _, runner = load_science_controls(root)
        resource_path = root / runner["manifests"]["resource"]
        environment_path = root / runner["manifests"]["environment"]
        if freeze["resource_manifest_sha256"] != hash_file(resource_path, "sha256"):
            failures.append(f"v0.2.8 {label} resource-manifest mismatch")
        if freeze["environment_manifest_sha256"] != hash_file(environment_path, "sha256"):
            failures.append(f"v0.2.8 {label} environment-manifest mismatch")
        failures.extend(verify_exact_repository_hashes(root, freeze["frozen_sha256"], None, label))
    except (TrustedDataError, KeyError, OSError) as error:
        failures.append(str(error))
        freeze = {}
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_sha256": hash_file(path, "sha256"),
        "freeze": freeze,
    }


def verify_implementation_freeze(root: Path | None = None) -> dict[str, Any]:
    root = root or repository_root()
    return _verify_freeze(
        root=root,
        path_name=IMPLEMENTATION_FREEZE_PATH,
        keys=IMPLEMENTATION_FREEZE_KEYS,
        freeze_id="pilot2-b1937-injection-runner-freeze-v0.2.8",
        expected_status="implementation_frozen_execution_not_authorized",
        label="implementation",
    )


def verify_readiness_freeze(root: Path | None = None) -> dict[str, Any]:
    root = root or repository_root()
    result = _verify_freeze(
        root=root,
        path_name=READINESS_FREEZE_PATH,
        keys=READINESS_FREEZE_KEYS,
        freeze_id="pilot2-b1937-injection-readiness-freeze-v0.2.8",
        expected_status="readiness_frozen_execution_not_authorized",
        label="readiness",
    )
    if result["status"] == "pass":
        try:
            freeze = result["freeze"]
            implementation = verify_implementation_freeze(root)
            if freeze["execution_readiness"] != "pass":
                result["failures"].append("v0.2.8 readiness semantic is not PASS")
            if freeze["implementation_freeze_sha256"] != implementation.get("freeze_sha256"):
                result["failures"].append("v0.2.8 readiness implementation-freeze mismatch")
            for key in (
                "repository_validation_sha256",
                "temporary_root_validation_sha256",
                "real_root_context_preflight_sha256",
                "environment_manifest_sha256",
                "resource_manifest_sha256",
            ):
                require_sha256(freeze[key], f"v0.2.8 readiness.{key}")
        except (TrustedDataError, KeyError) as error:
            result["failures"].append(str(error))
        result["status"] = "pass" if not result["failures"] else "fail"
    return result


def _validate_execution_freeze(
    freeze: Any,
    *,
    root: Path,
    implementation: dict[str, Any],
    readiness: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    try:
        item = require_exact_keys(freeze, EXECUTION_FREEZE_KEYS, "v0.2.8 execution freeze")
        if item["schema_version"] != 1 or type(item["schema_version"]) is not int:
            failures.append("v0.2.8 execution schema is invalid")
        if item["freeze_id"] != "pilot2-b1937-injection-execution-freeze-v0.2.8":
            failures.append("v0.2.8 execution ID is invalid")
        if item["status"] != "frozen_before_first_v0.2.8_injection_case":
            failures.append("v0.2.8 execution status is invalid")
        require_nonempty_string(item["user_authorization"], "v0.2.8 user authorization")
        if item["execution_authorized"] is not True:
            failures.append("v0.2.8 execution authorization is absent")
        if item["authorized_case_counts"] != EXPECTED_CASE_COUNTS:
            failures.append("v0.2.8 execution case counts are invalid")
        if (
            item["authorized_primary_fits"] != 688
            or type(item["authorized_primary_fits"]) is not int
        ):
            failures.append("v0.2.8 authorized primary-fit count is invalid")
        if item["inventory_sha256"] != INVENTORY_SHA256:
            failures.append("v0.2.8 execution inventory mismatch")
        expected_hashes = {
            "implementation_sha256": implementation_sha256(root),
            "science_control_sha256": science_control_sha256(root),
            "design_freeze_sha256": verify_design_freeze(root).get("freeze_sha256"),
            "remediation_freeze_sha256": verify_v023_remediation_freeze(root).get("freeze_sha256"),
            "implementation_freeze_sha256": implementation.get("freeze_sha256"),
            "readiness_freeze_sha256": readiness.get("freeze_sha256"),
        }
        for key, expected in expected_hashes.items():
            if item[key] != expected:
                failures.append(f"v0.2.8 execution {key} mismatch")
        _, _, runner = load_science_controls(root)
        resource_path = root / runner["manifests"]["resource"]
        environment_path = root / runner["manifests"]["environment"]
        if item["resource_manifest_sha256"] != hash_file(resource_path, "sha256"):
            failures.append("v0.2.8 execution resource-manifest mismatch")
        if item["environment_manifest_sha256"] != hash_file(environment_path, "sha256"):
            failures.append("v0.2.8 execution environment-manifest mismatch")
        audit = require_exact_keys(
            item["audit"],
            {
                "status",
                "record_path",
                "record_sha256",
                "disposition_path",
                "disposition_sha256",
                "report_path",
                "report_sha256",
            },
            "v0.2.8 execution audit",
        )
        if audit["status"] != "pass":
            failures.append("v0.2.8 execution audit is not PASS")
        audit_artifacts = (
            ("record_path", "record_sha256"),
            ("disposition_path", "disposition_sha256"),
            ("report_path", "report_sha256"),
        )
        for path_key, hash_key in audit_artifacts:
            require_nonempty_string(audit[path_key], f"v0.2.8 execution audit.{path_key}")
            require_sha256(audit[hash_key], f"v0.2.8 execution audit.{hash_key}")
            failures.extend(
                verify_exact_repository_hashes(
                    root,
                    {audit[path_key]: audit[hash_key]},
                    {audit[path_key]},
                    f"execution audit {path_key}",
                )
            )
        data_root = require_exact_keys(
            item["data_root"], {"data_root_id", "marker_sha256"}, "v0.2.8 authorized root"
        )
        require_nonempty_string(data_root["data_root_id"], "v0.2.8 data-root ID")
        require_sha256(data_root["marker_sha256"], "v0.2.8 marker hash")
        predecessors = validate_hash_map(item["predecessor_sha256"], "v0.2.8 predecessors")
        expected_predecessors = {
            name: binding["sha256"] for name, binding in runner["predecessor_bindings"].items()
        }
        if predecessors != expected_predecessors:
            failures.append("v0.2.8 execution predecessor binding set differs")
        if item["threshold_lock_sha256"] != predecessors.get("threshold_lock"):
            failures.append("v0.2.8 threshold-lock binding mismatch")
        launch = require_exact_keys(
            item["launch_contract"],
            {"session", "detached_background_launch", "module", "command"},
            "v0.2.8 launch contract",
        )
        if launch != {
            "session": "managed_persistent_exec_session",
            "detached_background_launch": False,
            "module": "pulsar_pilot.pilot2_injection_runner_v028",
            "command": "run",
        }:
            failures.append("v0.2.8 launch contract is invalid")
        supervision = require_exact_keys(
            item["supervision_policy"],
            {
                "heartbeat_interval_seconds",
                "stale_after_seconds",
                "checkpoint_case_interval",
                "passive_review_interval_seconds",
                "scientific_outcomes_in_health_record",
            },
            "v0.2.8 supervision policy",
        )
        if supervision != {
            "heartbeat_interval_seconds": 30,
            "stale_after_seconds": 90,
            "checkpoint_case_interval": 25,
            "passive_review_interval_seconds": 1800,
            "scientific_outcomes_in_health_record": False,
        }:
            failures.append("v0.2.8 supervision policy is invalid")
        for boundary in (
            "threshold_retuning_authorized",
            "observed_residual_access_authorized",
            "observed_periodic_search_authorized",
            "promotion_grade_authorized",
            "discovery_claim_authorized",
        ):
            if item[boundary] is not False:
                failures.append(f"v0.2.8 execution boundary invalid: {boundary}")
        if item["no_reroll"] is not True:
            failures.append("v0.2.8 no-reroll contract is absent")
        if (
            item["stop_rule"]
            != "any_failure_terminally_closes_v0.2.8_without_rerun_retune_or_promotion"
        ):
            failures.append("v0.2.8 stop rule is invalid")
        failures.extend(
            verify_exact_repository_hashes(root, item["frozen_sha256"], None, "execution")
        )
    except (TrustedDataError, KeyError, OSError) as error:
        failures.append(str(error))
    return failures


def verify_repository_execution_authorization(root: Path | None = None) -> dict[str, Any]:
    root = root or repository_root()
    design = verify_design_freeze(root)
    remediation = verify_v023_remediation_freeze(root)
    implementation = verify_implementation_freeze(root)
    readiness = verify_readiness_freeze(root)
    components = (design, remediation, implementation, readiness)
    failures = [failure for component in components for failure in component["failures"]]
    component_failure = any(component["status"] == "fail" for component in components)
    path = root / EXECUTION_FREEZE_PATH
    if not path.is_file():
        return {
            "status": "fail" if component_failure else "locked",
            "failures": failures + ["Separate v0.2.8 execution freeze is absent"],
            "predecessors_loaded": False,
        }
    try:
        freeze = load_json(path, "v0.2.8 execution freeze")
        failures.extend(
            _validate_execution_freeze(
                freeze,
                root=root,
                implementation=implementation,
                readiness=readiness,
            )
        )
    except TrustedDataError as error:
        failures.append(str(error))
        freeze = {}
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "predecessors_loaded": False,
        "freeze_sha256": hash_file(path, "sha256"),
        "freeze": freeze,
    }


def verify_data_root_identity(data_root: Path, authorization: dict[str, Any]) -> dict[str, Any]:
    marker_path = data_root / ".project-recherche-data-root.json"
    failures: list[str] = []
    try:
        marker = require_exact_keys(
            load_json(marker_path, "v0.2.8 data-root marker"),
            {"schema_version", "project", "data_root_id", "generation"},
            "v0.2.8 data-root marker",
        )
        if marker["schema_version"] != 2 or type(marker["schema_version"]) is not int:
            failures.append("v0.2.8 marker schema is invalid")
        if marker["project"] != MARKER_PROJECT:
            failures.append("v0.2.8 marker project is invalid")
        require_nonempty_string(marker["data_root_id"], "v0.2.8 marker data-root ID")
        require_nonempty_string(marker["generation"], "v0.2.8 marker generation")
        if marker["data_root_id"] != authorization["data_root_id"]:
            failures.append("v0.2.8 authorized data-root ID mismatch")
        if hash_file(marker_path, "sha256") != authorization["marker_sha256"]:
            failures.append("v0.2.8 authorized marker hash mismatch")
    except (TrustedDataError, OSError, KeyError) as error:
        failures.append(str(error))
        marker = {}
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "marker": marker,
    }


def verify_execution_gate(
    data_root: Path | None = None, root: Path | None = None
) -> dict[str, Any]:
    root = root or repository_root()
    repository = verify_repository_execution_authorization(root)
    if repository["status"] != "pass":
        return repository
    if data_root is None:
        return {
            **repository,
            "status": "fail",
            "failures": ["Authorized v0.2.8 execution requires an explicit data root"],
            "predecessors_loaded": False,
        }
    identity = verify_data_root_identity(data_root, repository["freeze"]["data_root"])
    if identity["status"] != "pass":
        return {
            **repository,
            "status": "fail",
            "failures": identity["failures"],
            "predecessors_loaded": False,
        }
    _, _, runner = load_science_controls(root)
    resource_path = root / runner["manifests"]["resource"]
    environment_path = root / runner["manifests"]["environment"]
    failures: list[str] = []
    try:
        resources = load_resource_manifest(resource_path, data_root=data_root)
        environment = load_json(environment_path, "v0.2.8 environment manifest")
        validate_environment_manifest(
            environment,
            repository_root=root,
            resource_manifest_sha256=hash_file(resource_path, "sha256"),
        )
    except (TrustedDataError, OSError) as error:
        failures.append(str(error))
        resources = {}
        environment = {}
    return {
        **repository,
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "predecessors_loaded": False,
        "data_root_identity": identity,
        "resource_manifest": resources,
        "environment_manifest": environment,
    }


def _require_ioc_run_id(value: Any, label: str) -> str:
    run_id = require_nonempty_string(value, label)
    if not run_id.startswith("pilot2-ioc-"):
        raise TrustedDataError(f"{label} is not a Pilot 2 IOC run ID")
    return run_id


def _validate_ioc_expected_accounting(value: Any, label: str) -> dict[str, int]:
    accounting = require_exact_keys(value, IOC_EXPECTED_ACCOUNTING, label)
    normalized: dict[str, int] = {}
    for key, expected in IOC_EXPECTED_ACCOUNTING.items():
        observed = require_type(accounting[key], int, f"{label}.{key}")
        if observed != expected:
            raise TrustedDataError(f"{label}.{key} differs from the fixed accounting")
        normalized[key] = observed
    return normalized


def _validate_ioc_data_root_binding(
    value: Any,
    *,
    label: str,
    include_path: bool,
) -> dict[str, str]:
    expected = {"data_root_id", "marker_sha256"}
    if include_path:
        expected.add("canonical_path")
    root = require_exact_keys(value, expected, label)
    normalized = {
        "data_root_id": require_nonempty_string(root["data_root_id"], f"{label}.data_root_id"),
        "marker_sha256": require_sha256(root["marker_sha256"], f"{label}.marker_sha256"),
    }
    if include_path:
        canonical = require_nonempty_string(root["canonical_path"], f"{label}.canonical_path")
        path = Path(canonical)
        if (
            not path.is_absolute()
            or path == Path(path.anchor)
            or str(path) != canonical
            or ".." in path.parts
        ):
            raise TrustedDataError(f"{label}.canonical_path is not a normalized absolute path")
        normalized = {"canonical_path": canonical, **normalized}
    return normalized


def validate_ioc_science_execution_binding(
    value: Any,
    *,
    ioc_run_id: str,
) -> dict[str, Any]:
    """Validate the external IOC-to-science binding without opening its data root."""

    expected_run_id = _require_ioc_run_id(ioc_run_id, "expected IOC run ID")
    if isinstance(value, Mapping):
        value = dict(value)
    binding = require_exact_keys(value, IOC_SCIENCE_BINDING_KEYS, "IOC science binding")
    bound_run_id = _require_ioc_run_id(binding["ioc_run_id"], "IOC science binding.ioc_run_id")
    if bound_run_id != expected_run_id:
        raise TrustedDataError("IOC science binding run ID differs")
    if binding["schema"] != IOC_SCIENCE_BINDING_SCHEMA:
        raise TrustedDataError("IOC science binding schema is invalid")
    if binding["module_release_id"] != IOC_MODULE_RELEASE_ID:
        raise TrustedDataError("IOC science binding module release differs")
    if binding["science_run_id"] != IOC_SCIENCE_RUN_ID:
        raise TrustedDataError("IOC science binding inner run ID differs")
    execution_freeze_sha256 = require_sha256(
        binding["execution_freeze_sha256"],
        "IOC science binding.execution_freeze_sha256",
    )
    inventory_sha256 = require_sha256(
        binding["inventory_sha256"], "IOC science binding.inventory_sha256"
    )
    if inventory_sha256 != INVENTORY_SHA256:
        raise TrustedDataError("IOC science binding inventory differs")
    accounting = _validate_ioc_expected_accounting(
        binding["expected_accounting"], "IOC science binding.expected_accounting"
    )
    data_root = _validate_ioc_data_root_binding(
        binding["science_data_root"],
        label="IOC science binding.science_data_root",
        include_path=True,
    )
    if binding["fresh_only"] is not True:
        raise TrustedDataError("IOC science binding is not fresh-only")
    if binding["resume_authorized"] is not False:
        raise TrustedDataError("IOC science binding authorizes resume")
    return {
        "schema": IOC_SCIENCE_BINDING_SCHEMA,
        "ioc_run_id": bound_run_id,
        "module_release_id": IOC_MODULE_RELEASE_ID,
        "science_run_id": IOC_SCIENCE_RUN_ID,
        "execution_freeze_sha256": execution_freeze_sha256,
        "inventory_sha256": INVENTORY_SHA256,
        "expected_accounting": accounting,
        "science_data_root": data_root,
        "fresh_only": True,
        "resume_authorized": False,
    }


def _validate_ioc_execution_freeze(freeze: Any, *, root: Path) -> list[str]:
    failures: list[str] = []
    try:
        item = require_exact_keys(freeze, IOC_EXECUTION_FREEZE_KEYS, "IOC execution freeze")
        if item["schema"] != IOC_EXECUTION_FREEZE_SCHEMA:
            failures.append("IOC execution freeze schema is invalid")
        if item["freeze_id"] != IOC_EXECUTION_FREEZE_ID:
            failures.append("IOC execution freeze ID is invalid")
        require_nonempty_string(item["recorded_utc"], "IOC execution freeze.recorded_utc")
        if item["status"] != IOC_EXECUTION_FREEZE_STATUS:
            failures.append("IOC execution freeze status is invalid")
        require_nonempty_string(item["scope"], "IOC execution freeze.scope")
        require_nonempty_string(
            item["user_authorization"], "IOC execution freeze.user_authorization"
        )
        if item["execution_authorized"] is not True:
            failures.append("IOC execution freeze does not authorize execution")
        _require_ioc_run_id(item["ioc_run_id"], "IOC execution freeze.ioc_run_id")
        if item["module_id"] != IOC_MODULE_ID:
            failures.append("IOC execution freeze module ID differs")
        if item["module_release_id"] != IOC_MODULE_RELEASE_ID:
            failures.append("IOC execution freeze module release differs")
        if item["science_run_id"] != IOC_SCIENCE_RUN_ID:
            failures.append("IOC execution freeze inner run ID differs")
        if item["inventory_sha256"] != INVENTORY_SHA256:
            failures.append("IOC execution freeze inventory differs")
        _validate_ioc_expected_accounting(
            item["expected_accounting"], "IOC execution freeze.expected_accounting"
        )
        _validate_ioc_data_root_binding(
            item["science_data_root"],
            label="IOC execution freeze.science_data_root",
            include_path=False,
        )
        expected_hashes = {
            "implementation_sha256": implementation_sha256(root),
            "science_control_sha256": science_control_sha256(root),
        }
        _, _, runner = load_science_controls(root)
        resource_path = root / runner["manifests"]["resource"]
        environment_path = root / runner["manifests"]["environment"]
        expected_hashes.update(
            {
                "environment_manifest_sha256": hash_file(environment_path, "sha256"),
                "resource_manifest_sha256": hash_file(resource_path, "sha256"),
            }
        )
        for key, expected in expected_hashes.items():
            require_sha256(item[key], f"IOC execution freeze.{key}")
            if item[key] != expected:
                failures.append(f"IOC execution freeze {key} differs")
        threshold_lock_sha256 = require_sha256(
            item["threshold_lock_sha256"], "IOC execution freeze.threshold_lock_sha256"
        )
        if threshold_lock_sha256 != runner["predecessor_bindings"]["threshold_lock"]["sha256"]:
            failures.append("IOC execution freeze threshold-lock binding differs")
        launch = require_exact_keys(
            item["launch_contract"], IOC_LAUNCH_CONTRACT, "IOC execution freeze.launch_contract"
        )
        if any(
            type(launch[key]) is not type(expected) or launch[key] != expected
            for key, expected in IOC_LAUNCH_CONTRACT.items()
        ):
            failures.append("IOC execution freeze launch contract differs")
        if item["fresh_only"] is not True:
            failures.append("IOC execution freeze is not fresh-only")
        if item["resume_authorized"] is not False:
            failures.append("IOC execution freeze authorizes resume")
        for boundary in (
            "observed_residual_access_authorized",
            "observed_periodic_search_authorized",
            "promotion_grade_authorized",
            "discovery_claim_authorized",
        ):
            if item[boundary] is not False:
                failures.append(f"IOC execution freeze boundary invalid: {boundary}")
        if item["stop_rule"] != IOC_STOP_RULE:
            failures.append("IOC execution freeze stop rule differs")
        frozen = validate_hash_map(item["frozen_sha256"], "IOC execution freeze.frozen_sha256")
        expected_frozen_paths = set(runner["implementation_paths"]) | {
            "src/pulsar_pilot/pilot2_ioc_harness.py",
            "src/pulsar_pilot/pilot2_science_module.py",
            *CURRENT_IMPLEMENTATION_PATHS,
        }
        failures.extend(
            verify_exact_repository_hashes(
                root,
                frozen,
                expected_frozen_paths,
                "IOC execution",
            )
        )
    except (TrustedDataError, KeyError, OSError) as error:
        failures.append(str(error))
    return failures


def _ioc_binding_from_mapping(binding: Mapping[str, Any]) -> dict[str, Any]:
    candidate = dict(binding)
    run_id = _require_ioc_run_id(candidate.get("ioc_run_id"), "IOC science binding.ioc_run_id")
    return validate_ioc_science_execution_binding(candidate, ioc_run_id=run_id)


def verify_ioc_science_execution_authorization(
    binding: Mapping[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Verify successor repository authority without touching the external data root."""

    root = root or repository_root()
    failures: list[str] = []
    legacy_path = root / EXECUTION_FREEZE_PATH
    if legacy_path.exists() or legacy_path.is_symlink():
        failures.append("legacy v0.2.8 execution freeze must remain absent")
    path = root / IOC_EXECUTION_FREEZE_PATH
    if not path.exists() and not path.is_symlink():
        return {
            "status": "fail" if failures else "locked",
            "failures": failures + ["Separate IOC science execution freeze is absent"],
            "predecessors_loaded": False,
        }
    if path.is_symlink() or not path.is_file():
        return {
            "status": "fail",
            "failures": failures + ["IOC science execution freeze is not a regular file"],
            "predecessors_loaded": False,
        }
    try:
        freeze_sha256 = hash_file(path, "sha256")
    except OSError as error:
        return {
            "status": "fail",
            "failures": failures + [f"IOC science execution freeze is unreadable: {error}"],
            "predecessors_loaded": False,
        }
    freeze: dict[str, Any] = {}
    normalized_binding: dict[str, Any] | None = None
    try:
        freeze = load_json(path, "IOC science execution freeze")
        failures.extend(_validate_ioc_execution_freeze(freeze, root=root))
        if binding is not None:
            normalized_binding = _ioc_binding_from_mapping(binding)
            if normalized_binding["execution_freeze_sha256"] != freeze_sha256:
                failures.append("IOC science binding execution-freeze hash differs")
            comparisons = {
                "ioc_run_id": normalized_binding["ioc_run_id"],
                "module_release_id": normalized_binding["module_release_id"],
                "science_run_id": normalized_binding["science_run_id"],
                "inventory_sha256": normalized_binding["inventory_sha256"],
                "expected_accounting": normalized_binding["expected_accounting"],
                "fresh_only": normalized_binding["fresh_only"],
                "resume_authorized": normalized_binding["resume_authorized"],
            }
            for key, expected in comparisons.items():
                if freeze.get(key) != expected:
                    failures.append(f"IOC science binding differs from freeze: {key}")
            bound_root = normalized_binding["science_data_root"]
            frozen_root = freeze.get("science_data_root")
            if not isinstance(frozen_root, Mapping) or {
                "data_root_id": bound_root["data_root_id"],
                "marker_sha256": bound_root["marker_sha256"],
            } != dict(frozen_root):
                failures.append("IOC science binding data-root identity differs from freeze")
    except (TrustedDataError, KeyError, OSError) as error:
        failures.append(str(error))
    result = {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "predecessors_loaded": False,
        "freeze_sha256": freeze_sha256,
        "freeze": freeze,
    }
    if normalized_binding is not None:
        result["binding"] = normalized_binding
    return result


def verify_ioc_science_execution_gate(
    data_root: Path | None,
    binding: Mapping[str, Any],
    root: Path | None = None,
) -> dict[str, Any]:
    """Verify the successor gate using only the explicitly bound external root."""

    root = root or repository_root()
    repository = verify_ioc_science_execution_authorization(binding, root)
    if repository["status"] != "pass":
        return repository
    normalized = repository["binding"]
    if data_root is None:
        return {
            **repository,
            "status": "fail",
            "failures": ["Authorized IOC science execution requires an explicit data root"],
            "predecessors_loaded": False,
        }
    supplied = Path(data_root)
    bound_path = Path(normalized["science_data_root"]["canonical_path"])
    if not supplied.is_absolute() or str(supplied) != str(bound_path):
        return {
            **repository,
            "status": "fail",
            "failures": ["explicit data root differs from the IOC science binding"],
            "predecessors_loaded": False,
        }
    failures: list[str] = []
    try:
        if supplied.is_symlink() or not supplied.is_dir():
            raise TrustedDataError("explicit IOC science data root is not a real directory")
        resolved = supplied.resolve(strict=True)
        if str(resolved) != normalized["science_data_root"]["canonical_path"]:
            raise TrustedDataError("IOC science data root is not canonical")
        identity = verify_data_root_identity(resolved, repository["freeze"]["science_data_root"])
        if identity["status"] != "pass":
            return {
                **repository,
                "status": "fail",
                "failures": identity["failures"],
                "predecessors_loaded": False,
                "data_root_identity": identity,
                "resource_manifest": {},
                "environment_manifest": {},
            }
        _, _, runner = load_science_controls(root)
        resource_path = root / runner["manifests"]["resource"]
        environment_path = root / runner["manifests"]["environment"]
        resources = load_resource_manifest(resource_path, data_root=resolved)
        environment = load_json(environment_path, "IOC science environment manifest")
        validate_environment_manifest(
            environment,
            repository_root=root,
            resource_manifest_sha256=hash_file(resource_path, "sha256"),
        )
    except (TrustedDataError, OSError) as error:
        failures.append(str(error))
        identity = {}
        resources = {}
        environment = {}
    return {
        **repository,
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "predecessors_loaded": False,
        "data_root_identity": identity,
        "resource_manifest": resources,
        "environment_manifest": environment,
    }


def execution_binding_sha256(
    *,
    implementation_hash: str,
    execution_freeze_sha256: str,
    threshold_lock_sha256: str,
    inventory_sha256: str,
    science_control_hash: str,
    environment_manifest_sha256: str,
    resource_manifest_sha256: str,
    input_binding_sha256: str,
) -> str:
    return canonical_sha256(
        {
            "implementation_sha256": implementation_hash,
            "execution_freeze_sha256": execution_freeze_sha256,
            "threshold_lock_sha256": threshold_lock_sha256,
            "inventory_sha256": inventory_sha256,
            "science_control_sha256": science_control_hash,
            "environment_manifest_sha256": environment_manifest_sha256,
            "resource_manifest_sha256": resource_manifest_sha256,
            "input_binding_sha256": input_binding_sha256,
        }
    )


def ioc_execution_binding_sha256(
    *,
    implementation_hash: str,
    execution_freeze_sha256: str,
    threshold_lock_sha256: str,
    inventory_sha256: str,
    science_control_hash: str,
    environment_manifest_sha256: str,
    resource_manifest_sha256: str,
    input_binding_sha256: str,
    ioc_manifest_sha256: str,
    ioc_run_id: str,
) -> str:
    """Bind the inner science execution to one exact outer IOC attempt."""

    values = {
        "implementation_sha256": implementation_hash,
        "execution_freeze_sha256": execution_freeze_sha256,
        "threshold_lock_sha256": threshold_lock_sha256,
        "inventory_sha256": inventory_sha256,
        "science_control_sha256": science_control_hash,
        "environment_manifest_sha256": environment_manifest_sha256,
        "resource_manifest_sha256": resource_manifest_sha256,
        "input_binding_sha256": input_binding_sha256,
        "ioc_manifest_sha256": ioc_manifest_sha256,
    }
    for key, digest in values.items():
        require_sha256(digest, f"IOC execution binding.{key}")
    if inventory_sha256 != INVENTORY_SHA256:
        raise TrustedDataError("IOC execution binding inventory differs")
    run_id = _require_ioc_run_id(ioc_run_id, "IOC execution binding.ioc_run_id")
    return canonical_sha256(
        {
            **values,
            "ioc_run_id": run_id,
            "module_release_id": IOC_MODULE_RELEASE_ID,
            "science_run_id": IOC_SCIENCE_RUN_ID,
        }
    )
