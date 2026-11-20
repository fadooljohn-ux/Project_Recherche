from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_yaml
from .injection_integrity import (
    DM_ERROR_KEY,
    TOA_ADJUSTMENT_KEY,
    UNCENTERED_TARGET_KEY,
    classify_injection_warning_lines,
)
from .paths import (
    MARKER_NAME,
    MARKER_PROJECT,
    configured_data_root,
    repository_root,
)
from .pilot1_benchmark import _directory_size_gib, _peak_rss_gib
from .pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner
from .pilot2_calibration_runtime import (
    CalibrationLedger,
    HeartbeatService,
    _utc_now,
)
from .pilot2_injection_executor import HEARTBEAT_INTERVAL_SECONDS, InjectionContext
from .pilot2_injection_executor_v027 import (
    RECORD_RUN_ID,
    RECORD_SCHEMA_VERSION,
    execute_injection_case,
)
from .pilot2_injection_remediation import BASE_CONFIG_PATH
from .pilot2_injection_remediation_v023 import (
    CONFIG_PATH as REMEDIATION_CONFIG_PATH,
)
from .pilot2_injection_remediation_v023 import (
    build_v023_inventory,
    verify_remediation_freeze,
)
from .pilot2_injection_runner_v022 import _gate, grade_records
from .pilot2_preflight import _load_release, _network_disabled
from .provenance import hash_file, logical_path

RUNNER_CONFIG_PATH = "config/pilot2_injection_runner_v0.2.7.yaml"
IMPLEMENTATION_FREEZE_PATH = "protocol/PILOT2_INJECTION_RUNNER_FREEZE_v0.2.7.json"
READINESS_FREEZE_PATH = "protocol/PILOT2_INJECTION_EXECUTION_READINESS_FREEZE_v0.2.7.json"
EXECUTION_FREEZE_PATH = "protocol/PILOT2_INJECTION_EXECUTION_FREEZE_v0.2.7.json"
STAGE = "injection_remediation_evaluation"
RUN_ID = "pilot2-b1937-injection-remediation-v0.2.7"
EXPECTED_AUTHORIZED_CASE_COUNTS = {
    "main": 240,
    "phase_reference": 60,
    "annual": 28,
    "boundary": 16,
    "solver_audits": 35,
}
IMPLEMENTATION_PATHS = (
    "src/pulsar_pilot/pilot2_injection_runner_v027.py",
    "src/pulsar_pilot/pilot2_injection_executor_v027.py",
    "src/pulsar_pilot/pilot2_injection_executor_v023.py",
    "src/pulsar_pilot/pilot2_injection_remediation_v023.py",
    "src/pulsar_pilot/pilot2_injection_runner_v022.py",
    "src/pulsar_pilot/pilot2_injection_remediation.py",
    "src/pulsar_pilot/injection_integrity.py",
    "src/pulsar_pilot/c1.py",
    "src/pulsar_pilot/c1r1.py",
    "src/pulsar_pilot/c3.py",
    "src/pulsar_pilot/pilot1_benchmark.py",
    "src/pulsar_pilot/pilot1_runtime.py",
    "src/pulsar_pilot/pilot2_preflight.py",
    "src/pulsar_pilot/pilot2_calibration_runtime.py",
)
IMPLEMENTATION_FREEZE_FROZEN_PATHS = (
    "config/pilot2_injection_runner_v0.2.7.yaml",
    "docs/PILOT2_SCIENCE_STAGE_NORTH_STAR.md",
    "protocol/PILOT2_INJECTION_RUNNER_PROTOCOL_v0.2.7.md",
    "results/pilot2/injection_v027_audit_finding_closure.json",
    "results/pilot2/injection_validation_manifest_v0.2.7.json",
    "src/pulsar_pilot/pilot2_injection_executor_v027.py",
    "src/pulsar_pilot/pilot2_injection_runner_v027.py",
    "tests/test_pilot2_injection_runner_v027.py",
)
READINESS_FREEZE_FROZEN_PATHS = (
    "docs/PILOT2_INJECTION_EXECUTION_READINESS_v0.2.7.md",
    "docs/PILOT2_SCIENCE_STAGE_NORTH_STAR.md",
    "protocol/PILOT2_INJECTION_RUNNER_FREEZE_v0.2.7.json",
    "results/pilot2/injection_execution_readiness_v0.2.7.json",
    "results/pilot2/injection_runner_zero_science_validation_v0.2.7.json",
    "results/pilot2/injection_v027_audit_finding_closure.json",
    "results/pilot2/injection_validation_manifest_v0.2.7.json",
    "src/pulsar_pilot/pilot2_injection_executor_v027.py",
    "src/pulsar_pilot/pilot2_injection_runner_v027.py",
    "tests/test_pilot2_injection_runner_v027.py",
)
EXECUTION_FREEZE_FROZEN_PATHS = (
    "config/pilot2_injection_runner_v0.2.7.yaml",
    "docs/PILOT2_INJECTION_EXECUTION_READINESS_v0.2.7.md",
    "docs/PILOT2_SCIENCE_STAGE_NORTH_STAR.md",
    "docs/audits/DEDICATED_SOL_AUDIT_PILOT2_v0.2.7_2026-08-11.md",
    "protocol/DEDICATED_SOL_AUDIT_RECORD_PILOT2_v0.2.7.json",
    "protocol/PILOT2_INJECTION_EXECUTION_READINESS_FREEZE_v0.2.7.json",
    "protocol/PILOT2_INJECTION_REMEDIATION_FREEZE_v0.2.3.json",
    "protocol/PILOT2_INJECTION_RUNNER_FREEZE_v0.2.7.json",
    "protocol/PILOT2_INJECTION_RUNNER_PROTOCOL_v0.2.7.md",
    "results/pilot2/dedicated_sol_audit_disposition_v0.2.7.json",
    "results/pilot2/dedicated_sol_audit_primary_verification_v0.2.7.json",
    "results/pilot2/injection_execution_readiness_v0.2.7.json",
    "results/pilot2/injection_runner_zero_science_validation_v0.2.7.json",
    "results/pilot2/injection_v027_audit_finding_closure.json",
    "results/pilot2/injection_validation_manifest_v0.2.7.json",
    "src/pulsar_pilot/pilot2_injection_executor_v027.py",
    "src/pulsar_pilot/pilot2_injection_runner_v027.py",
    "tests/test_pilot2_injection_runner_v027.py",
)


def _sync_regular_file(file_descriptor: int) -> None:
    os.fsync(file_descriptor)
    if sys.platform == "darwin":
        fcntl.fcntl(file_descriptor, fcntl.F_FULLFSYNC)


class TrustedJSONError(ValueError):
    """A trusted JSON document is malformed or contains duplicate members."""


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TrustedJSONError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _loads_trusted_json(payload: str, label: str) -> Any:
    try:
        return json.loads(payload, object_pairs_hook=_reject_duplicate_members)
    except json.JSONDecodeError as error:
        raise TrustedJSONError(f"{label} is malformed: {error}") from error
    except TrustedJSONError as error:
        raise TrustedJSONError(f"{label} contains {error}") from error


def _load_trusted_json(path: Path, label: str) -> Any:
    return _loads_trusted_json(path.read_text(encoding="utf-8"), label)


