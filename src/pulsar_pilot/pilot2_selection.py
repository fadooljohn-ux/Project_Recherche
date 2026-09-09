from __future__ import annotations

import hashlib
import statistics
import tarfile
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_text(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace")


def _combined_key(filename: str, split_suffixes: list[str]) -> str | None:
    key = filename.split("_PINT", 1)[0]
    if any(key.endswith(suffix) for suffix in split_suffixes):
        return None
    return key


def _parse_par(text: str) -> dict[str, Any]:
    values: dict[str, list[str]] = {}
    has_binary = False
    has_red_noise = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        pieces = stripped.split()
        values.setdefault(pieces[0], pieces[1:])
        has_binary = has_binary or pieces[0] == "BINARY"
        has_red_noise = has_red_noise or pieces[0].startswith(
            ("TNRED", "PLRedNoise")
        )
    required = ("PSR", "NTOA", "START", "FINISH", "ELAT")
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise RuntimeError(f"Released parameter file lacks {missing}")
    return {
        "psr": values["PSR"][0],
        "par_ntoa": int(float(values["NTOA"][0])),
        "par_start_mjd": float(values["START"][0]),
        "par_finish_mjd": float(values["FINISH"][0]),
        "ecliptic_latitude_degrees": float(values["ELAT"][0]),
        "binary_model": has_binary,
        "released_red_noise": has_red_noise,
    }


def _parse_tim(text: str) -> dict[str, Any]:
    mjds: list[float] = []
    uncertainties: list[float] = []
    observatories: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pieces = stripped.split()
        if pieces[0] in {
            "C",
            "#",
            "FORMAT",
            "MODE",
            "EFAC",
            "EQUAD",
            "JUMP",
            "INCLUDE",
        }:
            continue
        if len(pieces) < 5:
            continue
        try:
            mjd = float(pieces[2])
            uncertainty = float(pieces[3])
        except ValueError:
            continue
        mjds.append(mjd)
        uncertainties.append(uncertainty)
        observatories.add(pieces[4])
    if not mjds:
        raise RuntimeError("Timing file contains no active TOAs")
    return {
        "active_toa_count": len(mjds),
        "unique_floor_mjd_days": len({int(value) for value in mjds}),
        "start_mjd": min(mjds),
        "finish_mjd": max(mjds),
        "span_days": max(mjds) - min(mjds),
        "median_toa_uncertainty_microseconds": statistics.median(uncertainties),
        "p90_toa_uncertainty_microseconds": sorted(uncertainties)[
            int(0.9 * (len(uncertainties) - 1))
        ],
        "observatories": sorted(observatories),
    }


def _noise_inventory_has_red_noise(text: str) -> bool:
    normalized = text.lower()
    return any(
        marker in normalized
        for marker in ("red_noise", "rednoise", "tnred", "plrednoise")
    )


def _clipped_score(value: float, floor: float, best: float) -> float:
    if best <= floor:
        raise ValueError("Score best must exceed floor")
    return min(1.0, max(0.0, (value - floor) / (best - floor)))


def _score(record: dict[str, Any], ranking: dict[str, Any]) -> dict[str, float]:
    precision = ranking["precision"]
    precision_score = _clipped_score(
        float(precision["floor_microseconds"])
        - float(record["median_toa_uncertainty_microseconds"]),
        0.0,
        float(precision["floor_microseconds"])
        - float(precision["best_microseconds"]),
    )
    span = ranking["span"]
    days = ranking["unique_days"]
    toas = ranking["active_toas"]
    geometry = ranking["annual_geometry"]
    components = {
        "precision": precision_score * float(precision["weight"]),
        "span": _clipped_score(
            float(record["span_days"]),
            float(span["floor_days"]),
            float(span["best_days"]),
        )
        * float(span["weight"]),
        "unique_days": _clipped_score(
            float(record["unique_floor_mjd_days"]),
            float(days["floor"]),
            float(days["best"]),
        )
        * float(days["weight"]),
        "active_toas": _clipped_score(
            float(record["active_toa_count"]),
            float(toas["floor"]),
            float(toas["best"]),
        )
        * float(toas["weight"]),
        "annual_geometry": _clipped_score(
            abs(float(record["ecliptic_latitude_degrees"])),
            float(geometry["floor_absolute_degrees"]),
            float(geometry["best_absolute_degrees"]),
        )
        * float(geometry["weight"]),
        "no_released_red_noise": (
            0.0
            if record["released_red_noise"]
            else float(ranking["no_released_red_noise"]["weight"])
        ),
        "isolated_timing_model": (
            0.0
            if record["binary_model"]
            else float(ranking["isolated_timing_model"]["weight"])
        ),
    }
    return {**components, "total": sum(components.values())}


def build_selection(archive_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    expected_archive = config["archive"]
    if archive_path.stat().st_size != int(expected_archive["bytes"]):
        raise RuntimeError("Archive size mismatch")
    if _sha256(archive_path) != expected_archive["sha256"]:
        raise RuntimeError("Archive hash mismatch")
    base = str(expected_archive["member_root"])
    suffixes = list(config["hard_eligibility"]["exclude_observatory_split_suffixes"])
    relevant_prefixes = (
        f"{base}/wideband/par/",
        f"{base}/wideband/tim/",
        f"{base}/wideband/noise/",
        f"{base}/wideband/config/",
        f"{base}/wideband/dmx/",
        f"{base}/correlations/wideband/",
    )
    payloads: dict[str, bytes] = {}
    with tarfile.open(archive_path, "r|gz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.startswith(relevant_prefixes):
                continue
            handle = archive.extractfile(member)
            if handle is None:
                raise RuntimeError(f"Cannot read archive member {member.name}")
            payloads[member.name] = handle.read()

    par_members: dict[str, str] = {}
    tim_members: dict[str, str] = {}
    for name in payloads:
        filename = Path(name).name
        if filename.startswith("._"):
            continue
        if name.startswith(f"{base}/wideband/par/") and name.endswith(".par"):
            key = _combined_key(filename, suffixes)
            if key is not None:
                par_members[key] = name
        if name.startswith(f"{base}/wideband/tim/") and name.endswith(".tim"):
            key = _combined_key(filename, suffixes)
            if key is not None:
                tim_members[key] = name

    candidates: list[dict[str, Any]] = []
    hard = config["hard_eligibility"]
    for key in sorted(set(par_members) & set(tim_members)):
        par_member = par_members[key]
        tim_member = tim_members[key]
        par = _parse_par(_read_text(payloads[par_member]))
        tim = _parse_tim(_read_text(payloads[tim_member]))
        psr = str(par["psr"])
        companion_names = {
            "noise": f"{base}/wideband/noise/{psr}.wb.pars.txt",
            "config": f"{base}/wideband/config/{psr}.wb.yaml",
            "dmx": f"{base}/wideband/dmx/{psr}_dmxparse.wb.out",
            "correlation": (
                f"{base}/correlations/wideband/"
                f"{Path(par_member).stem}.correlation.txt"
            ),
        }
        par["released_red_noise"] = bool(par["released_red_noise"]) or (
            companion_names["noise"] in payloads
            and _noise_inventory_has_red_noise(
                _read_text(payloads[companion_names["noise"]])
            )
        )
        gates = {
            "not_prior_target": psr != config["prior_target_excluded"],
            "active_toa_minimum": tim["active_toa_count"]
            >= int(hard["active_toa_count_minimum"]),
            "active_toa_maximum": tim["active_toa_count"]
            <= int(hard["active_toa_count_maximum"]),
            "unique_days_minimum": tim["unique_floor_mjd_days"]
            >= int(hard["unique_floor_mjd_days_minimum"]),
            "span_minimum": tim["span_days"] >= float(hard["span_days_minimum"]),
            "median_uncertainty_maximum": tim[
                "median_toa_uncertainty_microseconds"
            ]
            <= float(hard["median_toa_uncertainty_microseconds_maximum"]),
            "absolute_ecliptic_latitude_minimum": abs(
                float(par["ecliptic_latitude_degrees"])
            )
            >= float(hard["absolute_ecliptic_latitude_degrees_minimum"]),
            "par_ntoa_matches": par["par_ntoa"] == tim["active_toa_count"],
            "required_companion_products": all(
                name in payloads for name in companion_names.values()
            ),
        }
        eligible = all(gates.values())
        record = {
            "psr": psr,
            **tim,
            **par,
            "archive_members": {
                "par": par_member,
                "tim": tim_member,
                **companion_names,
            },
            "hard_gates": gates,
            "eligible": eligible,
        }
        record["score"] = (
            _score(record, config["ranking"]["components"])
            if eligible
            else None
        )
        candidates.append(record)

    eligible = [record for record in candidates if record["eligible"]]
    if not eligible:
        raise RuntimeError("No target passes the frozen hard gates")
    ranked = sorted(
        eligible,
        key=lambda record: (
            -float(record["score"]["total"]),
            float(record["median_toa_uncertainty_microseconds"]),
            str(record["psr"]),
        ),
    )
    selected = ranked[0]
    selected_members: dict[str, Any] = {}
    for label, name in selected["archive_members"].items():
        payload = payloads[name]
        selected_members[label] = {
            "archive_member": name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

    return {
        "schema_version": 1,
        "selection_id": config["selection_id"],
        "status": "selected_metadata_only_no_observed_access",
        "archive": config["archive"],
        "candidate_count": len(candidates),
        "eligible_count": len(eligible),
        "selected_target": selected["psr"],
        "selected_score": selected["score"],
        "selected_metrics": {
            key: selected[key]
            for key in (
                "active_toa_count",
                "unique_floor_mjd_days",
                "span_days",
                "median_toa_uncertainty_microseconds",
                "p90_toa_uncertainty_microseconds",
                "ecliptic_latitude_degrees",
                "binary_model",
                "released_red_noise",
                "observatories",
            )
        },
        "selected_archive_members": selected_members,
        "eligible_ranking": [
            {
                "rank": rank,
                "psr": record["psr"],
                "score": record["score"],
                "active_toa_count": record["active_toa_count"],
                "unique_floor_mjd_days": record["unique_floor_mjd_days"],
                "span_days": record["span_days"],
                "median_toa_uncertainty_microseconds": record[
                    "median_toa_uncertainty_microseconds"
                ],
                "absolute_ecliptic_latitude_degrees": abs(
                    record["ecliptic_latitude_degrees"]
                ),
                "binary_model": record["binary_model"],
                "released_red_noise": record["released_red_noise"],
            }
            for rank, record in enumerate(ranked, 1)
        ],
        "all_candidates": candidates,
        "authority_boundary": {
            "manual_override_authorized": False,
            "observed_residual_access_authorized": False,
            "observed_periodic_search_authorized": False,
            "selection_authorizes_extraction_or_calibration": False,
        },
    }
