"""pixi.toml and pyproject.toml declare the scientific ranges separately; keep them equal.

Both files are hash-bound by the frozen environment manifest, so they cannot be
merged without requalification. This check stops them drifting apart instead.
"""

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONDA_NAME = {"astropy": "astropy-base"}


def test_pyproject_ranges_match_pixi():
    pixi = tomllib.loads((REPO / "pixi.toml").read_text())["dependencies"]
    project = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
    for requirement in project["dependencies"]:
        index = min(i for i, c in enumerate(requirement) if c in "<>=!~")
        name, spec = requirement[:index], requirement[index:]
        assert pixi[CONDA_NAME.get(name, name)] == spec, name
    assert project["requires-python"] == ">=3.11,<3.12" and pixi["python"] == "3.11.*"
