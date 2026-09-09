from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import math
import os
import platform
import resource
import shutil
import socket
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .c1 import generate_circular_delay_us
from .c1r1 import (
    _joint_downhill_fit,
    _joint_full_covariance_fit,
    wrapped_phase_difference,
)
from .config import load_yaml
from .g2 import classify_warning_lines
from .paths import initialize_data_root, repository_root, require_initialized_data_root
from .pilot1_benchmark import _synthetic_toas
from .pilot1_runtime import (
    build_search_frequency_grid,
    generate_covariance_null,
    null_ensemble_diagnostics,
    prepare_covariance_gls_scanner,
)
from .provenance import hash_file, logical_path

CONFIG_PATH = "config/pilot2_preflight_v0.2.yaml"
DESIGN_FREEZE_PATH = "protocol/PILOT2_SELECTION_AND_PREFLIGHT_FREEZE_v0.2.json"
AUTHORIZATION_PATH = (
    "protocol/PILOT2_PREFLIGHT_CORRECTIVE_AUTHORIZATION_v0.2.1.json"
)
EXECUTION_FREEZE_PATH = "protocol/PILOT2_PREFLIGHT_EXECUTION_R1_FREEZE_v0.2.1.json"
SELECTION_RESULT_PATH = "results/pilot2/target_selection_v0.2.json"
ARCHIVE_MEMBER_ROOT = "NANOGrav15yr_PulsarTiming_v2.1.0/"
DATASET_ROOT = "controlled/nanograv15yr-v2.1.0"
TARGET = "B1937+21"
SEARCH_PERIOD_MINIMUM_DAYS = 30.0
SEARCH_PERIOD_MAXIMUM_DAYS = 2000.0
SEARCH_OVERSAMPLING = 5
MAX_FIT_ITERATIONS = 20
APPLICATION_ERROR_MAXIMUM_MICROSECONDS = 0.001
AUDIT_AMPLITUDE_DIFFERENCE_MAXIMUM_MICROSECONDS = 0.01
AUDIT_PHASE_DIFFERENCE_MAXIMUM_RADIANS = 0.001
AUDIT_CHI2_DIFFERENCE_MAXIMUM = 0.1
REFERENCE_FULL_WORKLOAD = {"scans": 1784, "primary_fits": 568, "audits": 29}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _seed_for_case(base_seed: int, case_id: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def build_case_order(config: dict[str, Any]) -> dict[str, Any]:
    benchmark = config["synthetic_benchmark"]
    base_seed = int(benchmark["base_seed"])
    cases: list[dict[str, Any]] = []
    for index in range(int(benchmark["null_cases"])):
        case_id = f"p2-null-{index:03d}"
        cases.append(
            {
                "case_id": case_id,
                "family": "null",
                "seed": _seed_for_case(base_seed, case_id),
                "full_covariance_audit": False,
            }
        )
    injection_cases: list[dict[str, Any]] = []
    injections = benchmark["injection_cases"]
    for period_index, period in enumerate(injections["periods_days"]):
        for amplitude_index, amplitude in enumerate(
            injections["amplitudes_microseconds"]
        ):
            for phase_index, phase in enumerate(injections["phases_radians"]):
                case_id = (
                    f"p2-inj-p{period_index:02d}-a{amplitude_index:02d}"
                    f"-h{phase_index:02d}"
                )
                injection_cases.append(
                    {
                        "case_id": case_id,
                        "family": "injection",
                        "period_days": float(period),
                        "amplitude_microseconds": float(amplitude),
                        "phase_radians": float(phase),
                        "seed": _seed_for_case(base_seed, case_id),
                        "full_covariance_audit": False,
                    }
                )
    audit_count = int(benchmark["explicit_full_covariance_audit"]["cases"])
    audited_ids = {
        item["case_id"]
        for item in sorted(
            injection_cases,
            key=lambda item: hashlib.sha256(item["case_id"].encode()).hexdigest(),
        )[:audit_count]
    }
    for item in injection_cases:
        item["full_covariance_audit"] = item["case_id"] in audited_ids
    cases.extend(injection_cases)
    for sequence, case in enumerate(cases, 1):
        case["sequence"] = sequence
    if len(cases) != int(benchmark["total_unique_cases"]):
        raise RuntimeError("Pilot 2 benchmark does not contain exactly 50 cases")
    if len({item["case_id"] for item in cases}) != len(cases):
        raise RuntimeError("Pilot 2 benchmark case IDs are not unique")
    payload = {
        "schema_version": 1,
        "plan_id": config["plan_id"],
        "case_count": len(cases),
        "null_cases": sum(item["family"] == "null" for item in cases),
        "injection_cases": sum(item["family"] == "injection" for item in cases),
        "full_covariance_audits": sum(
            bool(item["full_covariance_audit"]) for item in cases
        ),
        "cases": cases,
    }
    payload["order_sha256"] = hashlib.sha256(_canonical_json(cases)).hexdigest()
    return payload


def verify_execution_freeze() -> dict[str, Any]:
    root = repository_root()
    design = json.loads((root / DESIGN_FREEZE_PATH).read_text(encoding="utf-8"))
    authorization = json.loads(
        (root / AUTHORIZATION_PATH).read_text(encoding="utf-8")
    )
    freeze_path = root / EXECUTION_FREEZE_PATH
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    config = load_yaml(root / CONFIG_PATH)
    failures: list[str] = []
    if design.get("preflight_status") != "frozen_design_execution_not_authorized":
        failures.append("Design freeze status is invalid")
    if any(design.get("authorization", {}).values()):
        failures.append("Design freeze must remain nonexecuting")
    for relative, expected in design.get("frozen_sha256", {}).items():
        path = root / relative
        if not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"Design hash mismatch: {relative}")
    if authorization.get("authorization") != (
        "exact_frozen_b1937_preflight_extraction_reproduction_and_50_synthetic_cases"
    ):
        failures.append("User authorization scope is invalid")
    if authorization.get("observed_periodic_search_authorized") is not False:
        failures.append("Observed periodic search must remain unauthorized")
    if freeze.get("status") != "frozen_before_first_pilot2_preflight_execution":
        failures.append("Execution freeze status is invalid")
    if freeze.get("authorization_sha256") != hash_file(
        root / AUTHORIZATION_PATH, "sha256"
    ):
        failures.append("Authorization hash mismatch")
    for relative, expected in freeze.get("frozen_sha256", {}).items():
        path = root / relative
        if not path.is_file() or hash_file(path, "sha256") != expected:
            failures.append(f"Execution hash mismatch: {relative}")
    actual_order = build_case_order(config)["order_sha256"]
    if actual_order != freeze.get("case_order_sha256"):
        failures.append("Synthetic case-order hash mismatch")
    if freeze.get("observed_periodic_search_authorized") is not False:
        failures.append("Observed periodic search is not locked")
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "freeze_id": freeze.get("freeze_id"),
        "freeze_sha256": hash_file(freeze_path, "sha256"),
        "authorization_sha256": hash_file(root / AUTHORIZATION_PATH, "sha256"),
        "case_order_sha256": actual_order,
    }


