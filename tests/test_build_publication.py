"""Redaction rules of the publication builder (synthetic text only)."""
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_publication as bp

HOME = "/" + "Users" + "/" + "someone"          # built in pieces so this file holds no literal home path


def test_paths_become_relative_or_symbolic():
    cases = {
        HOME + "/Documents/ChatGPT/Project Recherche Data/tpa-batch03/x.json": "../Project Recherche Data/tpa-batch03/x.json",
        HOME + "/Documents/Project Recherche/Project Recherche Data/a": "../Project Recherche Data/a",
        HOME + "/Documents/Project Recherche/Recherche Recovery/2026/b.xlsx": "../Recherche Recovery/2026/b.xlsx",
        HOME + "/Documents/ChatGPT/Project Recherche/results/r.json": "results/r.json",
        '"' + HOME + '/Documents/Project Recherche/Project Recherche"': '"."',
        HOME + "/Documents/Project Recherche/RELOCATION.tsv": "../RELOCATION.tsv",
        HOME + "/.pixi/bin/pixi run python": "pixi run python",
        HOME + "/.cache/recherche-tempo2/x": "${HOME}/.cache/recherche-tempo2/x",
        "${EXTERNAL_VOLUME}/Vera": "${EXTERNAL_VOLUME}/Vera",
        "${HOME}/data": "${HOME}/data",
    }
    for before, after in cases.items():
        assert bp.redact(before.encode()).decode() == after
        assert not bp.contains_host_path(bp.redact(before.encode()))


def test_text_without_a_home_path_is_untouched():
    data = b"results/observed/x.json and ../Project Recherche Data/y"
    assert bp.redact_file("a.txt", data) is data


def test_zip_members_are_redacted_and_order_kept():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/a.xml", "<t>" + HOME + "/Documents/ChatGPT/Project Recherche/docs/d.md</t>")
        archive.writestr("xl/b.xml", "<t>clean</t>")
    out = bp.redact_file("book.xlsx", buffer.getvalue())
    result = zipfile.ZipFile(io.BytesIO(out))
    assert result.namelist() == ["xl/a.xml", "xl/b.xml"]
    assert result.read("xl/a.xml") == b"<t>docs/d.md</t>" and result.read("xl/b.xml") == b"<t>clean</t>"
    assert not bp.contains_host_path(out) and bp.contains_host_path(buffer.getvalue())
