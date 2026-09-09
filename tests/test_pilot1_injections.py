import hashlib
import json
from pathlib import Path

import pytest

from pulsar_pilot.config import load_yaml
from pulsar_pilot.pilot1_injections import (
    THRESHOLD_LOCK_PATH,
    bracketed_crossing_amplitude,
    build_injection_order,
    injection_plan,
    projected_mass_moon_masses,
    verify_injection_freeze,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _plan() -> dict:
    return load_yaml(_root() / "config/pilot1.yaml")


def _threshold() -> dict:
    return json.loads((_root() / THRESHOLD_LOCK_PATH).read_text())


def test_injection_order_is_exact_deterministic_and_audited() -> None:
    order = build_injection_order(_plan())
    assert len(order) == 284
    assert len({case["case_id"] for case in order}) == 284
    assert len({case["seed"] for case in order}) == 284
    assert sum(case["full_covariance_audit"] for case in order) == 29
    assert sum(case["family"] == "main" for case in order) == 240
    assert sum(case["family"] == "annual" for case in order) == 28
    assert sum(case["family"] == "boundary" for case in order) == 16


def test_injection_plan_hashes_the_exact_order() -> None:
    plan = injection_plan(_plan(), _threshold())
    order = build_injection_order(_plan())
    canonical = json.dumps(order, sort_keys=True, separators=(",", ":")).encode()
    assert plan["execution_authorized"] is False
    assert plan["case_count"] == 284
    assert plan["full_covariance_audit_count"] == 29
    assert plan["case_order_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert plan["locked_threshold_delta_chi2"] == pytest.approx(23.33426855482562)


def test_bracketed_crossing_and_projected_mass_are_deterministic() -> None:
    cells = [
        {"amplitude_microseconds": 0.5, "fraction": 0.25},
        {"amplitude_microseconds": 1.0, "fraction": 0.75},
        {"amplitude_microseconds": 2.0, "fraction": 1.0},
    ]
    assert bracketed_crossing_amplitude(cells, 0.5) == pytest.approx(0.75)
    assert bracketed_crossing_amplitude(cells, 0.9) == pytest.approx(1.6)
    assert projected_mass_moon_masses(1.0, 100.0, 1.4) == pytest.approx(
        0.16109419267091107
    )


def test_injection_freeze_hashes_and_authorization() -> None:
    root = _root()
    relative = "protocol/PILOT1_INJECTION_FREEZE_v0.1.json"
    manifest = (root / "protocol/execution_freezes.sha256").read_text().strip().splitlines()
    expected = next(line.split("  ", 1)[0] for line in manifest if line.endswith(relative))
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
    result = verify_injection_freeze()
    assert result["status"] == "pass"
    assert result["failures"] == []
