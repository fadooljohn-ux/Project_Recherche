from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PilotConfig:
    raw: dict[str, Any]

    @property
    def archive_name(self) -> str:
        return str(self.raw["dataset"]["archive_name"])

    @property
    def archive_url(self) -> str:
        return str(self.raw["dataset"]["archive_url"])

    @property
    def published_md5(self) -> str:
        return str(self.raw["dataset"]["published_md5"])

    @property
    def target_name(self) -> str:
        return str(self.raw["target"]["name"])

    @property
    def max_download_bytes(self) -> int:
        return int(self.raw["analysis"]["max_download_bytes"])

    @property
    def weighted_rms_tolerance_fraction(self) -> float:
        return float(self.raw["analysis"]["weighted_rms_tolerance_fraction"])

    @property
    def parameter_sigma_tolerance(self) -> float:
        return float(self.raw["analysis"]["parameter_sigma_tolerance"])

    @property
    def numerical_tolerance_ulps(self) -> int:
        return int(self.raw["analysis"]["numerical_tolerance_ulps"])

    @property
    def max_fit_iterations(self) -> int:
        return int(self.raw["reproduction"]["max_iterations"])

    @property
    def free_base_parameters(self) -> list[str]:
        return [str(value) for value in self.raw["reproduction"]["free_base_parameters"]]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"Expected a mapping in {path}")
    return value


def load_pilot_config(path: Path) -> PilotConfig:
    raw = load_yaml(path)
    for key in ("dataset", "target", "analysis", "reproduction"):
        if key not in raw:
            raise ValueError(f"Missing required key {key!r} in {path}")
    if raw["target"].get("name") != "J1744-1134":
        raise ValueError("Pilot 0 is frozen to J1744-1134")
    if raw["reproduction"].get("fitter") != "WidebandDownhillFitter":
        raise ValueError("Gate G2 is frozen to WidebandDownhillFitter")
    if raw["reproduction"].get("free_dmx") is not True:
        raise ValueError("Gate G2 requires the released DMX parameters to remain free")
    return PilotConfig(raw=raw)
