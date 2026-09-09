import json
from pathlib import Path

import pytest

from pulsar_pilot.config import load_yaml
from pulsar_pilot.preunblinding import (
    CONFIG_PATH,
    build_deletion_replay_inventory,
    build_structured_tail_inventory,
    inventory_hashes,
    verify_freeze,
)
from pulsar_pilot.tail_robustness import theoretical_mixture_excess_kurtosis


def test_preunblinding_inventory_is_exact_and_disjoint() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / CONFIG_PATH)
    structured = build_structured_tail_inventory(config)
    replay = build_deletion_replay_inventory(config)
    assert len(structured) == 3000
    assert len({item["case_id"] for item in structured}) == 3000
    assert len({item["seed"] for item in structured}) == 3000
    assert len(replay) == 160
    assert len({item["source_case_id"] for item in replay}) == 160
    assert all(len(item["deletion_units"]) == 2 for item in replay)


def test_block_multipliers_match_frozen_kurtosis_targets() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / CONFIG_PATH)
    variants = config["structured_tail_variants"]["variants"]
    for variant in variants[:2]:
        observed = theoretical_mixture_excess_kurtosis(
            config["structured_tail_variants"]["common"]["contaminated_probability"],
            variant["contaminated_standard_deviation_multiplier"],
        )
        assert observed == pytest.approx(
            variant["target_innovation_excess_kurtosis"], abs=1e-12
        )


def test_preunblinding_policy_keeps_search_locked() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / CONFIG_PATH)
    assert config["observed_residual_access_authorized"] is False
    assert config["observed_periodic_search_authorized"] is False
    assert config["locked_detector"]["threshold_retuning_authorized"] is False
    assert (
        config["sequential_decision_control"]["further_tail_reroll_authorized"]
        is False
    )
    assert config["final_review"]["planned_independent_reviewer"] == "Claude Fable 5"
    assert (
        config["final_review"]["pipeline_operator_may_sign_as_independent_reviewer"]
        is False
    )


def test_preunblinding_freeze_is_self_consistent() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / CONFIG_PATH)
    freeze = json.loads(
        (root / "protocol/PILOT1_PREUNBLINDING_VALIDATION_FREEZE_v0.1.json").read_text()
    )
    assert freeze["inventory_sha256"] == inventory_hashes(config)
    assert verify_freeze()["status"] == "pass"
