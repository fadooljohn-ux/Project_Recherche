"""Focused checks of the new observed-search boundary, without observed data."""

import importlib
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


@pytest.fixture
def search(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "tools"))
    return importlib.import_module("b1937_search")


def test_grid_and_annual_mapping_match_qualified_metadata(search):
    from pulsar_pilot.pilot1_runtime import build_search_frequency_grid

    frequencies, grid = build_search_frequency_grid(
        np.array([0.0, 5798.043101777104]), 30.0, 2000.0, 5
    )
    assert np.array_equal(search.frequencies_from_grid(grid), frequencies)
    mask = search.build_annual_mask(frequencies, [365.25])
    assert len(mask["masked_grid_indices"]) == 1
    assert mask["masked_grid_indices"][0] == np.argmin(abs(1 / frequencies - 365.25))


def test_masked_peak_cannot_hide_unmasked_peak_or_change_threshold(search, tmp_path):
    frequencies = np.array([0.002, 0.003, 0.004])
    scanner = SimpleNamespace(
        frequencies_per_day=frequencies,
        scan=lambda _: {
            "all_delta_chi2": np.array([10.0, 100.0, 22.485020743823544]),
            "trigger_statistic": 100.0,
            "peak_period_days": 1 / 0.003,
        },
    )
    context = SimpleNamespace(scanner=scanner)
    counts = []
    result = search.analyze(
        context,
        np.zeros(3),
        None,
        {"threshold": 22.485020743823544, "annual_grid_mapping": {"masked_grid_indices": [1]}},
        tmp_path,
        counts.append,
    )
    assert result["selected_peak"]["index"] == 2
    assert result["disposition"] == "NO_TRIGGER"  # equality is not strictly greater
    assert counts == ["scans"]


def test_nonfinite_vector_never_reaches_scan(search, tmp_path):
    with pytest.raises(RuntimeError, match="nonfinite"):
        search.analyze(None, np.array([np.nan]), None, {}, tmp_path, lambda _: None)


def test_execution_acknowledgment_precedes_any_data_access(search, tmp_path, monkeypatch):
    package = tmp_path / "package.json"
    package.write_text("{}")

    def forbidden(*args):
        pytest.fail("Package/data verification should not be reached")

    monkeypatch.setattr(search, "check", forbidden)
    with pytest.raises(RuntimeError, match="explicit"):
        search.run(package, "wrong-digest")
    assert not (tmp_path / "b1937-observed-search-intent.json").exists()


def test_claim_cannot_be_consumed_twice(search, tmp_path):
    package = tmp_path / "package.json"
    package.write_text("{}")
    search.claim(tmp_path, package)
    original = (tmp_path / "b1937-observed-search-intent.json").read_bytes()
    with pytest.raises(FileExistsError):
        search.claim(tmp_path, package)
    assert (tmp_path / "b1937-observed-search-intent.json").read_bytes() == original


def test_runtime_failure_preserves_terminal_and_consumed_attempt(search, tmp_path, monkeypatch):
    package = tmp_path / "package.json"
    package.write_text("{}")
    data = tmp_path / "data"
    (data / "metadata").mkdir(parents=True)
    (data / "metadata/resources.json").write_text("{}")
    (data / "metadata/development-environment.json").write_text("{}")
    output = data / "observed-runs" / search.POLICY["run_id"]
    monkeypatch.setattr(
        search, "check", lambda _: {"data_root": str(data), "run_root": str(output)}
    )
    monkeypatch.setattr(search, "OfflineRuntimeBoundary", lambda *args: nullcontext(None))

    def broken(*args, **kwargs):
        raise RuntimeError("deliberate context setup failure")

    monkeypatch.setattr(search, "prepare_context", broken)
    terminal = search.run(package, search.sha(package))
    assert terminal["terminal_state"] == "operational_failure"
    assert search.read(output / "failure.json")["accounting"]["scans"] == 0
    assert search.read(output / "ledger.json")["runtime_active"] is False
    with pytest.raises(RuntimeError, match="already exists"):
        search.run(package, search.sha(package))