def _require_initialized_data_root(data_root: Path) -> None:
    marker = data_root / MARKER_NAME
    if not marker.is_file():
        raise RuntimeError(f"Data root is not initialized; run init-data-root first: {data_root}")
    try:
        payload = _load_trusted_json(marker, "data-root marker")
    except (OSError, TrustedJSONError) as error:
        raise RuntimeError(f"Data root marker is not trusted: {error}") from error
    if type(payload) is not dict or payload.get("project") != MARKER_PROJECT:
        raise RuntimeError(f"Data root marker belongs to another project: {data_root}")


def _sync_directory(path: Path) -> None:
    directory_descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def _durable_mkdirs(path: Path) -> None:
    if path.is_dir():
        return
    missing: list[Path] = []
    cursor = path
    while not cursor.exists():
        missing.append(cursor)
        cursor = cursor.parent
    if not cursor.is_dir():
        raise NotADirectoryError(f"Existing ancestor is not a directory: {cursor}")
    for directory in reversed(missing):
        os.mkdir(directory)
        _sync_directory(directory.parent)


def _durable_atomic_json(path: Path, value: dict[str, Any]) -> None:
    _durable_mkdirs(path.parent)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        _sync_regular_file(stream.fileno())
    os.replace(temporary, path)
    _sync_directory(path.parent)


def _verify_exact_repository_hashes(
    root: Path,
    frozen: object,
    expected_paths: tuple[str, ...],
    label: str,
) -> list[str]:
    if not isinstance(frozen, dict):
        return [f"v0.2.7 {label} frozen-hash contract is not an object"]
    expected = set(expected_paths)
    actual = set(frozen)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        return [
            (
                f"v0.2.7 {label} frozen-hash path set is not exact: "
                f"missing={missing}, unexpected={unexpected}"
            )
        ]
    resolved_root = root.resolve()
    failures: list[str] = []
    for relative in expected_paths:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            failures.append(f"v0.2.7 {label} unsafe hash path: {relative}")
            continue
        item = root / relative_path
        try:
            resolved_item = item.resolve(strict=True)
        except OSError:
            failures.append(f"v0.2.7 {label} hash target is absent: {relative}")
            continue
        if not resolved_item.is_relative_to(resolved_root) or item.is_symlink():
            failures.append(f"v0.2.7 {label} hash path escapes repository: {relative}")
            continue
        expected_hash = frozen[relative]
        if not isinstance(expected_hash, str) or hash_file(item, "sha256") != expected_hash:
            failures.append(f"v0.2.7 {label} hash mismatch: {relative}")
    return failures


PHASE_TELEMETRY_KEYS = (
    "recovered_sine_microseconds",
    "recovered_cosine_microseconds",
    "sine_uncertainty_microseconds",
    "cosine_uncertainty_microseconds",
    "sine_cosine_correlation",
    "sine_cosine_covariance_microseconds_squared",
    "recovered_phase_radians",
    "phase_standard_error_radians",
    "signed_wrapped_phase_error_radians",
)
RECORD_NUMERIC_KEYS = (
    "period_days",
    "amplitude_microseconds",
    "phase_radians",
    "locked_threshold_delta_chi2",
    "global_maximum_delta_chi2",
    "frequency_recovery_tolerance_per_day",
    "amplitude_bias_fraction",
    "phase_error_radians",
    *PHASE_TELEMETRY_KEYS,
    "toa_adjustment_error_microseconds",
    TOA_ADJUSTMENT_KEY,
    UNCENTERED_TARGET_KEY,
    DM_ERROR_KEY,
    "ordinary_absorption_fraction",
    "signal_astrometry_correlation",
)
RECORD_BOOLEAN_KEYS = (
    "triggered",
    "frequency_recovered",
    "ordinary_fit_converged",
    "joint_fit_converged",
    "solver_audit_required",
    "solver_audit_pass",
    "observed_residual_vector_used",
    "observed_periodic_scan_executed",
)
BASE_RECORD_KEYS = {
    "schema_version",
    "run_id",
    "execution_binding_sha256",
    "case",
    "family",
    *RECORD_NUMERIC_KEYS,
    *RECORD_BOOLEAN_KEYS,
    "solver_comparison",
    "full_covariance_solver",
    "input_binding",
}
FREQUENCY_GRID_KEYS = {
    "algorithm",
    "oversampling",
    "span_days",
    "minimum_period_days",
    "maximum_period_days",
    "minimum_frequency_per_day",
    "maximum_frequency_per_day",
    "frequency_step_per_day",
    "frequency_count",
}
INPUT_BINDING_KEYS = {
    "target",
    "active_toas",
    "covariance_shape",
    "timing_design_shape",
    "timing_design_rank",
    "frequency_grid",
    "reference_epoch_mjd_tdb",
    "observed_residual_vector_loaded",
    "observed_periodic_scan_executed",
    "network_access_enabled",
}
FULL_SOLVER_KEYS = {
    "solver",
    "completed",
    "returned_chi2",
    "sine_us",
    "cosine_us",
    "amplitude_us",
    "phase_radians",
    "sine_uncertainty_us",
    "cosine_uncertainty_us",
    "chi2",
    "reduced_chi2",
    "weighted_rms_us",
    "free_parameter_count",
    "release_red_noise_preserved",
    "wavex_absent",
}


