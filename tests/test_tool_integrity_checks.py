"""Operator tools must not rely on assert, which python -O silently removes."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from recherche_common import IntegrityError, require


def test_no_tool_uses_assert():
    offenders = [
        f"{path.name}:{node.lineno}"
        for path in sorted(TOOLS.glob("*.py"))
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Assert)
    ]
    assert offenders == []


def test_require_raises_a_named_error_that_existing_handlers_still_catch():
    require(True)
    with pytest.raises(IntegrityError, match="frozen code differs"):
        require(False, "frozen code differs")
    assert issubclass(IntegrityError, AssertionError)


def test_require_is_not_removed_by_optimized_python():
    code = (
        "import sys; sys.path.insert(0, sys.argv[1])\n"
        "from recherche_common import IntegrityError, require\n"
        "try:\n    require(False)\nexcept IntegrityError:\n    sys.exit(0)\nsys.exit(1)\n"
    )
    assert subprocess.run([sys.executable, "-O", "-c", code, str(TOOLS)]).returncode == 0


def test_data_root_override_must_be_an_existing_absolute_directory(tmp_path):
    code = "import sys; sys.path.insert(0, sys.argv[1]); import recherche_common as c; print(c.DATA_ROOT)"
    run = lambda value: subprocess.run(
        [sys.executable, "-c", code, str(TOOLS)],
        env={"RECHERCHE_DATA_ROOT": value}, capture_output=True, text=True,
    )
    assert run(str(tmp_path)).stdout.strip() == str(tmp_path)
    missing = run(str(tmp_path / "absent"))
    assert missing.returncode != 0 and "RECHERCHE_DATA_ROOT" in missing.stderr
