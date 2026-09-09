"""Prepare and diagnose four isolated MPTA chromatic profiles; never scan observed residuals."""

import argparse
import copy
import json
import shutil
import tarfile
from pathlib import Path

import chromatic_timing as chromatic
import mpta_batch as batch
import numpy as np
import target_calibration as cal

from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner

TARGETS = ("J1721-2457", "J1832-0836", "J1747-4036", "J1804-2858")
DEFAULT = batch.REPO.parent / "Project Recherche Data/chromatic-support-20260908"


def prepare(data, previous):
    """Copy verified release inputs and bind Table 2 MAP shapes, without orbit seeds."""
    prior = cal.read(previous / "selection.json")
    source = Path(prior.get("source_evidence_root", previous))
    tables_path = source / "research/mpta-tables.json"
    if cal.digest(tables_path) != prior["source_hashes"]["research/mpta-tables.json"]:
        raise ValueError("Published parameter table changed")
    table = {r[0]: r for r in cal.read(tables_path) if len(r) == 9 and r[0] in TARGETS}
    rows = []
    for target in TARGETS:
        row = copy.deepcopy(next(r for r in prior["rows"] if r["target"] == target))
        allowed = {"published_deterministic_chromatic_structure", "published_scattering_process"}
        if set(row["exclusion_reasons"]) - allowed:
            raise ValueError(f"Target has unrelated exclusions: {target}")
        r = table[target]
        if r[1]:
            event = {"kind": "gaussian", "index": batch.noise_value(r[2]),
                     "center_mjd": batch.noise_value(r[3]),
                     "width_days": batch.noise_value(r[4])}
        else:
            event = {"kind": "annual", "index": batch.noise_value(r[7])}
        row.update(selected=True, batch_index=len(rows), chromatic_support={
            "schema": "recherche-chromatic-v1", "event": event,
            "published_table_row": r, "table_sha256": cal.digest(tables_path),
            "source": "https://arxiv.org/html/2412.01148v1#S3.SS7",
        })
        rows.append(row)
    data.mkdir(parents=True, exist_ok=False)
    original = data / "original"
    original.mkdir()
    for name, digest in prior["original_hashes"].items():
        path = previous / "original" / name
        if cal.digest(path) != digest:
            raise ValueError(f"Original input changed: {path}")
        shutil.copy2(path, original / name)
    with tarfile.open(original / "mpta-partim.tar.gz") as archive:
        members = {Path(m.name).name: m for m in archive.getmembers() if m.isfile()}
        for row in rows:
            folder = data / row["target"] / "original"
            folder.mkdir(parents=True)
            for suffix in ("par", "tim"):
                path = folder / (row["target"] + "." + suffix)
                path.write_bytes(archive.extractfile(members[path.name]).read())
                if cal.digest(path) != row[suffix + "_sha256"]:
                    raise ValueError(f"Extracted input changed: {path}")
    cal.write(data / "selection.json", {
        "created_utc": batch.now(), "selected": list(TARGETS), "rows": rows,
        "purpose": "Chromatic support development and conditional calibration; no observed search",
        "policy": {**batch.POLICY, "search_count": 4, "seed": 2026091000},
        "source_selection_sha256": cal.digest(previous / "selection.json"),
        "source_evidence_root": str(source), "original_hashes": prior["original_hashes"],
    })
    for target in TARGETS:
        batch.prepare(data, target)