def _finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _strict_json_equal(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(actual) is dict:
        actual_dict = actual
        expected_dict = expected
        return set(actual_dict) == set(expected_dict) and all(
            _strict_json_equal(actual_dict[key], expected_dict[key]) for key in expected_dict
        )
    if type(actual) is list:
        actual_list = actual
        expected_list = expected
        return len(actual_list) == len(expected_list) and all(
            _strict_json_equal(left, right)
            for left, right in zip(actual_list, expected_list, strict=True)
        )
    return actual == expected


def _canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _input_binding_schema_failures(binding: object, label: str) -> list[str]:
    if type(binding) is not dict or set(binding) != INPUT_BINDING_KEYS:
        return [f"{label} input binding schema differs"]
    failures: list[str] = []
    expected = {
        "target": "B1937+21",
        "active_toas": 660,
        "covariance_shape": [1320, 1320],
        "timing_design_shape": [1320, 284],
        "timing_design_rank": 284,
        "observed_residual_vector_loaded": False,
        "observed_periodic_scan_executed": False,
        "network_access_enabled": False,
    }
    for key, value in expected.items():
        if not _strict_json_equal(binding.get(key), value):
            failures.append(f"{label} input binding differs: {key}")
    if type(binding.get("reference_epoch_mjd_tdb")) is not float or not _finite_number(
        binding.get("reference_epoch_mjd_tdb")
    ):
        failures.append(f"{label} input binding reference epoch is invalid")
    grid = binding.get("frequency_grid")
    if type(grid) is not dict or set(grid) != FREQUENCY_GRID_KEYS:
        failures.append(f"{label} input binding frequency-grid schema differs")
    else:
        if type(grid.get("algorithm")) is not str or (
            grid.get("algorithm") != "linear_frequency_independent_bin_oversampling"
        ):
            failures.append(f"{label} input binding frequency-grid algorithm differs")
        if (
            type(grid.get("oversampling")) is not int
            or grid.get("oversampling") != 5
            or type(grid.get("frequency_count")) is not int
            or grid["frequency_count"] < 2
        ):
            failures.append(f"{label} input binding frequency-grid count or oversampling differs")
        for key in FREQUENCY_GRID_KEYS - {"algorithm", "oversampling", "frequency_count"}:
            if type(grid.get(key)) is not float or not _finite_number(grid.get(key)):
                failures.append(f"{label} input binding frequency-grid value is invalid: {key}")
        if not _strict_json_equal(grid.get("minimum_period_days"), 30.0):
            failures.append(f"{label} input binding minimum search period differs")
        if not _strict_json_equal(grid.get("maximum_period_days"), 2000.0):
            failures.append(f"{label} input binding maximum search period differs")
        if not _strict_json_equal(grid.get("minimum_frequency_per_day"), 1.0 / 2000.0):
            failures.append(f"{label} input binding minimum search frequency differs")
        if not _strict_json_equal(grid.get("maximum_frequency_per_day"), 1.0 / 30.0):
            failures.append(f"{label} input binding maximum search frequency differs")
        if _finite_number(grid.get("span_days")) and _finite_number(
            grid.get("frequency_step_per_day")
        ):
            expected_step = 1.0 / (float(grid["span_days"]) * 5.0)
            if not math.isclose(
                float(grid["frequency_step_per_day"]),
                expected_step,
                rel_tol=0.0,
                abs_tol=1e-15,
            ):
                failures.append(f"{label} input binding frequency step is inconsistent")
    return failures


def _validate_input_binding(binding: object, trusted_binding: object) -> list[str]:
    failures = _input_binding_schema_failures(trusted_binding, "trusted")
    failures.extend(_input_binding_schema_failures(binding, "record"))
    if not failures and not _strict_json_equal(binding, trusted_binding):
        failures.append("record input binding differs from trusted execution context")
    return failures


def _input_binding_sha256(binding: object) -> str:
    failures = _input_binding_schema_failures(binding, "trusted")
    if failures:
        raise RuntimeError(f"Trusted input binding failed validation: {failures}")
    return _canonical_json_sha256(binding)


def _execution_binding_sha256(
    implementation: str,
    execution_freeze: str,
    threshold_lock: str,
    inventory: str,
    input_binding: str,
) -> str:
    return hashlib.sha256(
        (
            f"{implementation}:{execution_freeze}:{threshold_lock}:{inventory}:{input_binding}"
        ).encode()
    ).hexdigest()


def _validate_solver_payload(record: dict[str, Any], audit_required: bool) -> list[str]:
    comparison = record.get("solver_comparison")
    solver = record.get("full_covariance_solver")
    if not audit_required:
        return [] if comparison is None and solver is None else ["unexpected solver-audit payload"]
    failures: list[str] = []
    comparison_keys = {
        "amplitude_difference_microseconds",
        "phase_difference_radians",
        "chi2_difference",
    }
    if not isinstance(comparison, dict) or set(comparison) != comparison_keys:
        failures.append("solver comparison schema differs")
    elif not all(_finite_number(value) and value >= 0 for value in comparison.values()):
        failures.append("solver comparison contains an invalid value")
    if not isinstance(solver, dict) or set(solver) != FULL_SOLVER_KEYS:
        failures.append("full-covariance solver schema differs")
        return failures
    if solver.get("solver") != "WidebandTOAFitter_explicit_full_covariance":
        failures.append("full-covariance solver identity differs")
    for key in ("completed", "release_red_noise_preserved", "wavex_absent"):
        if type(solver.get(key)) is not bool:
            failures.append(f"full-covariance solver boolean is invalid: {key}")
    if type(solver.get("free_parameter_count")) is not int or solver["free_parameter_count"] < 0:
        failures.append("full-covariance solver parameter count is invalid")
    numeric = FULL_SOLVER_KEYS - {
        "solver",
        "completed",
        "free_parameter_count",
        "release_red_noise_preserved",
        "wavex_absent",
    }
    for key in numeric:
        if not _finite_number(solver.get(key)):
            failures.append(f"full-covariance solver value is invalid: {key}")
    return failures


def validate_complete_case_record(
    record: object,
    case: dict[str, Any],
    execution_binding: str,
    threshold_delta_chi2: float,
    audit_required: bool,
    trusted_input_binding: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("Recovered artifact is not a JSON object")
    expected_keys = set(BASE_RECORD_KEYS)
    if case["family"] != "annual":
        expected_keys.add("candidate_eligible")
    if set(record) != expected_keys:
        missing = sorted(expected_keys - set(record))
        unexpected = sorted(set(record) - expected_keys)
        raise RuntimeError(
            f"Recovered artifact schema differs: missing={missing}, unexpected={unexpected}"
        )
    failures: list[str] = []
    if record.get("schema_version") != RECORD_SCHEMA_VERSION:
        failures.append("record schema version differs")
    if record.get("run_id") != RECORD_RUN_ID:
        failures.append("record run ID differs")
    if record.get("execution_binding_sha256") != execution_binding:
        failures.append("record execution binding differs")
    if record.get("case") != case or record.get("family") != case["family"]:
        failures.append("record case or family differs")
    for key in RECORD_NUMERIC_KEYS:
        if not _finite_number(record.get(key)):
            failures.append(f"record numeric value is invalid: {key}")
    for key in RECORD_BOOLEAN_KEYS:
        if type(record.get(key)) is not bool:
            failures.append(f"record boolean value is invalid: {key}")
    for key in ("period_days", "amplitude_microseconds", "phase_radians"):
        if record.get(key) != float(case[key]):
            failures.append(f"record case value differs: {key}")
    if record.get("locked_threshold_delta_chi2") != float(threshold_delta_chi2):
        failures.append("record locked threshold differs")
    if record.get("solver_audit_required") is not audit_required:
        failures.append("record solver-audit requirement differs")
    nonnegative = {
        "frequency_recovery_tolerance_per_day",
        "amplitude_bias_fraction",
        "phase_error_radians",
        "sine_uncertainty_microseconds",
        "cosine_uncertainty_microseconds",
        "phase_standard_error_radians",
        "toa_adjustment_error_microseconds",
        TOA_ADJUSTMENT_KEY,
        UNCENTERED_TARGET_KEY,
        DM_ERROR_KEY,
    }
    for key in nonnegative:
        if _finite_number(record.get(key)) and record[key] < 0:
            failures.append(f"record value is negative: {key}")
    for key in ("ordinary_absorption_fraction", "signal_astrometry_correlation"):
        if _finite_number(record.get(key)) and not 0.0 <= record[key] <= 1.0:
            failures.append(f"record fraction is outside zero to one: {key}")
    if (
        _finite_number(record.get("sine_cosine_correlation"))
        and abs(record["sine_cosine_correlation"]) > 1.0
    ):
        failures.append("record sine-cosine correlation is outside minus one to one")
    if record.get("toa_adjustment_error_microseconds") != record.get(TOA_ADJUSTMENT_KEY):
        failures.append("record TOA-adjustment aliases differ")
    if (
        _finite_number(record.get("phase_error_radians"))
        and _finite_number(record.get("signed_wrapped_phase_error_radians"))
        and record["phase_error_radians"] != abs(record["signed_wrapped_phase_error_radians"])
    ):
        failures.append("record phase-error fields are inconsistent")
    if record.get("observed_residual_vector_used") is not False:
        failures.append("record observed-residual boundary differs")
    if record.get("observed_periodic_scan_executed") is not False:
        failures.append("record observed-periodic boundary differs")
    if case["family"] != "annual" and record.get("candidate_eligible") is not True:
        failures.append("record candidate-eligibility field differs")
    failures.extend(_validate_input_binding(record.get("input_binding"), trusted_input_binding))
    failures.extend(_validate_solver_payload(record, audit_required))
    if failures:
        raise RuntimeError(f"Recovered artifact failed complete validation: {failures}")
    return record


def _aggregate_sha256(paths: tuple[str, ...]) -> str:
    root = repository_root()
    digest = hashlib.sha256()
    for relative in paths:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def implementation_sha256() -> str:
    return _aggregate_sha256(IMPLEMENTATION_PATHS)


def _configs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = repository_root()
    return (
        load_yaml(root / BASE_CONFIG_PATH),
        load_yaml(root / REMEDIATION_CONFIG_PATH),
        load_yaml(root / RUNNER_CONFIG_PATH),
    )


def _inventory() -> dict[str, Any]:
    return build_v023_inventory()


def _verify_freeze(
    path_name: str,
    expected_status: str,
    label: str,
    expected_frozen_paths: tuple[str, ...],
) -> dict[str, Any]:
    root = repository_root()
    path = root / path_name
    if not path.is_file():
        return {"status": "locked", "failures": [f"v0.2.7 {label} freeze is absent"]}
    resolved_root = root.resolve()
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(resolved_root):
        return {
            "status": "fail",
            "failures": [f"v0.2.7 {label} freeze path escapes repository"],
        }
    try:
        freeze = _load_trusted_json(path, f"v0.2.7 {label} freeze")
    except (OSError, TrustedJSONError) as error:
        return {
            "status": "fail",
            "failures": [f"v0.2.7 {label} freeze is unreadable: {error}"],
        }
    if not isinstance(freeze, dict):
        return {
            "status": "fail",
            "failures": [f"v0.2.7 {label} freeze is not an object"],
        }
    failures: list[str] = []
    if freeze.get("status") != expected_status:
        failures.append(f"v0.2.7 {label} freeze status is invalid")
    if freeze.get("execution_authorized") is not False:
        failures.append(f"v0.2.7 {label} freeze authorizes execution")
    if freeze.get("science_cases_executed_during_validation") != 0:
        failures.append(f"v0.2.7 {label} validation was not zero-science")
    for key in (
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "promotion_grade_authorized",
        "discovery_claim_authorized",
    ):
        if freeze.get(key) is not False:
            failures.append(f"v0.2.7 {label} boundary invalid: {key}")
    inventory = _inventory()
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append(f"v0.2.7 {label} inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append(f"v0.2.7 {label} implementation mismatch")
    failures.extend(
        _verify_exact_repository_hashes(
            root,
            freeze.get("frozen_sha256"),
            expected_frozen_paths,
            label,
        )
    )
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "execution_authorized": False,
        "inventory_sha256": inventory["inventory_sha256"],
        "implementation_sha256": implementation_sha256(),
        "freeze_sha256": hash_file(path, "sha256"),
    }


def verify_implementation_freeze() -> dict[str, Any]:
    return _verify_freeze(
        IMPLEMENTATION_FREEZE_PATH,
        "implementation_frozen_execution_not_authorized",
        "implementation",
        IMPLEMENTATION_FREEZE_FROZEN_PATHS,
    )


def verify_readiness_freeze() -> dict[str, Any]:
    result = _verify_freeze(
        READINESS_FREEZE_PATH,
        "execution_readiness_frozen_execution_not_authorized",
        "readiness",
        READINESS_FREEZE_FROZEN_PATHS,
    )
    if result["status"] == "locked":
        return result
    path = repository_root() / READINESS_FREEZE_PATH
    try:
        freeze = _load_trusted_json(path, "v0.2.7 readiness freeze")
    except (OSError, TrustedJSONError) as error:
        result["status"] = "fail"
        result["failures"] = list(result["failures"]) + [
            f"v0.2.7 readiness freeze is unreadable: {error}"
        ]
        return result
    failures = list(result["failures"])
    if freeze.get("execution_readiness") != "pass":
        failures.append("v0.2.7 readiness semantic is not pass")
    result["status"] = "pass" if not failures else "fail"
    result["failures"] = failures
    return result


def verify_predecessor_bindings(data_root: Path) -> dict[str, Any]:
    _require_initialized_data_root(data_root)
    root = repository_root()
    _, remediation, runner = _configs()
    failures: list[str] = []
    bindings = runner["predecessor_bindings"]
    repository_keys = {
        "v0.2.2_execution_freeze",
        "v0.2.2_crash_audit",
        "v0.2.6_sol_audit_record",
        "v0.2.6_sol_audit_disposition",
    }
    for key, binding in bindings.items():
        base = root if key in repository_keys else data_root
        path = base / str(binding["logical_path"])
        if not path.is_file() or hash_file(path, "sha256") != binding["sha256"]:
            failures.append(f"Predecessor binding mismatch: {key}")
    if failures:
        return {"status": "fail", "failures": failures}
    try:
        v022_ledger = _load_trusted_json(
            data_root / bindings["v0.2.2_ledger"]["logical_path"],
            "v0.2.2 predecessor ledger",
        )
        crash = _load_trusted_json(
            root / bindings["v0.2.2_crash_audit"]["logical_path"],
            "v0.2.2 crash audit",
        )
        lock = _load_trusted_json(
            data_root / bindings["threshold_lock"]["logical_path"],
            "threshold lock",
        )
    except (OSError, TrustedJSONError) as error:
        return {
            "status": "fail",
            "failures": [f"Predecessor JSON is not trusted: {error}"],
        }
    if len(v022_ledger.get("completed_cases", {})) != 0:
        failures.append("v0.2.2 completed-case count changed")
    if v022_ledger.get("runtime_active") is not False:
        failures.append("v0.2.2 crash ledger is unexpectedly active")
    if v022_ledger.get("stage_status", {}).get(STAGE) != "running":
        failures.append("v0.2.2 crash ledger state changed")
    if v022_ledger.get("hard_stop") is not None:
        failures.append("v0.2.2 crash ledger was retrospectively terminalized")
    consumed = remediation["consumed_v0.2.2_case"]
    if crash.get("attempted_case", {}).get("case_id") != consumed["case_id"]:
        failures.append("Consumed v0.2.2 case binding changed")
    if lock.get("status") != "locked_before_sealed_evaluation":
        failures.append("Threshold-lock status changed")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "threshold_delta_chi2": float(lock["value_delta_chi2"]),
        "threshold_lock_sha256": bindings["threshold_lock"]["sha256"],
        "v0.2.2_crash_preserved": not failures,
        "consumed_v0.2.2_case_id": consumed["case_id"],
        "consumed_v0.2.2_seed": int(consumed["seed"]),
    }


def verify_repository_execution_authorization() -> dict[str, Any]:
    root = repository_root()
    implementation = verify_implementation_freeze()
    readiness = verify_readiness_freeze()
    failures = list(implementation["failures"]) + list(readiness["failures"])
    path = root / EXECUTION_FREEZE_PATH
    if not path.is_file():
        return {
            "status": "locked" if not failures else "fail",
            "failures": failures + ["Separate v0.2.7 execution freeze is absent"],
            "implementation": implementation,
            "readiness": readiness,
            "predecessors_loaded": False,
        }
    resolved_root = root.resolve()
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(resolved_root):
        return {
            "status": "fail",
            "failures": failures + ["v0.2.7 execution freeze path escapes repository"],
            "implementation": implementation,
            "readiness": readiness,
            "predecessors_loaded": False,
        }
    try:
        freeze = _load_trusted_json(path, "v0.2.7 execution freeze")
    except (OSError, TrustedJSONError) as error:
        return {
            "status": "fail",
            "failures": failures + [f"v0.2.7 execution freeze is unreadable: {error}"],
            "implementation": implementation,
            "readiness": readiness,
            "predecessors_loaded": False,
        }
    if not isinstance(freeze, dict):
        return {
            "status": "fail",
            "failures": failures + ["v0.2.7 execution freeze is not an object"],
            "implementation": implementation,
            "readiness": readiness,
            "predecessors_loaded": False,
        }
    if freeze.get("schema_version") != 1:
        failures.append("v0.2.7 execution freeze schema version is invalid")
    if freeze.get("freeze_id") != "pilot2-b1937-injection-execution-freeze-v0.2.7":
        failures.append("v0.2.7 execution freeze ID is invalid")
    if freeze.get("status") != "frozen_before_first_v0.2.7_injection_case":
        failures.append("v0.2.7 execution freeze status is invalid")
    if (
        not isinstance(freeze.get("user_authorization"), str)
        or not freeze["user_authorization"].strip()
    ):
        failures.append("v0.2.7 execution user authorization is absent")
    if freeze.get("execution_authorized") is not True:
        failures.append("v0.2.7 execution authorization is absent")
    if freeze.get("authorized_case_counts") != EXPECTED_AUTHORIZED_CASE_COUNTS:
        failures.append("v0.2.7 authorized case counts are invalid")
    if freeze.get("authorized_primary_fits") != 688:
        failures.append("v0.2.7 authorized primary-fit count is invalid")
    if freeze.get("no_reroll") is not True:
        failures.append("v0.2.7 no-reroll contract is absent")
    if freeze.get("threshold_retuning_authorized") is not False:
        failures.append("v0.2.7 threshold-retuning boundary is invalid")
    if freeze.get("v0.2.1_injection_acceptance_reuse_authorized") is not False:
        failures.append("v0.2.7 predecessor acceptance-reuse boundary is invalid")
    for key in (
        "observed_residual_access_authorized",
        "observed_periodic_search_authorized",
        "promotion_grade_authorized",
        "discovery_claim_authorized",
    ):
        if freeze.get(key) is not False:
            failures.append(f"v0.2.7 execution boundary invalid: {key}")
    inventory = _inventory()
    if freeze.get("inventory_sha256") != inventory["inventory_sha256"]:
        failures.append("v0.2.7 execution inventory mismatch")
    if freeze.get("implementation_sha256") != implementation_sha256():
        failures.append("v0.2.7 execution implementation mismatch")
    if freeze.get("implementation_freeze_sha256") != implementation.get("freeze_sha256"):
        failures.append("v0.2.7 execution implementation-freeze mismatch")
    if freeze.get("readiness_freeze_sha256") != readiness.get("freeze_sha256"):
        failures.append("v0.2.7 execution readiness-freeze mismatch")
    _, _, runner = _configs()
    expected_predecessors = {
        key: binding["sha256"] for key, binding in runner["predecessor_bindings"].items()
    }
    if freeze.get("predecessor_sha256") != expected_predecessors:
        failures.append("v0.2.7 execution predecessor contract mismatch")
    threshold_sha = expected_predecessors["threshold_lock"]
    if freeze.get("threshold_lock_sha256") != threshold_sha:
        failures.append("v0.2.7 execution threshold-lock mismatch")
    expected_supervision = {
        "heartbeat_interval_seconds": 30,
        "stale_after_seconds": 90,
        "checkpoint_case_interval": 25,
        "passive_review_interval_seconds": 1800,
        "scientific_outcomes_in_health_record": False,
    }
    if freeze.get("supervision_policy") != expected_supervision:
        failures.append("v0.2.7 execution supervision policy is invalid")
    if freeze.get("stop_rule") != (
        "any_gate_failure_stops_before_or_during_execution_without_reroll_retune_or_promotion"
    ):
        failures.append("v0.2.7 execution stop rule is invalid")
    failures.extend(
        _verify_exact_repository_hashes(
            root,
            freeze.get("frozen_sha256"),
            EXECUTION_FREEZE_FROZEN_PATHS,
            "execution",
        )
    )
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "implementation": implementation,
        "readiness": readiness,
        "predecessors_loaded": False,
        "freeze_sha256": hash_file(path, "sha256"),
    }


