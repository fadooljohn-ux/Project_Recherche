"""Shared operator helpers: integrity checks that survive ``python -O``, and data locations."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _location(variable: str, default: str) -> Path:
    value = os.environ.get(variable)
    if value is None:
        return REPO.parent / default
    path = Path(value).expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise RuntimeError(f"{variable} must be an existing absolute directory: {value!r}")
    return path


# External inputs, preparation, caches and runs. Override with RECHERCHE_DATA_ROOT.
DATA_ROOT = _location("RECHERCHE_DATA_ROOT", "Project Recherche Data")
# Verified archives and workbook backups. Override with RECHERCHE_RECOVERY_ROOT.
RECOVERY_ROOT = _location("RECHERCHE_RECOVERY_ROOT", "Recherche Recovery")


class IntegrityError(AssertionError):
    """A frozen-execution or evidence check failed.

    Subclasses AssertionError so existing handlers behave as before; unlike an
    ``assert`` statement it is not removed by ``python -O`` or PYTHONOPTIMIZE.
    """


def require(condition, message: str = "Integrity check failed") -> None:
    if not condition:
        raise IntegrityError(message)
