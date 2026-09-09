import hashlib
import json
from pathlib import Path

from pulsar_pilot.config import load_yaml
from pulsar_pilot.sensitivity_extension import (
    CONFIG_PATH,
    _recovery_surface,
    build_extension_order,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_extension_inventory_is_exact_unique_and_deterministic() -> None:
    config = load_yaml(_root() / CONFIG_PATH)
    order = build_extension_order(config)
    assert len(order) == 240
    assert len({case["case_id"] for case in order}) == 240
    assert len({case["seed"] for case in order}) == 240
    assert sum(case["full_covariance_audit"] for case in order) == 24
    assert hashlib.sha256(
        json.dumps(order, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def test_recovery_surface_requires_trigger_and_frequency() -> None:
    def record(amplitude: float, triggered: bool, recovered: bool) -> dict:
        return {
            "case": {"period_days": 100.0, "amplitude_microseconds": amplitude},
            "triggered": triggered,
            "frequency_recovered": recovered,
        }

    records = [
        record(0.1, True, False),
        record(0.2, True, True),
        record(0.3, True, True),
    ]
    result = _recovery_surface(records)
    cells = result["periods"]["100.0"]["cells"]
    assert [cell["fraction"] for cell in cells] == [0.0, 1.0, 1.0]
    assert result["recovered_definition"] == "triggered_and_frequency_recovered"