def verify_execution_gate(data_root: Path | None = None) -> dict[str, Any]:
    local = verify_repository_execution_authorization()
    if local["status"] != "pass":
        return local
    if data_root is None:
        return {
            **local,
            "status": "fail",
            "failures": ["Authorized execution requires an explicit data root"],
            "predecessors_loaded": False,
        }
    predecessors = verify_predecessor_bindings(data_root)
    failures = list(predecessors["failures"])
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "implementation": local["implementation"],
        "readiness": local["readiness"],
        "predecessors": predecessors,
        "predecessors_loaded": True,
        "freeze_sha256": local["freeze_sha256"],
    }


class V027Ledger(CalibrationLedger):
    def __init__(self, data_root: Path, inventory_sha256: str, implementation_hash: str):
        super().__init__(data_root, inventory_sha256, implementation_hash)
        self.path = data_root / "run_records/pilot2/calibration-v0.2.7-ledger.json"
        self.health_path = data_root / "run_records/pilot2/calibration-v0.2.7-health.json"
        self.dashboard_path = data_root / "derived/pilot2/calibration-v0.2.7-dashboard/index.html"

    def empty(self) -> dict[str, Any]:
        state = super().empty()
        state["run_id"] = RUN_ID
        state["stage_status"] = {STAGE: "pending", "promotion_grade": "pending"}
        state["v0.2.2_resume_authorized"] = False
        state["consumed_v0.2.2_case_reused"] = False
        state["active_attempt"] = None
        state["attempt_history"] = []
        return state

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty()
        try:
            state = _load_trusted_json(self.path, "v0.2.7 ledger")
        except (OSError, TrustedJSONError) as error:
            raise RuntimeError(f"v0.2.7 ledger is not trusted: {error}") from error
        if type(state) is not dict:
            raise RuntimeError("v0.2.7 ledger is not a JSON object")
        if state.get("inventory_sha256") != self.inventory_sha256:
            raise RuntimeError("v0.2.7 ledger inventory hash mismatch")
        if state.get("implementation_sha256") != self.implementation_sha256:
            raise RuntimeError("v0.2.7 ledger implementation hash mismatch")
        return state

    def save(self, state: dict[str, Any]) -> None:
        state["updated_utc"] = _utc_now()
        _durable_atomic_json(self.path, state)
        self.write_health(state)

    def begin_stage(self, stage: str) -> dict[str, Any]:
        if stage != STAGE:
            raise ValueError(f"Unknown v0.2.7 runner stage: {stage}")
        state = self.load()
        if state["hard_stop"] is not None:
            raise RuntimeError("v0.2.7 ledger contains a hard stop")
        if state["stage_status"][STAGE] == "pass":
            raise RuntimeError("v0.2.7 injection stage is already complete")
        if state["active_stage"] not in {None, STAGE}:
            raise RuntimeError("A different v0.2.7 stage is active")
        if state["active_stage"] is None:
            state["active_stage_started_utc"] = _utc_now()
        state["active_stage"] = STAGE
        state["stage_status"][STAGE] = "running"
        self.save(state)
        return state

    def health(self, state: dict[str, Any]) -> dict[str, Any]:
        health = super().health(state)
        completed = sum(item["stage"] == STAGE for item in state["completed_cases"].values())
        health.update(
            completed_injection_cases=completed,
            total_injection_cases=344,
            scientific_outcomes_sealed=state["stage_status"][STAGE] not in {"pass", "fail"},
            attempt_active=state.get("active_attempt") is not None,
            manual_refresh_command=(
                "PYTHONPATH=src pixi run python -m "
                "pulsar_pilot.pilot2_injection_runner_v027 health --data-root <PATH>"
            ),
        )
        return health

    def begin_attempt(
        self,
        sequence: int,
        case: dict[str, Any],
        execution_binding: str,
        input_binding_sha256: str,
        artifact_path: Path,
    ) -> dict[str, Any]:
        state = self.load()
        if state["active_stage"] != STAGE or state["stage_status"][STAGE] != "running":
            raise RuntimeError("Attempt cannot begin outside the active running stage")
        if state.get("active_attempt") is not None:
            raise RuntimeError("A prior v0.2.7 attempt requires recovery disposition")
        attempt = {
            "case_id": str(case["case_id"]),
            "seed": int(case["seed"]),
            "sequence": int(sequence),
            "family": str(case["family"]),
            "execution_binding_sha256": execution_binding,
            "input_binding_sha256": input_binding_sha256,
            "artifact_logical_path": logical_path(artifact_path, self.data_root),
            "status": "started_seed_consumed",
            "recorded_utc": _utc_now(),
        }
        state["active_attempt"] = attempt
        state.setdefault("attempt_history", []).append(dict(attempt))
        self.save(state)
        return attempt

    def clear_attempt(self, case_id: str, disposition: str) -> None:
        state = self.load()
        active = state.get("active_attempt")
        if active is None or active.get("case_id") != case_id:
            raise RuntimeError("Active v0.2.7 attempt does not match completed case")
        state.setdefault("attempt_history", []).append(
            {
                **active,
                "status": disposition,
                "recorded_utc": _utc_now(),
            }
        )
        state["active_attempt"] = None
        self.save(state)


