import hashlib
import json
from pathlib import Path

import numpy as np

from pulsar_pilot.config import load_yaml
from pulsar_pilot.one_shot_search import (
    CANDIDATE_SCHEMA_PATH,
    CONFIG_PATH,
    FREEZE_PATH,
    IMPLEMENTATION_PATH,
    PACKAGE_MANIFEST_PATH,
    _mandatory_context,
    _verify_manifest,
    build_annual_mask,
    build_one_shot_plan,
    select_strongest_unmasked,
    verify_execution_authority,
)


def test_annual_mask_is_exact_unique_and_deterministic() -> None:
    frequencies = np.asarray([1 / 500, 1 / 380, 1 / 365.25, 1 / 350, 1 / 100])
    mask = build_annual_mask(frequencies, [350.0, 365.25, 380.0])
    assert mask["masked_grid_indices"] == [3, 2, 1]
    assert mask["masked_grid_periods_days"] == [350.0, 365.25, 380.0]
    assert len(set(mask["masked_grid_indices"])) == 3


def test_strongest_unmasked_cell_has_candidate_authority() -> None:
    frequencies = np.asarray([1 / 500, 1 / 380, 1 / 365.25, 1 / 350, 1 / 100])
    statistics = np.asarray([3.0, 99.0, 100.0, 98.0, 25.0])
    selected = select_strongest_unmasked(statistics, frequencies, [1, 2, 3])
    assert selected["index"] == 4
    assert selected["statistic"] == 25.0
    assert selected["period_days"] == 100.0


def test_plan_is_metadata_only_and_keeps_observed_access_false() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / CONFIG_PATH)
    times = np.linspace(50_000.0, 55_000.0, 20)
    days = np.repeat(np.arange(10), 2)
    plan = build_one_shot_plan(config, times, days)
    assert plan["observed_residual_access_authorized"] is False
    assert plan["observed_periodic_search_authorized"] is False
    assert plan["deletion_units"] == 30
    assert len(plan["annual_mask"]["masked_grid_indices"]) == 3


def test_fable_conditions_c1_through_c7_are_bound() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / CONFIG_PATH)
    schema = json.loads((root / CANDIDATE_SCHEMA_PATH).read_text(encoding="utf-8"))
    context = _mandatory_context()

    assert config["deletion_diagnostics"]["deletion_checks_as_hard_vetoes"] is False
    assert config["deletion_diagnostics"]["classification"] == "advisory_only"
    assert config["deletion_diagnostics"]["paired_row_units"] == 433
    assert config["deletion_diagnostics"]["utc_day_units"] == 316
    assert config["frozen_context"]["further_tail_reroll_authorized"] is False
    assert config["frozen_context"]["new_recovery_randomness_authorized"] is False
    assert set(schema["properties"]["mandatory_context"]["required"]) <= set(context)
    assert config["robust_refit"]["included"] is False
    assert config["detector"]["locked_threshold_delta_chi2"] == 23.33426855482562
    assert config["detector"]["period_minimum_days"] == 30.0
    assert config["detector"]["period_maximum_days"] == 2000.0
    assert config["detector"]["frequency_oversampling"] == 5
    assert config["resources"] == {
        "wall_hours_maximum": 4.0,
        "peak_memory_gib_maximum": 16.0,
        "complete_data_root_gib_maximum": 5.0,
    }
    assert "resource_envelope_passed" in schema["properties"]["integrity"]["required"]
    assert config["observed_residual_access_authorized"] is False
    assert config["observed_periodic_search_authorized"] is False


def test_advisory_labels_have_no_candidate_authority_in_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / CANDIDATE_SCHEMA_PATH).read_text(encoding="utf-8"))
    deletion_mode = schema["$defs"]["deletionMode"]
    assert deletion_mode["properties"]["candidate_authority"]["const"] == (
        "none_advisory_only"
    )
    assert deletion_mode["properties"]["mechanical_label"]["enum"] == [
        "DELETION_FRAGILE",
        "DELETION_STABLE",
    ]


def test_authority_precedes_observed_residual_import_and_intent_precedes_access() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / IMPLEMENTATION_PATH).read_text(encoding="utf-8")
    runner = source[source.index("def run_one_shot") : source.index("def main")]
    assert runner.index("verify_execution_authority") < runner.index(
        "from pint.residuals import WidebandTOAResiduals"
    )
    assert runner.index("_write_json(intent_path, intent)") < runner.index(
        "WidebandTOAResiduals(toas, model)"
    )
    assert runner.count("_write_json(intent_path, intent)") == 1


def test_execution_is_locked_without_both_final_records(monkeypatch, tmp_path: Path) -> None:
    package = {
        "status": "pass",
        "failures": [],
        "freeze_sha256": "a" * 64,
        "package_manifest_sha256": "b" * 64,
        "implementation_sha256": "c" * 64,
        "candidate_schema_sha256": "d" * 64,
    }
    monkeypatch.setattr(
        "pulsar_pilot.one_shot_search.verify_package", lambda _data_root: package
    )
    monkeypatch.setattr(
        "pulsar_pilot.one_shot_search.repository_root", lambda: tmp_path
    )
    authority = verify_execution_authority(tmp_path / "data")
    assert authority["status"] == "locked"
    assert authority["observed_residual_access_authorized"] is False
    assert authority["observed_periodic_search_authorized"] is False
    assert authority["failures"] == [
        "final Fable sign-off is absent",
        "explicit user authorization is absent",
    ]


def test_runtime_manifest_verifier_rejects_a_changed_file(tmp_path: Path) -> None:
    payload = tmp_path / "payload.txt"
    payload.write_text("expected\n", encoding="utf-8")
    manifest = tmp_path / "manifest.sha256"
    expected = hashlib.sha256(payload.read_bytes()).hexdigest()
    manifest.write_text(f"{expected}  payload.txt\n", encoding="utf-8")
    assert _verify_manifest(tmp_path, manifest) == []
    payload.write_text("changed\n", encoding="utf-8")
    assert _verify_manifest(tmp_path, manifest) == [
        "manifest hash mismatch: payload.txt"
    ]


def test_one_shot_freeze_and_manifest_are_hash_bound() -> None:
    root = Path(__file__).resolve().parents[1]
    freeze = json.loads((root / FREEZE_PATH).read_text(encoding="utf-8"))
    manifest = root / PACKAGE_MANIFEST_PATH
    assert freeze["status"] == "frozen_for_final_fable_review"
    assert freeze["authorization"] == "preparation_only_execution_locked"
    assert freeze["observed_residual_access_authorized"] is False
    assert freeze["observed_periodic_search_authorized"] is False
    assert freeze["deletion_checks_as_hard_vetoes"] is False
    assert freeze["robust_refit_included"] is False
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == freeze[
        "package_manifest_sha256"
    ]
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