def diagnose(data):
    output = data / "diagnosis.json"
    if output.exists():
        raise FileExistsError("Completed diagnosis is retained; use its receipt")
    selection = cal.read(data / "selection.json")
    results = []
    for row in selection["rows"]:
        target = row["target"]
        saved = data / target / "diagnosis.json"
        if saved.exists():
            result = cal.read(saved)
            if result["support_sha256"] != cal.digest(chromatic.__file__):
                raise ValueError("Saved diagnosis uses different support code")
            results.append(result)
            continue
        root = data / target
        calibration = cal.run(root / "profile/profile.json", data / "calibration-cache")
        profile, arrays = cal.load_profile(root / "profile/profile.json")
        with np.load(root / "prepared/metadata.npz") as metadata:
            radio, errors, groups = (metadata[k] for k in ("radio", "errors", "epoch_index"))
        with np.load(Path(calibration["path"]) / "projection-and-sensitivity.npz") as grid:
            frequencies, eligible, worst = (
                grid[k] for k in ("frequencies", "eligible", "worst_phase_amplitude_us")
            )
        times = arrays["times"]
        extra = chromatic.event_design(times, radio, row["chromatic_support"]["event"])
        args = (times, frequencies, profile["reference_epoch_mjd_tdb"])
        scanner = prepare_covariance_gls_scanner(arrays["covariance"], arrays["design"], *args)
        # Same threshold and eligible cells isolate the model's sensitivity cost.
        # This deliberately omits real chromatic terms: an optimistic comparison, not a valid null.
        noise = {**row["noise"], "chrom_amplitude": None}
        old_cov = batch.published_covariance(times, errors, groups, noise)
        old = prepare_covariance_gls_scanner(old_cov, arrays["design"][:, :-extra.shape[1]], *args)
        _, old_worst = cal.sensitivity(old, eligible, calibration["threshold"], 0.95)
        ratios = worst[eligible] / old_worst[eligible]
        trials = []
        rng = np.random.default_rng(profile["policy"]["seed"] + 500)
        # Three fixed requested periods, nearest eligible cells, 32 phases/noise draws each.
        for period in (60.0, 150.0, 300.0):
            indices = np.flatnonzero(eligible)
            index = indices[np.argmin(abs(1 / frequencies[indices] - period))]
            phase = 2 * np.pi * (times - profile["reference_epoch_mjd_tdb"]) * frequencies[index]
            orbit = np.column_stack([np.sin(phase), np.cos(phase)])
            amplitude = worst[index] * 1e-6
            phase_coefficients = np.column_stack([
                np.cos(np.arange(32) * 2 * np.pi / 32),
                np.sin(np.arange(32) * 2 * np.pi / 32),
            ]).T * amplitude
            # Include a deterministic event at the published amplitude; fit it, do not subtract it.
            published = row["chromatic_support"]["published_table_row"]
            event_amplitude = 10 ** batch.noise_value(published[1] or published[6])
            event = extra @ np.full(extra.shape[1], event_amplitude)
            noiseless = orbit @ phase_coefficients + event[:, None]
            whitened = scanner.whiten_and_project(noiseless[:, 0])
            rhs = scanner.projected_whitened_templates[:, index, :].T @ whitened
            recovered = scanner.template_gram_pseudoinverse[index] @ rhs
            relative_error = float(np.linalg.norm(recovered - phase_coefficients[:, 0]) / amplitude)
            if relative_error > 1e-5:
                raise ValueError(f"Noiseless orbital recovery failed: {target} {period}")
            noise_draws = scanner.covariance_cholesky @ rng.standard_normal((len(times), 32))
            detections = sum(
                scanner.scan(noiseless[:, i] + noise_draws[:, i])["all_delta_chi2"][index]
                > calibration["threshold"] for i in range(32)
            )
            trials.append({"requested_period_days": period,
                           "grid_period_days": float(1 / frequencies[index]),
                           "amplitude_us": float(amplitude * 1e6),
                           "trials": 32, "detections_at_injected_cell": int(detections),
                           "noiseless_relative_coefficient_error": relative_error})
        result = {
            "target": target, "status": "DEVELOPMENT_COMPLETE", "calibration": calibration,
            "profile_sha256": cal.digest(root / "profile/profile.json"),
            "support_sha256": cal.digest(chromatic.__file__),
            "diagnostic_code_sha256": cal.digest(__file__),
            "conditional_sensitivity_cost_ratio_median": float(np.median(ratios)),
            "conditional_sensitivity_cost_ratio_range": [float(ratios.min()), float(ratios.max())],
            "comparison": "Same cells/threshold; denominator omits published chromatic effects",
            "injections": trials, "observed_search_executed": False,
        }
        cal.write(saved, result)
        results.append(result)
        print(json.dumps(result), flush=True)
    cal.write(output, {
        "created_utc": batch.now(), "status": "DEVELOPMENT_COMPLETE", "results": results,
        "observed_search_executed": False, "selection_sha256": cal.digest(data / "selection.json"),
        "limitations": "Fixed MAP shape/index/noise; 96 injections per target are engineering checks, not new qualification or a measured 95% completeness guarantee",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "diagnose"))
    parser.add_argument("--data", type=Path, default=DEFAULT)
    parser.add_argument("--previous-data", type=Path, default=batch.DATA)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.data.resolve(), args.previous_data.resolve())
    else:
        diagnose(args.data.resolve())