def prepare_context(data_root: Path, cases: list[dict[str, Any]]) -> InjectionContext:
    log_path = data_root / "run_records/pilot2/injection-v0.2.7-setup.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with _network_disabled():
        model, toas = _load_release(data_root, log_path)
    from pint.fitter import WidebandTOAFitter

    fitter = WidebandTOAFitter(toas, model)
    covariance = fitter.get_noise_covariancematrix().matrix
    design = fitter.get_designmatrix().matrix
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    frequencies, grid = build_search_frequency_grid(times, 30.0, 2000.0, 5)
    reference_epoch = float(model.PEPOCH.value)
    scanner = prepare_covariance_gls_scanner(
        covariance, design, times, frequencies, reference_epoch
    )
    exact_scanners = {
        period: prepare_covariance_gls_scanner(
            covariance, design, times, np.asarray([1.0 / period]), reference_epoch
        )
        for period in sorted({float(case["period_days"]) for case in cases})
    }
    binding = {
        "target": "B1937+21",
        "active_toas": len(toas),
        "covariance_shape": list(covariance.shape),
        "timing_design_shape": list(design.shape),
        "timing_design_rank": scanner.timing_design_rank,
        "frequency_grid": grid,
        "reference_epoch_mjd_tdb": reference_epoch,
        "observed_residual_vector_loaded": False,
        "observed_periodic_scan_executed": False,
        "network_access_enabled": False,
    }
    expected = {
        "active_toas": 660,
        "covariance_shape": [1320, 1320],
        "timing_design_shape": [1320, 284],
        "timing_design_rank": 284,
    }
    for key, value in expected.items():
        if binding[key] != value:
            raise RuntimeError(f"v0.2.7 injection setup mismatch: {key}")
    return InjectionContext(
        model=model,
        toas=toas,
        scanner=scanner,
        exact_scanners=exact_scanners,
        times=times,
        reference_epoch=reference_epoch,
        input_binding=binding,
    )


