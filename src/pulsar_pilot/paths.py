from __future__ import annotations

import json
import os
from pathlib import Path

ENV_NAME = "RECHERCHE_DATA_ROOT"
MARKER_NAME = ".project-recherche-data-root.json"
MARKER_PROJECT = "project-recherche-pulsar-pilot"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configured_data_root(explicit: str | None = None) -> Path:
    value = explicit or os.environ.get(ENV_NAME)
    if not value:
        raise RuntimeError(f"Set {ENV_NAME} to the single authorized pilot data root")
    root = Path(value).expanduser().resolve()
    repo = repository_root().resolve()
    if root == repo or repo in root.parents or root in repo.parents:
        raise RuntimeError("The controlled data root must be separate from the Git repository")
    return root


def initialize_data_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    marker = root / MARKER_NAME
    payload = {"schema_version": 1, "project": MARKER_PROJECT}
    if marker.exists():
        existing = json.loads(marker.read_text(encoding="utf-8"))
        if existing != payload:
            raise RuntimeError(f"Unexpected marker contents at {marker}")
    else:
        marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for name in ("raw", "controlled", "derived", "run_records", "tmp"):
        (root / name).mkdir(exist_ok=True)


def require_initialized_data_root(root: Path) -> None:
    marker = root / MARKER_NAME
    if not marker.is_file():
        raise RuntimeError(f"Data root is not initialized; run init-data-root first: {root}")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    if payload.get("project") != MARKER_PROJECT:
        raise RuntimeError(f"Data root marker belongs to another project: {root}")
