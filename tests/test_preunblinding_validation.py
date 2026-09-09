import hashlib
import json
from pathlib import Path

import numpy as np

from pulsar_pilot.preunblinding_validation import (
    build_deletion_units,
    generate_structured_null,
)


def test_structured_block_null_is_reproducible_and_block_limited() -> None:
    toa_count = 1_000
    factor = np.eye(2 * toa_count)
    days = np.arange(toa_count)
    variant = {
        "selected_native_innovation_block": "timing",
        "contaminated_probability": 0.01,
        "contaminated_standard_deviation_multiplier": 3.1718582673952787,
    }
    first, first_count = generate_structured_null(
        factor, np.random.default_rng(12345), variant, toa_count, days
    )
    second, second_count = generate_structured_null(
        factor, np.random.default_rng(12345), variant, toa_count, days
    )
    assert np.array_equal(first, second)
    assert first_count == second_count
    assert 2 <= first_count <= 25
    assert 0.8 <= np.var(first[:toa_count]) <= 1.2
    assert 0.8 <= np.var(first[toa_count:]) <= 1.2


def test_clustered_day_null_contaminates_paired_coordinates() -> None:
    toa_count = 200
    factor = np.eye(2 * toa_count)
    days = np.repeat(np.arange(100), 2)
    variant = {
        "selected_day_probability": 0.10,
        "contaminated_standard_deviation_multiplier": 2.8237419549367053,
    }
    values, contaminated_count = generate_structured_null(
        factor, np.random.default_rng(24680), variant, toa_count, days
    )
    assert values.shape == (2 * toa_count,)
    assert contaminated_count % 4 == 0
    assert contaminated_count > 0


def test_deletion_units_cover_rows_and_unique_days() -> None:
    units = build_deletion_units(np.asarray([59000, 59000, 59001, 59003]))
    assert len(units) == 7
    row_units = [unit for unit in units if unit["mode"] == "paired_wideband_toa_row"]
    day_units = [
        unit
        for unit in units
        if unit["mode"] == "all_rows_on_one_floor_mjd_utc_day"
    ]
    assert len(row_units) == 4
    assert len(day_units) == 3
    assert day_units[0]["removed_rows"] == [0, 1]


def test_execution_module_has_no_observed_residual_path() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (
        root / "src/pulsar_pilot/preunblinding_validation.py"
    ).read_text(encoding="utf-8")
    assert "WidebandTOAResiduals" not in source
    assert "observed-periodic" not in source
    assert "--execute-synthetic" in source


def test_execution_freeze_binds_implementation_and_keeps_search_locked() -> None:
    root = Path(__file__).resolve().parents[1]
    freeze = json.loads(
        (
            root
            / "protocol/PILOT1_PREUNBLINDING_EXECUTION_FREEZE_v0.1.json"
        ).read_text(encoding="utf-8")
    )
    assert freeze["status"] == "frozen_before_synthetic_execution"
    assert freeze["authorization"] == "exact_frozen_synthetic_validation_only"
    assert freeze["observed_residual_access_authorized"] is False
    assert freeze["observed_periodic_search_authorized"] is False
    assert freeze["new_recovery_randomness_authorized"] is False
    assert freeze["authorized_case_counts"]["structured_tail_nulls"] == 3000
    assert freeze["authorized_case_counts"]["deterministic_recovery_replays"] == 160
    assert freeze["authorized_case_counts"]["deletion_units"] == 749
    for relative, expected in freeze["frozen_sha256"].items():
        observed = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        assert observed == expected
