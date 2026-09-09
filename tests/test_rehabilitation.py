import io
import json
import os
from datetime import UTC, datetime, timedelta

import pytest

from pulsar_pilot import pilot2_ioc_harness as ioc
from pulsar_pilot.pilot2_development import development_cases, solver_check_cases
from pulsar_pilot.pilot2_offline_resources import ResourceOpenTracer
from pulsar_pilot.runtime_limits import ResourceLimitExceeded, RuntimeLimits


def test_astropy_style_fileio_is_traced_only_inside_boundary(tmp_path):
    resource = tmp_path / "iers.dat"
    resource.write_bytes(b"controlled")
    with ResourceOpenTracer(tmp_path) as tracer, io.FileIO(resource, "r") as handle:
        assert handle.read() == b"controlled"
    assert tracer.opened == {"iers.dat"}
    other = tmp_path / "later.dat"
    other.write_bytes(b"later")
    assert tracer.opened == {"iers.dat"}


def test_long_case_reports_liveness_separately_from_progress(tmp_path):
    value = ioc._status_value("pilot2-ioc-dev-status-test", "running", "run", 1, 4, 1, "Working")
    value["updated_at"] = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    (tmp_path / "status.json").write_text(json.dumps(value))
    observed = ioc.observe_status(tmp_path)
    assert observed["pid"] == os.getpid()
    assert observed["observed_process_state"] == "running"
    assert observed["heartbeat_state"] == "process_alive"
    assert observed["progress_state"] == "waiting"
    assert observed["checkpoint"] == 1
    assert observed["observed_rss_gib"] > 0


def test_limits_fail_before_starting_more_work(tmp_path, monkeypatch):
    limits = RuntimeLimits(tmp_path, wall_seconds=1, rss_gib=16, disk_gib=1)
    monkeypatch.setattr("pulsar_pilot.runtime_limits.time.monotonic", lambda: limits.started + 2)
    with pytest.raises(ResourceLimitExceeded, match="Elapsed time"):
        limits.check()


def test_development_fixture_is_stable_and_covers_required_families():
    cases = development_cases()  # Builder also checks both formal seed inventories.
    assert cases == development_cases()
    assert {c["family"] for c in cases} == {"main", "phase_reference", "annual", "boundary"}
    assert len({c["seed"] for c in cases}) == 4
    assert all(c["case_id"].startswith("recherche-dev-") for c in cases)


def test_solver_check_reuses_the_two_retained_annual_fixtures():
    cases = solver_check_cases()
    assert len(cases) == 3
    assert [c["family"] for c in cases].count("annual") == 2
    assert {c["seed"] for c in cases if c["family"] == "annual"} == {
        next(c["seed"] for c in development_cases() if c["family"] == "annual"),
        8183475920083870252,
    }
