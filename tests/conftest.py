"""Current behavioral tests and explicitly version-bound historical checks."""

import json
from pathlib import Path


def pytest_collection_modifyitems(config, items):
    history = set(json.loads(Path(__file__).with_name("historical_state.json").read_text()))
    # In the redacted public edition, tests bound to the private bytes of redacted files cannot pass.
    if (Path(__file__).resolve().parents[1] / "publication-manifest.json").exists():
        history |= set(json.loads(Path(__file__).with_name("publication_state.json").read_text())["tests"])
    selected, historical = [], []
    for item in items:
        (historical if item.nodeid in history else selected).append(item)
    if historical:
        config.hook.pytest_deselected(items=historical)
        items[:] = selected


def pytest_report_header(config):
    lines = ["Historical release-state checks: run tools/check_history.py against recorded Git versions"]
    if (Path(__file__).resolve().parents[1] / "publication-manifest.json").exists():
        lines.append("Public edition: tests bound to redacted files are deselected (tests/publication_state.json)")
    return lines