def _record_path(data_root: Path, sequence: int, case: dict[str, Any]) -> Path:
    return (
        data_root
        / "derived/pilot2/calibration-v0.2.7/injections"
        / str(case["family"])
        / f"{sequence:04d}-{case['case_id']}.json"
    )


def prepare_case_directories(data_root: Path) -> None:
    case_root = data_root / "derived/pilot2/calibration-v0.2.7/injections"
    _durable_mkdirs(case_root)
    for family in ("main", "phase_reference", "annual", "boundary"):
        _durable_mkdirs(case_root / family)


def _resource_gate(name: str, observed: float, limit: float) -> dict[str, Any]:
    return _gate(name, observed, "<=", limit, observed <= limit)


def terminalize_execution_failure(
    ledger: V027Ledger,
    result_path: Path,
    error: Exception,
    active_case_id: str | None,
    failure_class: str = "unexpected_execution_exception",
) -> dict[str, Any]:
    state = ledger.load()
    result = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "stage": STAGE,
        "status": "fail",
        "failure_class": failure_class,
        "exception_type": type(error).__name__,
        "exception_message": str(error),
        "active_case_id": active_case_id,
        "completed_case_records": len(state["completed_cases"]),
        "partial_scientific_metrics_recorded": False,
        "threshold_retuned": False,
        "observed_residual_vector_used": False,
        "observed_periodic_scan_executed": False,
        "promotion_grade_executed": False,
    }
    _durable_atomic_json(result_path, result)
    ledger.complete_stage(STAGE, result_path, False)
    return result


def _verified_attempt_artifact(
    ledger: V027Ledger,
    attempt: dict[str, Any],
    case: dict[str, Any],
    execution_binding: str,
    input_binding_sha256: str,
    trusted_input_binding: dict[str, Any],
    threshold_delta_chi2: float,
    audit_required: bool,
) -> tuple[Path, dict[str, Any]]:
    if attempt.get("case_id") != case["case_id"]:
        raise RuntimeError("Interrupted attempt case ID differs from frozen inventory")
    if int(attempt.get("seed", -1)) != int(case["seed"]):
        raise RuntimeError("Interrupted attempt seed differs from frozen inventory")
    if attempt.get("execution_binding_sha256") != execution_binding:
        raise RuntimeError("Interrupted attempt execution binding differs")
    if attempt.get("input_binding_sha256") != input_binding_sha256:
        raise RuntimeError("Interrupted attempt input binding differs")
    path = ledger.data_root / str(attempt["artifact_logical_path"])
    record = _load_trusted_json(path, "interrupted v0.2.7 case artifact")
    validate_complete_case_record(
        record,
        case,
        execution_binding,
        threshold_delta_chi2,
        audit_required,
        trusted_input_binding,
    )
    return path, record


