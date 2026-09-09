import json
from pathlib import Path

from pulsar_pilot.release import INITIAL_V01_FREEZE, verify_initial_v01_release


def test_initial_v01_release_freeze_is_self_consistent() -> None:
    root = Path(__file__).resolve().parents[1]
    freeze = json.loads((root / INITIAL_V01_FREEZE).read_text())
    assert freeze["status"] == "initial_v0.1_promoted"
    assert freeze["promotion_score"] == "22_of_22"
    assert freeze["observed_residual_periodic_search_authorized"] is False
    result = verify_initial_v01_release()
    assert result["status"] == "pass"
    assert result["external_records_checked"] is False
