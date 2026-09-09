import json
from pathlib import Path

import pytest

from pulsar_pilot.paths import (
    MARKER_NAME,
    MARKER_PROJECT,
    configured_data_root,
    initialize_data_root,
    require_initialized_data_root,
)


def test_initialize_and_require_data_root(tmp_path: Path) -> None:
    root = tmp_path / "pilot-data"
    initialize_data_root(root)
    require_initialized_data_root(root)
    marker = json.loads((root / MARKER_NAME).read_text(encoding="utf-8"))
    assert marker["project"] == MARKER_PROJECT
    assert (root / "raw").is_dir()


def test_rejects_repository_as_data_root() -> None:
    with pytest.raises(RuntimeError, match="separate"):
        configured_data_root(str(Path(__file__).resolve().parents[1]))


def test_rejects_unmarked_data_root(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not initialized"):
        require_initialized_data_root(tmp_path)
