"""Current behavioral tests and explicitly version-bound historical checks."""

import json
from pathlib import Path


def pytest_collection_modifyitems(config, items):
    history = json.loads(Path(__file__).with_name("historical_state.json").read_text())
    selected, historical = [], []
    for item in items:
        (historical if item.nodeid in history else selected).append(item)
    if historical:
        config.hook.pytest_deselected(items=historical)
        items[:] = selected


def pytest_report_header(config):
    return (
        "Historical release-state checks: run tools/check_history.py against recorded Git versions"
    )
