from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def hash_file(path: Path, algorithm: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def logical_path(path: Path, data_root: Path) -> str:
    return path.resolve().relative_to(data_root.resolve()).as_posix()


def verify_sha256_manifest(manifest: Path, data_root: Path) -> dict[str, Any]:
    checked: list[dict[str, Any]] = []
    root = data_root.resolve()
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        try:
            expected, relative_text = line.split("  ", 1)
        except ValueError as exc:
            raise ValueError(f"Malformed manifest line {line_number}") from exc
        relative = Path(relative_text)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe manifest path on line {line_number}: {relative_text}")
        candidate = (root / relative).resolve()
        if root not in candidate.parents:
            raise ValueError(f"Manifest path escapes data root on line {line_number}")
        if not candidate.is_file():
            raise FileNotFoundError(f"Manifest file missing: {relative_text}")
        actual = hash_file(candidate, "sha256")
        checked.append(
            {
                "logical_path": relative.as_posix(),
                "bytes": candidate.stat().st_size,
                "sha256": actual,
                "status": "pass" if actual == expected else "fail",
            }
        )
    failures = [item for item in checked if item["status"] != "pass"]
    return {
        "status": "pass" if checked and not failures else "fail",
        "files_checked": len(checked),
        "bytes_checked": sum(int(item["bytes"]) for item in checked),
        "failures": failures,
    }
