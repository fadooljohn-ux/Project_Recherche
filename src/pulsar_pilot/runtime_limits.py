"""Cooperative limits checked between expensive numerical operations."""

from __future__ import annotations

import time
from pathlib import Path

import psutil


class ResourceLimitExceeded(RuntimeError):
    pass


class RuntimeLimits:
    def __init__(self, root: Path, *, wall_seconds: float, rss_gib: float, disk_gib: float):
        self.root = root
        self.started = time.monotonic()
        self.wall_seconds, self.rss_gib, self.disk_gib = wall_seconds, rss_gib, disk_gib
        self.process = psutil.Process()

    def check(self, *, disk: bool = False) -> None:
        if time.monotonic() - self.started > self.wall_seconds:
            raise ResourceLimitExceeded("Elapsed time limit exceeded")
        if self.process.memory_info().rss / 1024**3 > self.rss_gib:
            raise ResourceLimitExceeded("Resident memory limit exceeded")
        if (
            disk
            and sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()) / 1024**3
            > self.disk_gib
        ):
            raise ResourceLimitExceeded("Data size limit exceeded")
