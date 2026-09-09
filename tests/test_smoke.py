from pathlib import Path

import pytest

from pulsar_pilot.smoke import _logical_path


def test_logical_path_is_relative_to_controlled_root(tmp_path: Path) -> None:
    path = tmp_path / "controlled" / "input.tim"
    path.parent.mkdir()
    path.touch()
    assert _logical_path(path, tmp_path) == "controlled/input.tim"


def test_logical_path_rejects_external_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _logical_path(Path("/private/tmp/outside"), tmp_path)
