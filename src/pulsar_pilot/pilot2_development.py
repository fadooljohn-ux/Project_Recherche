"""Small real integration fixture using the production numerical functions."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .paths import repository_root
from .pilot1_runtime import ResumableArtifactLedger
from .pilot2_durable_ledger import SingleWriterLock, durable_atomic_json
from .pilot2_injection_remediation import build_remediation_inventory
from .pilot2_injection_remediation_v023 import build_v023_inventory
from .pilot2_offline_resources import OfflineRuntimeBoundary, validate_environment_manifest
from .pilot2_runtime_core import (
    execute_injection_case,
    prepare_context,
    validate_complete_case_record,
)
from .pilot2_trusted_data import canonical_sha256, load_yaml
from .provenance import hash_file
from .runtime_limits import RuntimeLimits


def development_cases() -> list[dict[str, Any]]:
    """Fixed strong representatives, with IDs/seeds disjoint from formal inventories."""
    inventory = build_v023_inventory()["cases"]
    old = build_remediation_inventory(
        load_yaml(repository_root() / "config/pilot2_calibration_v0.2.1.yaml"),
        load_yaml(repository_root() / "config/pilot2_injection_remediation_v0.2.2.yaml"),
    )["cases"]
    formal_seeds = {c["seed"] for c in inventory + old}
    cases = []
    for family in ("main", "phase_reference", "annual", "boundary"):
        candidates = [c for c in inventory if c["family"] == family]
        if family == "annual":
            candidates = [c for c in candidates if c["period_days"] == 365.25]
        case = dict(max(candidates, key=lambda c: (c["amplitude_microseconds"], -c["period_days"])))
        case["case_id"] = f"recherche-dev-20260907-{family}"
        if family == "annual":
            case["case_id"] += "-365d"
        case["seed"] = (
            int.from_bytes(hashlib.sha256(case["case_id"].encode()).digest()[:8], "big") % 2**63
        )
        if case["seed"] in formal_seeds:
            raise RuntimeError("Development seed overlaps a formal inventory")
        cases.append(case)
    return cases


def solver_check_cases() -> list[dict[str, Any]]:
    """The two retained annual fixtures and one ordinary comparison control."""
    selected = [c for c in development_cases() if c["family"] in {"main", "annual"}]
    annual_pi = next(c for c in selected if c["family"] == "annual").copy()
    annual_pi["case_id"] = "recherche-dev-annual-diagnosis-20260908-pi"
    annual_pi["phase_radians"] = math.pi
    annual_pi["seed"] = (
        int.from_bytes(hashlib.sha256(annual_pi["case_id"].encode()).digest()[:8], "big") % 2**63
    )
    if annual_pi["seed"] in {c["seed"] for c in build_v023_inventory()["cases"]}:
        raise RuntimeError("Annual solver fixture overlaps formal inventory")
    return selected + [annual_pi]


def verify_inputs(root: Path) -> None:
    marker = json.loads((root / ".project-recherche-data-root.json").read_text())
    if marker.get("data_root_id") != "recherche-rehabilitation-20260907":
        raise RuntimeError("Development requires the isolated rehabilitation root")
    spec = json.loads((repository_root() / "config/rehabilitation_inputs.json").read_text())
    for item in spec["inputs"]:
        path = root / item["path"]
        if (
            not path.is_file()
            or path.is_symlink()
            or not path.resolve().is_relative_to(root)
            or hash_file(path, "sha256") != item["sha256"]
        ):
            raise RuntimeError(f"Controlled input differs: {item['path']}")
    environment = json.loads((root / "metadata/development-environment.json").read_text())
    validate_environment_manifest(
        environment,
        repository_root=repository_root(),
        resource_manifest_sha256=hash_file(root / "metadata/resources.json", "sha256"),
        verify_live=True,
    )


def execute_development(
    run_root: Path,
    manifest: Mapping[str, Any],
    publish_status: Callable[..., Any],
) -> Mapping[str, Any]:
    root = Path(manifest["data_root"]).resolve(strict=True)
    if (
        manifest.get("mode") != "development"
        or manifest.get("formal_qualification") is not False
        or not manifest["cases"]
        or any(case not in development_cases() + solver_check_cases() for case in manifest["cases"])
        or len({case["case_id"] for case in manifest["cases"]}) != len(manifest["cases"])
        or run_root.resolve() != root / "development-runs" / manifest["run_id"]
    ):
        raise RuntimeError("Development manifest differs from the fixed fixture")
    verify_inputs(root)
    for relative, expected in manifest["source_sha256"].items():
        if hash_file(repository_root() / relative, "sha256") != expected:
            raise RuntimeError(f"Source changed after preparation: {relative}")
    cases = manifest["cases"]
    resources = json.loads((root / "metadata/resources.json").read_text())
    if hash_file(root / "metadata/resources.json", "sha256") != manifest["resources_sha256"]:
        raise RuntimeError("Resource manifest changed after preparation")
    base = load_yaml(repository_root() / "config/pilot2_calibration_v0.2.1.yaml")
    threshold = json.loads(
        (root / "run_records/pilot2/calibration-threshold-lock-v0.2.1.json").read_text()
    )
    threshold_value = float(threshold["value_delta_chi2"])
    binding = canonical_sha256(dict(manifest))
    counts = {"cases": 0, "random_draws": 0, "scans": 0, "primary_fits": 0, "solver_audits": 0}
    ledger = ResumableArtifactLedger(run_root / "ledger.json", canonical_sha256(cases), binding)
    limits = RuntimeLimits(root, wall_seconds=3600, rss_gib=16, disk_gib=1.5)

    def progress() -> None:
        durable_atomic_json(run_root / "accounting.json", counts)
        publish_status(
            stage="run", completed=counts["cases"], total=len(cases), checkpoint=counts["cases"]
        )

    def operation(name: str) -> None:
        counts[name] += 1
        progress()
        limits.check()

    records = []
    with SingleWriterLock(root), OfflineRuntimeBoundary(root, resources) as boundary:
        limits.check(disk=True)
        progress()
        context = prepare_context(
            root,
            cases,
            resource_manifest=resources,
            resource_manifest_sha256=manifest["resources_sha256"],
            environment_manifest_sha256=manifest["environment_sha256"],
            setup_log_relative=str((run_root / "context.log").relative_to(root)),
            resource_boundary=boundary,
        )
        durable_atomic_json(run_root / "input-binding.json", context.input_binding)
        for case in cases:
            limits.check(disk=True)
            audit = case["family"] in {"main", "annual"}
            record = execute_injection_case(
                context, case, threshold_value, audit, base, binding, on_operation=operation
            )
            if case["family"] != "annual":
                record["candidate_eligible"] = True
            validate_complete_case_record(
                record,
                case=case,
                execution_binding=binding,
                threshold_delta_chi2=threshold_value,
                audit_required=audit,
                trusted_input_binding=context.input_binding,
            )
            record["run_id"] = manifest["run_id"]
            record["development_only"] = True
            path = run_root / "cases" / f"{case['case_id']}.json"
            durable_atomic_json(path, record)
            ledger.record(case["case_id"], path, root)
            records.append(record)
            counts["cases"] += 1
            progress()
        trace = boundary.verify_trace()
    durable_atomic_json(run_root / "resource-trace.json", trace)
    expected = {
        "cases": len(cases),
        "random_draws": len(cases),
        "scans": len(cases),
        "primary_fits": 2 * len(cases),
        "solver_audits": sum(c["family"] in {"main", "annual"} for c in cases),
    }
    if counts != expected or ledger.verify(root)["status"] != "pass":
        raise RuntimeError("Development execution or artifact accounting differs")
    checks = {
        "all_fits_converged": all(
            r["ordinary_fit_converged"] and r["joint_fit_converged"] for r in records
        ),
        "solver_audits_passed": all(r["solver_audit_pass"] for r in records),
        "offline_resources_verified": trace["status"] == "pass",
        "case_records_valid": True,
    }
    durable_atomic_json(
        run_root / "development-result.json",
        {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "accounting": counts,
            "formal_qualification": False,
            "scope": "selected development fixtures; no population recovery or discovery claim",
            "case_artifacts": [f"cases/{c['case_id']}.json" for c in cases],
        },
    )
    if not all(checks.values()):
        raise RuntimeError(f"Development numerical checks failed: {checks}")
    return {"completed": counts["cases"], "total": len(cases), "checkpoint": counts["cases"]}
