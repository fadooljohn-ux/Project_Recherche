from pathlib import Path

from pulsar_pilot.config import load_pilot_config, load_yaml

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_target_and_cases() -> None:
    config = load_pilot_config(ROOT / "config" / "target.yaml")
    injections = load_yaml(ROOT / "config" / "injections.yaml")
    assert config.target_name == "J1744-1134"
    assert [case["id"] for case in injections["cases"]] == ["C0", "C1", "C2", "C3"]
    assert next(case for case in injections["cases"] if case["id"] == "C1")[
        "hard_recovery_gate"
    ]


def test_download_cap_is_one_gb_or_less() -> None:
    config = load_pilot_config(ROOT / "config" / "target.yaml")
    assert config.max_download_bytes <= 1_000_000_000
