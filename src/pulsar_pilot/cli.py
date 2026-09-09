from __future__ import annotations

import argparse
import json
from pathlib import Path

from .acquire import download_archive, extract_target
from .c0 import run_c0
from .c1 import run_c1
from .c1r1 import run_c1_r1
from .c2 import run_c2
from .c3 import run_c3
from .config import load_pilot_config, load_yaml
from .g2 import run_g2
from .machine import write_manifest
from .paths import (
    configured_data_root,
    initialize_data_root,
    repository_root,
    require_initialized_data_root,
)
from .pilot1 import build_pilot1_plan_summary, evaluate_v01_promotion
from .pilot1_runtime import (
    build_pilot1_case_inventory,
    inventory_summary,
    run_pilot1_preflight,
)
from .precision import assert_precision, format_report
from .provenance import verify_sha256_manifest
from .smoke import run_smoke


def _config_path() -> Path:
    return repository_root() / "config" / "target.yaml"


def command_validate_config(_: argparse.Namespace) -> int:
    config = load_pilot_config(_config_path())
    injections = load_yaml(repository_root() / "config" / "injections.yaml")
    ids = [case["id"] for case in injections.get("cases", [])]
    if ids != ["C0", "C1", "C2", "C3"]:
        raise RuntimeError(f"Unexpected frozen case order: {ids}")
    print(json.dumps({"target": config.target_name, "cases": ids, "status": "pass"}, indent=2))
    return 0


def command_precision(_: argparse.Namespace) -> int:
    print(format_report(assert_precision()))
    return 0


