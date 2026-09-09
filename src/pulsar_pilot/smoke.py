from __future__ import annotations

import json
import os
import platform
import resource
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _logical_path(path: Path, data_root: Path) -> str:
    return path.resolve().relative_to(data_root.resolve()).as_posix()


def run_smoke(data_root: Path) -> dict[str, Any]:
    """Load the frozen target and calculate non-fitting residual diagnostics."""
    controlled = data_root / "controlled" / "nanograv15yr-v2.1.0"
    clock_dir = controlled / "clock"
    par_path = controlled / "wideband" / "par" / "J1744-1134_PINT_20230131.wb.par"
    tim_path = controlled / "wideband" / "tim" / "J1744-1134_PINT_20230131.wb.tim"
    for required in (clock_dir, par_path, tim_path):
        if not required.exists():
            raise FileNotFoundError(f"Required controlled input is missing: {required}")

    run_dir = data_root / "run_records"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "pilot0_smoke.log"
    record_path = run_dir / "pilot0_smoke.json"
    cache_root = data_root / "derived" / "cache"
    cache_root.mkdir(parents=True, exist_ok=True)

    # These must be set before PINT/Astropy initialize their observatory and cache state.
    os.environ["PINT_CLOCK_OVERRIDE"] = str(clock_dir)
    os.environ["XDG_CACHE_HOME"] = str(cache_root)

    import astropy.units as u
    import numpy as np
    import pint
    import pint.logging
    from pint.models import get_model_and_toas
    from pint.residuals import Residuals, WidebandTOAResiduals

    pint.logging.setup(
        level="WARNING",
        sink=log_path,
        usecolors=False,
        capturewarnings=True,
        removeprior=True,
    )

    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    model, toas = get_model_and_toas(
        par_path,
        tim_path,
        ephem="DE440",
        include_bipm=True,
        bipm_version="BIPM2019",
        planets=True,
        usepickle=False,
        limits="warn",
    )
    load_wall_seconds = time.perf_counter() - wall_start

    residual_start = time.perf_counter()
    toa_residuals = Residuals(toas, model, residual_type="toa")
    weighted_rms_us = float(toa_residuals.rms_weighted().to_value(u.us))
    wideband_residuals = WidebandTOAResiduals(toas, model)
    wideband_chi2 = float(wideband_residuals.chi2)
    residual_wall_seconds = time.perf_counter() - residual_start

    mjds = toas.get_mjds()
    expected_ntoas = int(model.NTOA.value) if hasattr(model, "NTOA") else None
    published_chi2 = float(model.CHI2.value) if hasattr(model, "CHI2") else None
    warning_lines = 0
    if log_path.exists():
        warning_lines = sum(1 for line in log_path.read_text(encoding="utf-8").splitlines() if line)

    record: dict[str, Any] = {
        "schema_version": 1,
        "recorded_utc": datetime.now(UTC).isoformat(),
        "gate": "load_and_residual_smoke",
        "status": "pass" if len(toas) == 433 and expected_ntoas == 433 else "fail",
        "dataset": "nanograv15yr-v2.1.0",
        "target": "J1744-1134",
        "mode": "wideband",
        "inputs": {
            "par": _logical_path(par_path, data_root),
            "tim": _logical_path(tim_path, data_root),
            "clock_override": _logical_path(clock_dir, data_root),
            "ephemeris": "DE440",
            "timescale": "TT(BIPM2019)",
        },
        "software": {
            "python": platform.python_version(),
            "pint_pulsar": pint.__version__,
            "numpy": np.__version__,
            "process_machine": platform.machine(),
            "longdouble_mantissa_bits": int(np.finfo(np.longdouble).nmant),
        },
        "observations": {
            "ntoas_loaded": len(toas),
            "ntoas_declared_in_model": expected_ntoas,
            "mjd_min": float(mjds.min().value),
            "mjd_max": float(mjds.max().value),
        },
        "residuals": {
            "toa_weighted_rms_us": weighted_rms_us,
            "wideband_chi2_computed": wideband_chi2,
            "chi2_recorded_in_release_model": published_chi2,
        },
        "resources": {
            "load_wall_seconds": load_wall_seconds,
            "residual_wall_seconds": residual_wall_seconds,
            "total_wall_seconds": time.perf_counter() - wall_start,
            "cpu_seconds": time.process_time() - cpu_start,
            "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**2,
        },
        "diagnostics": {
            "log": _logical_path(log_path, data_root),
            "nonempty_log_lines": warning_lines,
        },
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if record["status"] != "pass":
        raise RuntimeError(f"Smoke acceptance failed; see {record_path}")
    return record