def _directory_size_gib(path: Path) -> float:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) / (
        1024**3
    )


def _peak_rss_gib() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**3 if platform.system() == "Darwin" else 1024**2
    return peak / divisor


def _safe_copy_file(source: Path, destination: Path) -> dict[str, Any]:
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f"Shared runtime source is not a regular file: {source}")
    expected = hash_file(source, "sha256")
    if destination.exists():
        if not destination.is_file() or hash_file(destination, "sha256") != expected:
            raise RuntimeError(f"Existing shared runtime copy differs: {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        shutil.copyfile(source, temporary)
        if hash_file(temporary, "sha256") != expected:
            raise RuntimeError(f"Shared runtime copy verification failed: {source}")
        os.replace(temporary, destination)
        destination.chmod(0o444)
    return {
        "logical_path": destination.as_posix(),
        "bytes": destination.stat().st_size,
        "sha256": expected,
    }


def seed_required_clock_cache_entries(data_root: Path) -> list[dict[str, Any]]:
    entries = [
        {
            "url": (
                "https://raw.githubusercontent.com/ipta/"
                "pulsar-clock-corrections/main/tempo/clock/time_ao.dat"
            ),
            "controlled_source": data_root / DATASET_ROOT / "clock/time_ao.dat",
        }
    ]
    records: list[dict[str, Any]] = []
    cache_root = data_root / "derived/cache/astropy/download/url"
    for entry in entries:
        url = str(entry["url"])
        key = hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()
        destination = cache_root / key
        contents = destination / "contents"
        url_file = destination / "url"
        source = Path(entry["controlled_source"])
        copy_record = _safe_copy_file(source, contents)
        url_payload = url.encode()
        if url_file.exists():
            if url_file.read_bytes() != url_payload:
                raise RuntimeError(f"Existing Astropy cache URL differs: {url_file}")
        else:
            url_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = url_file.with_suffix(".tmp")
            temporary.write_bytes(url_payload)
            os.replace(temporary, url_file)
            url_file.chmod(0o444)
        records.append(
            {
                "url": url,
                "cache_key": key,
                "controlled_source": logical_path(source, data_root),
                "contents": {
                    "logical_path": logical_path(contents, data_root),
                    "bytes": int(copy_record["bytes"]),
                    "sha256": copy_record["sha256"],
                },
                "url_file_sha256": hashlib.sha256(url_payload).hexdigest(),
                "network_download_bytes": 0,
            }
        )
    return records


@contextlib.contextmanager
def _network_disabled() -> Any:
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def blocked_connect(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("Network access is disabled for the Pilot 2 preflight")

    socket.socket.connect = blocked_connect
    socket.socket.connect_ex = blocked_connect
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex


def seed_shared_runtime(source_root: Path, data_root: Path) -> dict[str, Any]:
    require_initialized_data_root(source_root)
    source_clock = source_root / DATASET_ROOT / "clock"
    source_cache = source_root / "derived/cache"
    if not source_clock.is_dir() or not source_cache.is_dir():
        raise RuntimeError("Audited v0.1 clock or ephemeris cache is missing")
    groups = (
        (source_clock, data_root / DATASET_ROOT / "clock", "clock"),
        (source_cache, data_root / "derived/cache", "cache"),
    )
    files: list[dict[str, Any]] = []
    for source_dir, destination_dir, group in groups:
        for source in sorted(item for item in source_dir.rglob("*") if item.is_file()):
            if source.name.startswith("._"):
                continue
            destination = destination_dir / source.relative_to(source_dir)
            record = _safe_copy_file(source, destination)
            record["group"] = group
            record["source_relative"] = source.relative_to(source_root).as_posix()
            record["logical_path"] = logical_path(destination, data_root)
            files.append(record)
    manifest = {
        "schema_version": 1,
        "source": "audited_v0.1_controlled_clock_and_local_ephemeris_cache",
        "network_download_bytes": 0,
        "file_count": len(files),
        "bytes": sum(int(item["bytes"]) for item in files),
        "files": files,
    }
    manifest["inventory_sha256"] = hashlib.sha256(_canonical_json(files)).hexdigest()
    return manifest


def extract_selected_products(
    archive_path: Path, data_root: Path, selection: dict[str, Any]
) -> dict[str, Any]:
    archive_record = selection["archive"]
    if archive_path.stat().st_size != int(archive_record["bytes"]):
        raise RuntimeError("Pilot 2 archive size mismatch")
    if hash_file(archive_path, "sha256") != archive_record["sha256"]:
        raise RuntimeError("Pilot 2 archive SHA-256 mismatch")
    expected = {
        item["archive_member"]: {"label": label, **item}
        for label, item in selection["selected_archive_members"].items()
    }
    if len(expected) != 6:
        raise RuntimeError("Pilot 2 selection does not bind exactly six products")
    extracted: dict[str, dict[str, Any]] = {}
    destination_root = (data_root / DATASET_ROOT).resolve()
    with tarfile.open(archive_path, "r|gz") as archive:
        for member in archive:
            if member.name not in expected:
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise RuntimeError(f"Selected member is not a regular file: {member.name}")
            relative = Path(member.name.removeprefix(ARCHIVE_MEMBER_ROOT))
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"Unsafe selected archive path: {member.name}")
            destination = (destination_root / relative).resolve()
            if destination_root not in destination.parents:
                raise RuntimeError(f"Selected archive member escaped data root: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"Cannot read selected archive member: {member.name}")
            payload = source.read()
            bound = expected[member.name]
            digest = hashlib.sha256(payload).hexdigest()
            if len(payload) != int(bound["bytes"]) or digest != bound["sha256"]:
                raise RuntimeError(f"Selected member hash mismatch: {member.name}")
            if destination.exists():
                if hash_file(destination, "sha256") != digest:
                    raise RuntimeError(f"Existing selected product differs: {destination}")
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix(destination.suffix + ".tmp")
                temporary.write_bytes(payload)
                os.replace(temporary, destination)
                destination.chmod(0o444)
            extracted[member.name] = {
                "label": bound["label"],
                "archive_member": member.name,
                "logical_path": logical_path(destination, data_root),
                "bytes": len(payload),
                "sha256": digest,
            }
    if set(extracted) != set(expected):
        missing = sorted(set(expected) - set(extracted))
        raise RuntimeError(f"Selected archive products are missing: {missing}")
    files = sorted(extracted.values(), key=lambda item: str(item["label"]))
    return {
        "status": "pass",
        "archive": {
            "bytes": archive_path.stat().st_size,
            "sha256": archive_record["sha256"],
        },
        "file_count": len(files),
        "payload_bytes": sum(int(item["bytes"]) for item in files),
        "files": files,
    }


def _load_release(data_root: Path, log_path: Path) -> tuple[Any, Any]:
    controlled = data_root / DATASET_ROOT
    par = controlled / "wideband/par/B1937+21_PINT_20230131.wb.par"
    tim = controlled / "wideband/tim/B1937+21_PINT_20230131.wb.tim"
    clock = controlled / "clock"
    for required in (par, tim, clock):
        if not required.exists():
            raise RuntimeError(f"Pilot 2 controlled input is missing: {required}")
    os.environ["PINT_CLOCK_OVERRIDE"] = str(clock)
    os.environ["XDG_CACHE_HOME"] = str(data_root / "derived/cache")
    from astropy.utils import iers

    iers.conf.auto_download = False
    import pint.logging
    from pint.models import get_model_and_toas

    pint.logging.setup(
        level="INFO",
        sink=log_path,
        usecolors=False,
        capturewarnings=True,
        removeprior=True,
    )
    return get_model_and_toas(
        par,
        tim,
        ephem="DE440",
        include_bipm=True,
        bipm_version="BIPM2019",
        planets=True,
        usepickle=False,
        limits="warn",
    )


def _reproduce_release(
    model: Any, toas: Any, config: dict[str, Any]
) -> tuple[dict[str, Any], Any]:
    import astropy.units as u
    from pint.fitter import WidebandDownhillFitter
    from pint.residuals import WidebandTOAResiduals

    gates = config["reproduction_gates"]
    mjds = np.asarray(toas.get_mjds().value, dtype=float)
    errors = np.asarray(toas.get_errors().to_value(u.us), dtype=float)
    metadata = {
        "active_toa_count": len(toas),
        "unique_floor_mjd_days": len({int(item) for item in mjds}),
        "span_days": float(np.ptp(mjds)),
        "median_toa_uncertainty_microseconds": float(np.median(errors)),
        "released_red_noise": "PLRedNoise" in model.components,
        "isolated_timing_model": "Binary" not in model.components
        and not any(name.startswith("Binary") for name in model.components),
        "free_parameter_count": len(model.free_params),
        "free_dmx_count": sum(name.startswith("DMX_") for name in model.free_params),
    }
    reference = WidebandTOAResiduals(toas, model)
    fit_start = time.perf_counter()
    fitter = WidebandDownhillFitter(toas, copy.deepcopy(model))
    returned = bool(fitter.fit_toas(maxiter=MAX_FIT_ITERATIONS))
    fit_seconds = time.perf_counter() - fit_start
    postfit = WidebandTOAResiduals(toas, fitter.model)
    combined = np.asarray(postfit.calc_wideband_resids(), dtype=float)
    timing = combined[: len(toas)]
    dm = combined[len(toas) :]
    criteria = {
        "active_toa_count_exact": metadata["active_toa_count"]
        == int(gates["active_toa_count_exact"]),
        "unique_floor_mjd_days_exact": metadata["unique_floor_mjd_days"]
        == int(gates["unique_floor_mjd_days_exact"]),
        "span_within_tolerance": abs(
            metadata["span_days"] - float(gates["span_days_expected"])
        )
        <= float(gates["span_days_absolute_tolerance"]),
        "median_uncertainty_within_tolerance": abs(
            metadata["median_toa_uncertainty_microseconds"]
            - float(gates["median_toa_uncertainty_microseconds_expected"])
        )
        <= float(gates["median_toa_uncertainty_absolute_tolerance"]),
        "released_red_noise_present": metadata["released_red_noise"]
        is bool(gates["released_red_noise_required"]),
        "isolated_timing_model": metadata["isolated_timing_model"]
        is bool(gates["isolated_timing_model_required"]),
        "ordinary_fit_converged": returned and bool(fitter.converged),
        "finite_timing_residuals": bool(np.all(np.isfinite(timing))),
        "finite_dm_residuals": bool(np.all(np.isfinite(dm))),
    }
    result = {
        "status": "pass" if all(criteria.values()) else "fail",
        "metadata": metadata,
        "fit": {
            "fitter": "WidebandDownhillFitter",
            "max_iterations": MAX_FIT_ITERATIONS,
            "returned_converged": returned,
            "fitter_converged": bool(fitter.converged),
            "wall_seconds": fit_seconds,
            "reference_chi2": float(reference.chi2),
            "postfit_chi2": float(postfit.chi2),
            "reference_weighted_rms_microseconds": float(
                reference.toa.rms_weighted().to_value(u.us)
            ),
            "postfit_weighted_rms_microseconds": float(
                postfit.toa.rms_weighted().to_value(u.us)
            ),
        },
        "criteria": criteria,
        "observed_residual_accessed_for_aggregate_reproduction": True,
        "observed_periodic_scan_executed": False,
    }
    return result, fitter.model


def _sanitized_case_record(record: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(record, sort_keys=True))


def _run_synthetic_benchmark(
    model: Any,
    toas: Any,
    config: dict[str, Any],
    data_root: Path,
    wall_start: float,
) -> dict[str, Any]:
    from pint.fitter import WidebandTOAFitter

    inventory = build_case_order(config)
    covariance_fitter = WidebandTOAFitter(toas, model)
    covariance = covariance_fitter.get_noise_covariancematrix().matrix
    design = covariance_fitter.get_designmatrix().matrix
    times = np.asarray(toas.table["tdbld"].data, dtype=float)
    frequencies, grid = build_search_frequency_grid(
        times,
        SEARCH_PERIOD_MINIMUM_DAYS,
        SEARCH_PERIOD_MAXIMUM_DAYS,
        SEARCH_OVERSAMPLING,
    )
    reference_epoch = float(model.PEPOCH.value)
    setup_start = time.perf_counter()
    scanner = prepare_covariance_gls_scanner(
        covariance, design, times, frequencies, reference_epoch
    )
    setup_seconds = time.perf_counter() - setup_start
    count = len(toas)
    factor = scanner.covariance_cholesky
    output_root = data_root / "derived/pilot2/preflight-v0.2/cases"
    output_root.mkdir(parents=True, exist_ok=True)
    noise_realizations: list[np.ndarray] = []
    records: list[dict[str, Any]] = []
    integrity_failures: list[str] = []
    scan_times: list[float] = []
    primary_fit_times: list[float] = []
    full_fit_times: list[float] = []
    application_errors: list[float] = []
    for case in inventory["cases"]:
        case_id = str(case["case_id"])
        noise = generate_covariance_null(factor, np.random.default_rng(case["seed"]))
        noise_realizations.append(noise)
        requested = noise.copy()
        if case["family"] == "injection":
            signal = np.asarray(
                generate_circular_delay_us(
                    times.astype(np.longdouble),
                    float(case["period_days"]),
                    float(case["amplitude_microseconds"]),
                    float(case["phase_radians"]),
                    reference_epoch,
                ),
                dtype=float,
            )
            requested[:count] += signal * 1e-6
        scan_start = time.perf_counter()
        scan = scanner.scan(requested)
        scan_seconds = time.perf_counter() - scan_start
        scan_times.append(scan_seconds)
        trigger = {key: value for key, value in scan.items() if not key.startswith("all_")}
        record: dict[str, Any] = {
            "schema_version": 1,
            "case": case,
            "trigger": trigger,
            "scan_wall_seconds": scan_seconds,
            "observed_residual_vector_used": False,
        }
        finite_trigger = all(
            math.isfinite(float(value))
            for key, value in trigger.items()
            if isinstance(value, (float, int)) and key != "peak_index"
        )
        if not finite_trigger:
            integrity_failures.append(f"{case_id}:nonfinite_trigger")
        if case["full_covariance_audit"]:
            synthetic, application = _synthetic_toas(toas, model, requested)
            application_error = max(
                float(application["toa_adjustment_maximum_absolute_error_microseconds"]),
                float(
                    application[
                        "uncentered_toa_residual_target_maximum_absolute_error_microseconds"
                    ]
                ),
            )
            application_errors.append(application_error)
            primary_start = time.perf_counter()
            primary = _joint_downhill_fit(
                synthetic,
                model,
                1.0 / float(case["period_days"]),
                reference_epoch,
                MAX_FIT_ITERATIONS,
            )
            primary_seconds = time.perf_counter() - primary_start
            primary_fit_times.append(primary_seconds)
            full_start = time.perf_counter()
            full = _joint_full_covariance_fit(
                synthetic,
                model,
                1.0 / float(case["period_days"]),
                reference_epoch,
                MAX_FIT_ITERATIONS,
            )
            full_seconds = time.perf_counter() - full_start
            full_fit_times.append(full_seconds)
            comparison = {
                "amplitude_difference_microseconds": abs(
                    float(primary["amplitude_us"]) - float(full["amplitude_us"])
                ),
                "phase_difference_radians": abs(
                    wrapped_phase_difference(
                        float(primary["phase_radians"]),
                        float(full["phase_radians"]),
                    )
                ),
                "chi2_difference": abs(float(primary["chi2"]) - float(full["chi2"])),
            }
            audit_pass = (
                bool(primary["returned_converged"])
                and bool(primary["fitter_converged"])
                and bool(full["completed"])
                and bool(primary["release_red_noise_preserved"])
                and bool(full["release_red_noise_preserved"])
                and bool(primary["wavex_absent"])
                and bool(full["wavex_absent"])
                and application_error <= APPLICATION_ERROR_MAXIMUM_MICROSECONDS
                and comparison["amplitude_difference_microseconds"]
                <= AUDIT_AMPLITUDE_DIFFERENCE_MAXIMUM_MICROSECONDS
                and comparison["phase_difference_radians"]
                <= AUDIT_PHASE_DIFFERENCE_MAXIMUM_RADIANS
                and comparison["chi2_difference"] <= AUDIT_CHI2_DIFFERENCE_MAXIMUM
            )
            if not audit_pass:
                integrity_failures.append(f"{case_id}:solver_audit")
            record["application"] = application
            record["primary_solver"] = {
                key: value
                for key, value in primary.items()
                if key not in {"fitter", "model", "residuals"}
            }
            record["primary_solver"]["wall_seconds"] = primary_seconds
            record["full_covariance_solver"] = {
                key: value
                for key, value in full.items()
                if key not in {"fitter", "model", "residuals"}
            }
            record["full_covariance_solver"]["wall_seconds"] = full_seconds
            record["solver_comparison"] = comparison
            record["audit_pass"] = audit_pass
        record = _sanitized_case_record(record)
        case_path = output_root / f"{int(case['sequence']):02d}-{case_id}.json"
        case_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        records.append(
            {
                "case_id": case_id,
                "logical_path": logical_path(case_path, data_root),
                "bytes": case_path.stat().st_size,
                "sha256": hash_file(case_path, "sha256"),
                "record": record,
            }
        )
        print(
            f"PILOT2_PROGRESS {int(case['sequence'])}/50 {case_id}",
            flush=True,
        )
        if time.perf_counter() - wall_start > float(
            config["resources"]["macbook_wall_hours_maximum"]
        ) * 3600.0:
            raise RuntimeError("Pilot 2 preflight exceeded its one-hour wall cap")
    diagnostics = null_ensemble_diagnostics(np.asarray(noise_realizations), factor)
    reference = REFERENCE_FULL_WORKLOAD
    projection = {
        "reference_workload_role": "v0.1_sized_calibration_planning_only",
        "reference_workload": reference,
        "scan_seconds": float(np.mean(scan_times)) * int(reference["scans"]),
        "primary_fit_seconds": float(np.mean(primary_fit_times))
        * int(reference["primary_fits"]),
        "audit_seconds": float(np.mean(full_fit_times)) * int(reference["audits"]),
        "setup_seconds": setup_seconds,
    }
    projected_seconds = sum(
        float(value) for key, value in projection.items() if key.endswith("seconds")
    )
    projection["total_seconds"] = projected_seconds
    projection["total_hours"] = projected_seconds / 3600.0
    audit_records = [
        item["record"] for item in records if "solver_comparison" in item["record"]
    ]
    criteria = {
        "exactly_50_cases_completed": len(records) == 50,
        "exactly_20_null_cases": sum(
            item["record"]["case"]["family"] == "null" for item in records
        )
        == 20,
        "exactly_30_injection_cases": sum(
            item["record"]["case"]["family"] == "injection" for item in records
        )
        == 30,
        "exactly_10_full_covariance_audits": len(audit_records) == 10,
        "integrity_failures_zero": not integrity_failures,
        "all_solver_audits_pass": all(item["audit_pass"] for item in audit_records),
        "projected_reference_calibration_under_six_hours": projected_seconds
        <= float(
            config["synthetic_benchmark"]["gates"][
                "projected_full_calibration_wall_hours_maximum"
            ]
        )
        * 3600.0,
        "observed_residual_vector_unused": all(
            item["record"]["observed_residual_vector_used"] is False
            for item in records
        ),
        "threshold_not_locked": True,
        "scientific_sensitivity_claim_not_made": True,
    }
    return {
        "status": "pass" if all(criteria.values()) else "fail",
        "inventory": inventory,
        "frequency_grid": grid,
        "reference_epoch_mjd_tdb": reference_epoch,
        "covariance_shape": list(covariance.shape),
        "timing_design_shape": list(design.shape),
        "timing_design_rank": scanner.timing_design_rank,
        "setup_wall_seconds": setup_seconds,
        "null_diagnostics": diagnostics,
        "case_artifacts": [
            {key: value for key, value in item.items() if key != "record"}
            for item in records
        ],
        "audit_comparisons": [item["solver_comparison"] for item in audit_records],
        "maximum_application_error_microseconds": max(application_errors, default=0.0),
        "integrity_failures": integrity_failures,
        "runtime_projection": projection,
        "criteria": criteria,
        "diagnostic_only": {
            "null_global_maxima": [
                item["record"]["trigger"]["trigger_statistic"]
                for item in records
                if item["record"]["case"]["family"] == "null"
            ],
            "injection_triggers": [
                {
                    "case_id": item["case_id"],
                    "trigger_statistic": item["record"]["trigger"]["trigger_statistic"],
                    "peak_period_days": item["record"]["trigger"]["peak_period_days"],
                }
                for item in records
                if item["record"]["case"]["family"] == "injection"
            ],
        },
        "observed_residual_vector_used": False,
        "threshold_calibration_performed": False,
        "scientific_sensitivity_claim_authorized": False,
    }


def run_preflight(
    data_root: Path, archive_path: Path, source_v01_root: Path
) -> dict[str, Any]:
    freeze = verify_execution_freeze()
    if freeze["status"] != "pass":
        raise RuntimeError(f"Pilot 2 execution freeze failed: {freeze}")
    root = repository_root()
    config = load_yaml(root / CONFIG_PATH)
    selection = json.loads((root / SELECTION_RESULT_PATH).read_text(encoding="utf-8"))
    if selection["selected_target"] != TARGET:
        raise RuntimeError("Pilot 2 selected target is not B1937+21")
    initialize_data_root(data_root)
    require_initialized_data_root(data_root)
    recorded = datetime.now(UTC)
    run_id = recorded.strftime("pilot2-preflight-%Y%m%dT%H%M%SZ")
    run_root = data_root / "run_records/pilot2"
    run_root.mkdir(parents=True, exist_ok=True)
    log_path = run_root / f"{run_id}.log"
    wall_start = time.perf_counter()
    shared_runtime = seed_shared_runtime(source_v01_root, data_root)
    shared_runtime["seeded_clock_url_cache_entries"] = (
        seed_required_clock_cache_entries(data_root)
    )
    extraction = extract_selected_products(archive_path, data_root, selection)
    with _network_disabled():
        model, toas = _load_release(data_root, log_path)
        reproduction, postfit_model = _reproduce_release(model, toas, config)
        if reproduction["status"] != "pass":
            raise RuntimeError(f"Pilot 2 reproduction gate failed: {reproduction}")
        benchmark = _run_synthetic_benchmark(
            postfit_model, toas, config, data_root, wall_start
        )
    sanitized_log = [
        line.replace(str(data_root), "RECHERCHE_DATA_ROOT").replace(
            str(source_v01_root), "PILOT1_DATA_ROOT"
        )
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    warnings = classify_warning_lines(sanitized_log)
    wall_seconds = time.perf_counter() - wall_start
    peak_memory_gib = _peak_rss_gib()
    data_root_gib = _directory_size_gib(data_root)
    resources = config["resources"]
    criteria = {
        "execution_freeze_verified": freeze["status"] == "pass",
        "shared_runtime_seeded_without_download": shared_runtime[
            "network_download_bytes"
        ]
        == 0,
        "exactly_six_selected_products": extraction["file_count"] == 6,
        "selected_payload_bytes_exact": extraction["payload_bytes"]
        == int(config["source"]["expected_selected_payload_bytes"]),
        "reproduction_passed": reproduction["status"] == "pass",
        "synthetic_benchmark_passed": benchmark["status"] == "pass",
        "unexpected_material_warnings_zero": warnings["status"] == "pass",
        "wall_time_under_one_hour": wall_seconds
        <= float(resources["macbook_wall_hours_maximum"]) * 3600.0,
        "peak_memory_under_16_gib": peak_memory_gib
        <= float(resources["peak_memory_gib_maximum"]),
        "data_root_under_1_5_gib": data_root_gib
        <= float(resources["complete_data_root_gib_maximum"]),
        "additional_download_bytes_zero": shared_runtime["network_download_bytes"]
        == int(resources["additional_download_bytes_maximum"]),
        "observed_periodic_search_not_executed": True,
        "threshold_calibration_not_executed": True,
    }
    status = "pass" if all(criteria.values()) else "fail"
    scorecard = {
        "overall": status.upper(),
        "passed": sum(criteria.values()),
        "total": len(criteria),
        "criteria": {key: "PASS" if value else "FAIL" for key, value in criteria.items()},
    }
    result = {
        "schema_version": 1,
        "run_id": run_id,
        "recorded_utc": recorded.isoformat().replace("+00:00", "Z"),
        "status": status,
        "target": TARGET,
        "scope": "released_fit_reproduction_and_exactly_50_synthetic_cases",
        "freeze": freeze,
        "shared_runtime": shared_runtime,
        "extraction": extraction,
        "reproduction": reproduction,
        "synthetic_benchmark": benchmark,
        "warnings": warnings,
        "resources": {
            "wall_seconds": wall_seconds,
            "wall_hours": wall_seconds / 3600.0,
            "peak_memory_gib": peak_memory_gib,
            "complete_data_root_gib": data_root_gib,
            "additional_download_bytes": 0,
        },
        "scorecard": scorecard,
        "observed_residual_access": "aggregate_reproduction_only",
        "observed_residual_global_search_executed": False,
        "observed_periodic_content_reported": False,
        "threshold_calibration_executed": False,
        "external_adviser_used": False,
    }
    result_path = run_root / f"{run_id}-summary.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    result["external_record"] = {
        "logical_path": logical_path(result_path, data_root),
        "bytes": result_path.stat().st_size,
        "sha256": hash_file(result_path, "sha256"),
    }
    print(f"PILOT2_RESULT {status.upper()} {result_path}", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(prog="pilot2-preflight")
    parser.add_argument("command", choices=("plan", "verify-freeze", "run"))
    parser.add_argument("--data-root")
    parser.add_argument("--archive")
    parser.add_argument("--source-v01-root")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "plan":
        result = build_case_order(load_yaml(repository_root() / CONFIG_PATH))
    elif args.command == "verify-freeze":
        result = verify_execution_freeze()
    else:
        if not args.data_root or not args.archive or not args.source_v01_root:
            parser.error("run requires --data-root, --archive, and --source-v01-root")
        result = run_preflight(
            Path(args.data_root).expanduser().resolve(),
            Path(args.archive).expanduser().resolve(),
            Path(args.source_v01_root).expanduser().resolve(),
        )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    elif args.command != "run":
        print(rendered, end="")
    return 0 if result.get("status", "pass") != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