def command_init_root(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    initialize_data_root(root)
    print(json.dumps({"status": "initialized", "data_root": str(root)}, indent=2))
    return 0


def command_machine(args: argparse.Namespace) -> int:
    payload = write_manifest(Path(args.output))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_download(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = download_archive(load_pilot_config(_config_path()), root)
    printable = {key: str(value) if isinstance(value, Path) else value for key, value in result.items()}
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


def command_extract(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = extract_target(load_pilot_config(_config_path()), root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_smoke(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = run_smoke(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_verify_data(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    manifest = repository_root() / "manifests" / "files.sha256"
    result = verify_sha256_manifest(manifest, root)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "pass":
        raise RuntimeError("Controlled-data hash verification failed")
    return 0


def command_g2(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = run_g2(load_pilot_config(_config_path()), root)
    summary = {
        "status": result["status"],
        "gate": result["gate"],
        "criteria": result["criteria"],
        "fit": result["fit"],
        "parameter_comparison": {
            key: value
            for key, value in result["parameter_comparison"].items()
            if key != "parameters"
        },
        "warnings": result["warnings"],
        "resources": result["resources"],
        "outputs": result["outputs"],
        "injection_authorized": result["injection_authorized"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


def command_c0(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = run_c0(
        load_pilot_config(_config_path()),
        load_yaml(repository_root() / "config" / "injections.yaml"),
        root,
    )
    summary = {
        "status": result["status"],
        "case": result["case"],
        "criteria": result["criteria"],
        "injection": result["injection"],
        "refit": result["refit"],
        "trigger": result["trigger"],
        "warnings": result["warnings"],
        "resources": result["resources"],
        "outputs": result["outputs"],
        "blocked_cases": result["blocked_cases"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


def command_c1(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = run_c1(
        load_pilot_config(_config_path()),
        load_yaml(repository_root() / "config" / "injections.yaml"),
        root,
    )
    summary = {
        "status": result["status"],
        "case": result["case"],
        "criteria": result["criteria"],
        "injection": result["injection"],
        "blind_unmodeled_refit": result["blind_unmodeled_refit"],
        "blind_trigger": result["blind_trigger"],
        "joint_wavex": result["joint_wavex"],
        "transfer": result["transfer"],
        "warnings": result["warnings"],
        "resources": result["resources"],
        "outputs": result["outputs"],
        "blocked_cases": result["blocked_cases"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


def command_c1_r1(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = run_c1_r1(
        load_pilot_config(_config_path()),
        load_yaml(repository_root() / "config" / "injections.yaml"),
        root,
    )
    summary = {
        "status": result["status"],
        "case": result["case"],
        "scorecard": result["scorecard"],
        "criteria": result["criteria"],
        "injection": result["injection"],
        "ordinary_refit": result["ordinary_refit"],
        "frequency_diagnostic": result["frequency_diagnostic"],
        "compatible_joint_recovery": result["compatible_joint_recovery"],
        "independent_full_covariance_crosscheck": result[
            "independent_full_covariance_crosscheck"
        ],
        "warnings": result["warnings"],
        "resources": result["resources"],
        "outputs": result["outputs"],
        "blocked_cases": result["blocked_cases"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


def command_c2(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = run_c2(
        load_pilot_config(_config_path()),
        load_yaml(repository_root() / "config" / "injections.yaml"),
        root,
    )
    summary = {
        "status": result["status"],
        "case": result["case"],
        "scorecard": result["scorecard"],
        "hard_criteria": result["hard_criteria"],
        "diagnostic_outcomes": result["diagnostic_outcomes"],
        "injection": result["injection"],
        "ordinary_refit": result["ordinary_refit"],
        "frequency_diagnostic": result["frequency_diagnostic"],
        "compatible_joint_recovery": result["compatible_joint_recovery"],
        "independent_full_covariance_crosscheck": result[
            "independent_full_covariance_crosscheck"
        ],
        "warnings": result["warnings"],
        "resources": result["resources"],
        "outputs": result["outputs"],
        "blocked_cases": result["blocked_cases"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


def command_c3(args: argparse.Namespace) -> int:
    root = configured_data_root(args.data_root)
    require_initialized_data_root(root)
    result = run_c3(
        load_pilot_config(_config_path()),
        load_yaml(repository_root() / "config" / "injections.yaml"),
        root,
    )
    summary = {
        "status": result["status"],
        "case": result["case"],
        "scorecard": result["scorecard"],
        "hard_criteria": result["hard_criteria"],
        "diagnostic_outcomes": result["diagnostic_outcomes"],
        "injection": result["injection"],
        "ordinary_refits": result["ordinary_refits"],
        "frequency_diagnostic": result["frequency_diagnostic"],
        "compatible_joint_recovery": result["compatible_joint_recovery"],
        "independent_full_covariance_crosscheck": result[
            "independent_full_covariance_crosscheck"
        ],
        "warnings": result["warnings"],
        "resources": result["resources"],
        "outputs": result["outputs"],
        "pilot0_injection_cases_complete": result["pilot0_injection_cases_complete"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


def command_pilot1_plan(args: argparse.Namespace) -> int:
    plan = load_yaml(repository_root() / "config" / "pilot1.yaml")
    result = build_pilot1_plan_summary(plan)
    if args.metrics:
        result["promotion_evaluation"] = evaluate_v01_promotion(
            plan, load_yaml(Path(args.metrics))
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_pilot1_inventory(args: argparse.Namespace) -> int:
    plan = load_yaml(repository_root() / "config" / "pilot1.yaml")
    inventory = build_pilot1_case_inventory(plan)
    result = inventory if args.full else inventory_summary(inventory)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_pilot1_preflight(args: argparse.Namespace) -> int:
    data_root = configured_data_root(args.data_root)
    require_initialized_data_root(data_root)
    result = run_pilot1_preflight(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pulsar-pilot")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-config")
    validate.set_defaults(func=command_validate_config)
    precision = sub.add_parser("precision-check")
    precision.set_defaults(func=command_precision)
    init_root = sub.add_parser("init-data-root")
    init_root.add_argument("--data-root")
    init_root.set_defaults(func=command_init_root)
    machine = sub.add_parser("machine-manifest")
    machine.add_argument("--output", required=True)
    machine.set_defaults(func=command_machine)
    download = sub.add_parser("download")
    download.add_argument("--data-root")
    download.set_defaults(func=command_download)
    extract = sub.add_parser("extract-target")
    extract.add_argument("--data-root")
    extract.set_defaults(func=command_extract)
    smoke = sub.add_parser("smoke-load")
    smoke.add_argument("--data-root")
    smoke.set_defaults(func=command_smoke)
    verify_data = sub.add_parser("verify-data")
    verify_data.add_argument("--data-root")
    verify_data.set_defaults(func=command_verify_data)
    g2 = sub.add_parser("g2-refit")
    g2.add_argument("--data-root")
    g2.set_defaults(func=command_g2)
    c0 = sub.add_parser("c0-matched-null")
    c0.add_argument("--data-root")
    c0.set_defaults(func=command_c0)
    c1 = sub.add_parser("c1-positive-control")
    c1.add_argument("--data-root")
    c1.set_defaults(func=command_c1)
    c1_r1 = sub.add_parser("c1-r1-corrective-control")
    c1_r1.add_argument("--data-root")
    c1_r1.set_defaults(func=command_c1_r1)
    c2 = sub.add_parser("c2-boundary-control")
    c2.add_argument("--data-root")
    c2.set_defaults(func=command_c2)
    c3 = sub.add_parser("c3-annual-stress")
    c3.add_argument("--data-root")
    c3.set_defaults(func=command_c3)
    pilot1 = sub.add_parser("pilot1-plan")
    pilot1.add_argument("--metrics")
    pilot1.set_defaults(func=command_pilot1_plan)
    pilot1_inventory = sub.add_parser("pilot1-inventory")
    pilot1_inventory.add_argument("--full", action="store_true")
    pilot1_inventory.set_defaults(func=command_pilot1_inventory)
    pilot1_preflight = sub.add_parser("pilot1-preflight")
    pilot1_preflight.add_argument("--data-root")
    pilot1_preflight.set_defaults(func=command_pilot1_preflight)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