def recover_active_attempt(
    ledger: V027Ledger,
    cases: list[dict[str, Any]],
    execution_binding: str,
    input_binding_sha256: str,
    trusted_input_binding: dict[str, Any],
    threshold_delta_chi2: float,
    audit_ids: set[str],
    result_path: Path,
) -> dict[str, Any] | None:
    state = ledger.load()
    attempt = state.get("active_attempt")
    if attempt is None:
        return None
    cases_by_id = {str(case["case_id"]): case for case in cases}
    case_id = str(attempt.get("case_id"))
    case = cases_by_id.get(case_id)
    if case is None:
        error = RuntimeError("Interrupted attempt is absent from the frozen inventory")
        terminalize_execution_failure(
            ledger,
            result_path,
            error,
            case_id,
            "interrupted_consumed_attempt_without_verified_artifact",
        )
        raise error
    try:
        path, record = _verified_attempt_artifact(
            ledger,
            attempt,
            case,
            execution_binding,
            input_binding_sha256,
            trusted_input_binding,
            threshold_delta_chi2,
            case_id in audit_ids,
        )
        completed = state["completed_cases"].get(case_id)
        if completed is None:
            ledger.record_case(STAGE, case_id, path)
            disposition = "verified_artifact_adopted_without_recomputation"
        else:
            verification = ledger.verify_artifacts()
            if verification["status"] != "pass" or case_id in verification["failures"]:
                raise RuntimeError("Interrupted attempt ledger artifact failed verification")
            if (
                completed.get("logical_path") != attempt.get("artifact_logical_path")
                or int(completed.get("bytes", -1)) != path.stat().st_size
                or completed.get("sha256") != hash_file(path, "sha256")
            ):
                raise RuntimeError("Interrupted attempt ledger binding differs")
            disposition = "verified_ledger_record_reconciled_without_recomputation"
        ledger.clear_attempt(case_id, disposition)
        return record
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as error:
        state = ledger.load()
        if state["active_stage"] == STAGE and state["stage_status"][STAGE] == "running":
            terminalize_execution_failure(
                ledger,
                result_path,
                error,
                case_id,
                "interrupted_consumed_attempt_without_verified_artifact",
            )
        raise RuntimeError(
            "A consumed v0.2.7 attempt lacks a verified adoptable artifact"
        ) from error


def execute(data_root: Path) -> dict[str, Any]:
    gate = verify_execution_gate(data_root)
    if gate["status"] != "pass":
        raise RuntimeError(f"v0.2.7 injection execution is locked: {gate['failures']}")
    _require_initialized_data_root(data_root)
    base, remediation, runner = _configs()
    inventory = _inventory()
    cases = inventory["cases"]
    audit_ids = set(inventory["solver_audit_case_ids"])
    ledger = V027Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    result_path = data_root / runner["paths"]["result"]
    current_case_id: str | None = None

    try:
        if ledger.verify_artifacts()["status"] != "pass":
            raise RuntimeError("v0.2.7 recorded artifact integrity failure")
        state = ledger.load()
        if state["stage_status"][STAGE] == "pass":
            return {
                "status": "already_complete",
                "science_cases_executed_this_invocation": 0,
            }
        if state["active_stage"] is None:
            ledger.begin_stage(STAGE)
        elif not (state["active_stage"] == STAGE and state["stage_status"][STAGE] == "running"):
            raise RuntimeError("v0.2.7 ledger is not in a resumable stage state")

        predecessor = gate["predecessors"]
        lock_path = data_root / runner["predecessor_bindings"]["threshold_lock"]["logical_path"]
        lock_sha = hash_file(lock_path, "sha256")
        prepare_context_result = prepare_context(data_root, cases)
        trusted_input_binding = prepare_context_result.input_binding
        input_binding_sha = _input_binding_sha256(trusted_input_binding)
        execution_binding = _execution_binding_sha256(
            implementation_sha256(),
            gate["freeze_sha256"],
            lock_sha,
            inventory["inventory_sha256"],
            input_binding_sha,
        )
        recover_active_attempt(
            ledger,
            cases,
            execution_binding,
            input_binding_sha,
            trusted_input_binding,
            float(predecessor["threshold_delta_chi2"]),
            audit_ids,
            result_path,
        )

        started = time.perf_counter()
        records_by_id: dict[str, dict[str, Any]] = {}
        executed = 0

        def enforce_runtime_cap() -> None:
            elapsed = time.perf_counter() - started
            limit = float(runner["resource_caps"]["wall_hours_maximum"]) * 3600
            if elapsed > limit:
                raise RuntimeError("v0.2.7 injection stage exceeded the six-hour cap")

        prepare_case_directories(data_root)

        def load_or_execute(
            sequence: int,
            case: dict[str, Any],
            candidate_eligible: bool | None,
        ) -> tuple[dict[str, Any], bool]:
            nonlocal current_case_id, executed
            current_case_id = str(case["case_id"])
            path = _record_path(data_root, sequence, case)
            if current_case_id in ledger.load()["completed_cases"]:
                record = _load_trusted_json(path, "completed v0.2.7 case artifact")
                validate_complete_case_record(
                    record,
                    case,
                    execution_binding,
                    float(predecessor["threshold_delta_chi2"]),
                    current_case_id in audit_ids,
                    trusted_input_binding,
                )
                return record, False
            ledger.begin_attempt(
                sequence,
                case,
                execution_binding,
                input_binding_sha,
                path,
            )
            record = execute_injection_case(
                prepare_context_result,
                case,
                float(predecessor["threshold_delta_chi2"]),
                current_case_id in audit_ids,
                base,
                execution_binding,
            )
            if candidate_eligible is not None:
                record["candidate_eligible"] = candidate_eligible
            validate_complete_case_record(
                record,
                case,
                execution_binding,
                float(predecessor["threshold_delta_chi2"]),
                current_case_id in audit_ids,
                trusted_input_binding,
            )
            _durable_atomic_json(path, record)
            ledger.record_case(STAGE, current_case_id, path)
            ledger.clear_attempt(current_case_id, "committed_without_interruption")
            executed += 1
            return record, True

        def process_nonannual(family: str) -> None:
            for sequence, case in (
                (sequence, case)
                for sequence, case in enumerate(cases, 1)
                if case["family"] == family
            ):
                record, _ = load_or_execute(sequence, case, True)
                records_by_id[case["case_id"]] = record
                print(
                    f"PILOT2R7_INJECTION_PROGRESS {len(records_by_id)}/344",
                    flush=True,
                )
                enforce_runtime_cap()

        with HeartbeatService(ledger, HEARTBEAT_INTERVAL_SECONDS):
            process_nonannual("main")
            process_nonannual("phase_reference")
            annual_periods = sorted(
                {float(case["period_days"]) for case in cases if case["family"] == "annual"}
            )
            correlation_limit = float(
                base["candidate_eligibility"]["maximum_signal_astrometry_correlation"]
            )
            absorption_limit = float(
                base["candidate_eligibility"]["maximum_ordinary_model_absorption_fraction"]
            )
            for period in annual_periods:
                group = [
                    (sequence, case)
                    for sequence, case in enumerate(cases, 1)
                    if case["family"] == "annual" and float(case["period_days"]) == period
                ]
                group_records: list[dict[str, Any]] = []
                for sequence, case in group:
                    record, _ = load_or_execute(sequence, case, None)
                    group_records.append(record)
                    records_by_id[case["case_id"]] = record
                    print(
                        f"PILOT2R7_INJECTION_PROGRESS {len(records_by_id)}/344",
                        flush=True,
                    )
                    enforce_runtime_cap()
                eligible = (
                    max(float(item["signal_astrometry_correlation"]) for item in group_records)
                    < correlation_limit
                    and max(float(item["ordinary_absorption_fraction"]) for item in group_records)
                    < absorption_limit
                )
                for record in group_records:
                    if (
                        "candidate_eligible" in record
                        and bool(record["candidate_eligible"]) != eligible
                    ):
                        raise RuntimeError("Resumed v0.2.7 annual eligibility differs")
                    record["candidate_eligible"] = eligible
            process_nonannual("boundary")

        records = [records_by_id[case["case_id"]] for case in cases]
        if hash_file(lock_path, "sha256") != lock_sha:
            raise RuntimeError("Predecessor threshold lock changed during v0.2.7 execution")
        result = grade_records(records, base, remediation)
        elapsed_hours = (time.perf_counter() - started) / 3600.0
        peak_memory = _peak_rss_gib()
        data_root_size = _directory_size_gib(data_root)
        setup_log = data_root / runner["paths"]["setup_log"]
        sanitized = [
            line.replace(str(data_root), "RECHERCHE_DATA_ROOT")
            for line in setup_log.read_text(encoding="utf-8").splitlines()
        ]
        warnings = classify_injection_warning_lines(sanitized)
        result["gates"].extend(
            [
                _resource_gate(
                    "injection_wall_hours",
                    elapsed_hours,
                    float(runner["resource_caps"]["wall_hours_maximum"]),
                ),
                _resource_gate(
                    "peak_memory_gib",
                    peak_memory,
                    float(runner["resource_caps"]["peak_memory_gib_maximum"]),
                ),
                _resource_gate(
                    "complete_data_root_gib",
                    data_root_size,
                    float(runner["resource_caps"]["complete_data_root_gib_maximum"]),
                ),
                _gate(
                    "unexpected_material_warnings",
                    warnings["status"],
                    "==",
                    "pass",
                    warnings["status"] == "pass",
                ),
            ]
        )
        result["status"] = (
            "pass" if all(item["status"] == "pass" for item in result["gates"]) else "fail"
        )
        result.update(
            threshold_lock_sha256=lock_sha,
            threshold_retuned=False,
            science_cases_executed_this_invocation=executed,
            execution_binding_sha256=execution_binding,
            wall_hours=elapsed_hours,
            peak_memory_gib=peak_memory,
            complete_data_root_gib=data_root_size,
            warnings=warnings,
            observed_residual_vector_used=False,
            observed_periodic_scan_executed=False,
            promotion_grade_executed=False,
        )
        _durable_atomic_json(result_path, result)
        ledger.complete_stage(STAGE, result_path, result["status"] == "pass")
        return {
            "status": result["status"],
            "completed_injection_cases": len(records),
            "science_cases_executed_this_invocation": executed,
            "ledger_verification": ledger.verify_artifacts(),
            "promotion_grade_executed": False,
        }
    except Exception as error:
        state = ledger.load()
        if state["active_stage"] == STAGE and state["stage_status"][STAGE] == "running":
            terminalize_execution_failure(ledger, result_path, error, current_case_id)
        raise


