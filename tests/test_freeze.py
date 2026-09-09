import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_record_hashes_and_config_snapshot() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = root / "protocol" / "freeze_records.sha256"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        assert _sha256(root / relative) == expected

    freeze = json.loads((root / "protocol" / "FREEZE_RECORD_v0.7.json").read_text())
    for section in ("config_sha256", "implementation_sha256", "scorecard_sha256"):
        for relative, expected in freeze[section].items():
            assert _sha256(root / relative) == expected
    assert _sha256(root / "pixi.lock") == freeze["pixi_lock_sha256"]
    authorization = root / "protocol" / "STAGE_C_AUTHORIZATION_v0.5.json"
    assert _sha256(authorization) == freeze["stage_c_authorization_sha256"]
