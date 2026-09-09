from __future__ import annotations

import json
import platform
import sys

import numpy as np


def precision_report() -> dict[str, object]:
    import pint

    float64 = np.finfo(np.float64)
    longdouble = np.finfo(np.longdouble)
    extended = bool(longdouble.eps < float64.eps and longdouble.nmant > float64.nmant)
    return {
        "python_version": sys.version.split()[0],
        "process_machine": platform.machine(),
        "pint_version": getattr(pint, "__version__", "unknown"),
        "numpy_version": np.__version__,
        "float64_epsilon": float(float64.eps),
        "longdouble_epsilon": float(longdouble.eps),
        "float64_mantissa_bits": int(float64.nmant),
        "longdouble_mantissa_bits": int(longdouble.nmant),
        "extended_precision": extended,
        "gate_g1_precision": "pass" if extended else "fail",
    }


def assert_precision() -> dict[str, object]:
    report = precision_report()
    if report["process_machine"] != "x86_64":
        raise RuntimeError(f"Expected x86_64 Rosetta process, got {report['process_machine']}")
    if not report["extended_precision"]:
        raise RuntimeError("NumPy longdouble does not exceed float64 precision")
    return report


def format_report(report: dict[str, object]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)