def supervision_snapshot(data_root: Path) -> dict[str, Any]:
    inventory = _inventory()
    ledger = V027Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    status = state["stage_status"][STAGE]
    return {
        "schema_version": 1,
        "event": f"terminal_{status}" if status in {"pass", "fail"} else "locked_idle",
        "injection_cases_completed": len(state["completed_cases"]),
        "injection_cases_total": 344,
        "checkpoint_count": len(state["checkpoints"]),
        "hard_stop_present": state["hard_stop"] is not None,
        "heartbeat_interval_seconds": 30,
        "stale_after_seconds": 90,
        "passive_review_interval_seconds": 1800,
        "scientific_outcomes_sealed": status not in {"pass", "fail"},
    }


def zero_case_dry_run(data_root: Path) -> dict[str, Any]:
    _require_initialized_data_root(data_root)
    inventory = _inventory()
    ledger = V027Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
    state = ledger.load()
    ledger.save(state)
    gate = verify_execution_gate()
    allowed_lock_failures = {
        "v0.2.7 readiness freeze is absent",
        "Separate v0.2.7 execution freeze is absent",
    }
    criteria = {
        "remediation_freeze_passes": verify_remediation_freeze()["status"] == "pass",
        "implementation_freeze_passes": verify_implementation_freeze()["status"] == "pass",
        "execution_gate_fail_closed": (
            gate["status"] in {"locked", "fail"}
            and "Separate v0.2.7 execution freeze is absent" in gate["failures"]
            and set(gate["failures"]) <= allowed_lock_failures
        ),
        "predecessors_not_loaded": gate["predecessors_loaded"] is False,
        "zero_cases_recorded": len(state["completed_cases"]) == 0,
        "stage_pending": state["stage_status"][STAGE] == "pending",
        "hard_stop_absent": state["hard_stop"] is None,
        "artifact_verification_passes": ledger.verify_artifacts()["status"] == "pass",
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(criteria.values()) else "fail",
        "operation": "v0.2.7_runner_zero_science_integrity_dry_run",
        "criteria": criteria,
        "science_cases_executed": 0,
        "random_draws_generated": 0,
        "model_fits_executed": 0,
        "periodic_scans_executed": 0,
        "predecessor_artifacts_loaded": 0,
        "execution_gate_status": gate["status"],
        "health_record": logical_path(ledger.health_path, data_root),
        "dashboard": logical_path(ledger.dashboard_path, data_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-injection-runner-v027")
    parser.add_argument(
        "command", choices=("verify-implementation", "verify-gate", "dry-run", "health", "run")
    )
    parser.add_argument("--data-root")
    args = parser.parse_args()
    if args.command == "verify-implementation":
        result = verify_implementation_freeze()
    elif args.command == "verify-gate":
        root = configured_data_root(args.data_root) if args.data_root else None
        result = verify_execution_gate(root)
    else:
        data_root = configured_data_root(args.data_root)
        if args.command == "dry-run":
            result = zero_case_dry_run(data_root)
        elif args.command == "health":
            inventory = _inventory()
            ledger = V027Ledger(data_root, inventory["inventory_sha256"], implementation_sha256())
            result = ledger.write_health(ledger.load())
        else:
            result = execute(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status", "pass") not in {"fail"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
