from pathlib import Path

import pytest

from pulsar_pilot.provenance import hash_file, logical_path, verify_sha256_manifest


def test_hash_and_logical_path(tmp_path: Path) -> None:
    root = tmp_path / "data"
    path = root / "raw" / "sample.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"abc")
    assert hash_file(path, "sha256") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert logical_path(path, root) == "raw/sample.txt"


def test_verify_sha256_manifest(tmp_path: Path) -> None:
    root = tmp_path / "data"
    path = root / "raw" / "sample.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"abc")
    manifest = tmp_path / "files.sha256"
    manifest.write_text(f"{hash_file(path, 'sha256')}  raw/sample.txt\n", encoding="utf-8")
    result = verify_sha256_manifest(manifest, root)
    assert result == {
        "status": "pass",
        "files_checked": 1,
        "bytes_checked": 3,
        "failures": [],
    }


def test_verify_sha256_manifest_rejects_traversal(tmp_path: Path) -> None:
    manifest = tmp_path / "files.sha256"
    manifest.write_text(f"{'0' * 64}  ../outside\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe manifest path"):
        verify_sha256_manifest(manifest, tmp_path / "data")
