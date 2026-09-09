"""Bounded MPTA original searches with published fixed noise and recorded selection."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import tarfile
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

import chromatic_timing as chromatic
import numpy as np
import target_calibration as cal
from b1257_benchmark import unwrap_cluster
from scipy.linalg import solve_triangular
from scipy.stats import chi2

from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

REPO = Path(__file__).resolve().parents[1]
DATA = REPO.parent / "Project Recherche Data/mpta-batch01-20260908"
PREVIOUS = REPO.parent / "Project Recherche Data/five-companion-benchmark-20260908"
RESOURCES = REPO.parent / "Project Recherche Data/operational-20260908"
NOISE_NAMES = (
    "efac",
    "log10_equad",
    "log10_ecorr",
    "red_amplitude",
    "red_gamma",
    "dm_amplitude",
    "dm_gamma",
    "chrom_amplitude",
    "chrom_gamma",
    "chrom_index",
    "sw_amplitude",
    "sw_gamma",
    "common_amplitude",
    "solar_density",
)
ALIASES = {"B1855+09": "J1857+0943", "B1937+21": "J1939+2134", "B1953+29": "J1955+2908"}
POLICY = {
    **cal.DEFAULT_POLICY,
    "minimum_period_days": 30.0,
    "maximum_period_days": 400.0,
    "search_count": 10,
    "seed": 2026090800,
}


def now():
    return datetime.now(UTC).isoformat()


def noise_value(text):
    if text == "-":
        return None
    return float(re.match(r"\{?([+-]?[0-9.]+)", text).group(1))


def white_covariance(errors, groups, noise):
    variance = (noise["efac"] * errors) ** 2
    if noise["log10_equad"] is not None:
        variance += 10.0 ** (2 * noise["log10_equad"])
    covariance = np.diag(variance)
    if noise["log10_ecorr"] is not None:
        covariance += (groups[:, None] == groups[None, :]) * 10.0 ** (2 * noise["log10_ecorr"])
    return covariance


def red_covariance(times, amplitude, gamma, modes=120):
    """Equation 6, Miles et al.; seconds squared, 120 sine/cosine harmonic pairs."""
    seconds = (np.asarray(times) - np.min(times)) * 86400.0
    span = np.ptp(seconds)
    frequency = np.arange(1, modes + 1) / span
    year = 365.25 * 86400.0
    power = (
        10.0 ** (2 * amplitude) / (12 * np.pi**2) * (frequency * year) ** (-gamma) * year**3 / span
    )
    phase = 2 * np.pi * seconds[:, None] * frequency
    sine, cosine = np.sin(phase), np.cos(phase)
    return (sine * power) @ sine.T + (cosine * power) @ cosine.T


def published_covariance(times, errors, groups, noise, *, radio=None):
    if noise["chrom_amplitude"] is not None and radio is None:
        raise ValueError("This bounded adapter does not admit extra chromatic scattering")
    covariance = white_covariance(errors, groups, noise)
    if noise["red_amplitude"] is not None:
        covariance += red_covariance(times, noise["red_amplitude"], noise["red_gamma"])
    covariance += red_covariance(times, noise["common_amplitude"], 13 / 3)
    if noise["chrom_amplitude"] is not None:
        covariance += chromatic.scattering_covariance(
            red_covariance(times, noise["chrom_amplitude"], noise["chrom_gamma"]),
            radio, noise["chrom_index"],
        )
    return covariance


def inventory(data):
    destination = data / "selection.json"
    if destination.exists():
        raise FileExistsError("Selection already exists")
    research = data / "research"
    tables = cal.read(research / "mpta-tables.json")
    noises = {
        r[0]: dict(zip(NOISE_NAMES, map(noise_value, r[1:])))
        for r in tables
        if len(r) == 15 and r[0].startswith("J")
    }
    events = {r[0] for r in tables if len(r) == 9 and r[0].startswith("J")}
    ng = {
        ALIASES.get(r[0], r[0])
        for r in cal.read(research / "nanograv-tables.json")
        if r and re.match("[JB][0-9]", r[0])
    }
    epta = set(re.findall(r"J\d{4}[+\-]\d{4}", (research / "epta-sample.html").read_text()))
    jbo_members = cal.read(research / "jbo-archive-inventory.json")
    jbo = {ALIASES.get(p.split("/")[1], p.split("/")[1]) for p in jbo_members if "/" in p}
    assert len(noises) == 83 and len(ng) == 45 and len(epta) == 25
    original = data / "original"
    original.mkdir(exist_ok=False)
    for name in ("mpta-partim.tar.gz", "mk2utc_observatory.clk", "tai2tt_bipm2020.clk"):
        shutil.copy2(PREVIOUS / "original" / name, original / name)
    assert (
        cal.digest(original / "mpta-partim.tar.gz")
        == "172eb9472f4788f22bfe3b24faad2dc0169fca680b80340e4c829201fdafc393"
    )
    rows = []
    with tarfile.open(original / "mpta-partim.tar.gz") as archive:
        members = {Path(m.name).name: m for m in archive.getmembers() if m.isfile()}
        for name in sorted(noises):
            par = archive.extractfile(members[name + ".par"]).read()
            tim = archive.extractfile(members[name + ".tim"]).read()
            fields = {s.split()[0]: s.split()[1:] for s in par.decode().splitlines() if s.split()}
            observations = []
            for line in tim.decode().splitlines():
                v = line.split()
                if len(v) < 5 or v[0] in ("FORMAT", "MODE", "C", "#"):
                    continue
                try:
                    observations.append((v[0], float(v[1]), float(v[2]), float(v[3])))
                except ValueError:
                    raise ValueError(f"Unexpected TIM line for {name}: {line[:80]}") from None
            epochs = sorted({r[0] for r in observations})
            span = max(r[2] for r in observations) - min(r[2] for r in observations)
            noise = noises[name]
            # Precision proxy fits an intercept and dispersion independently in each epoch.
            epoch_precision = []
            for epoch in epochs:
                sample = [r for r in observations if r[0] == epoch]
                frequencies = np.array([r[1] for r in sample])
                errors = np.array([r[3] for r in sample]) * 1e-6
                matrix = np.column_stack([np.ones(len(sample)), (1400.0 / frequencies) ** 2])
                c = white_covariance(errors, np.zeros(len(sample), dtype=int), noise)
                if np.linalg.matrix_rank(matrix) == 2:
                    epoch_precision.append(
                        np.sqrt(np.linalg.inv(matrix.T @ np.linalg.solve(c, matrix))[0, 0]) * 1e6
                    )
            prior = {"JBO800": name in jbo, "NANOGrav11": name in ng, "EPTA_DR2": name in epta}
            reasons = []
            if "BINARY" in fields:
                reasons.append("supplied_binary_model")
            if name == "J1024-0719":
                reasons.append("known_wide_stellar_companion")
            if name in events:
                reasons.append("published_deterministic_chromatic_structure")
            if noise["chrom_amplitude"] is not None:
                reasons.append("published_scattering_process")
            if span < 1200 or len(epochs) < 40 or len(epoch_precision) < 40:
                reasons.append("insufficient_usable_span_or_epochs")
            proxy = (
                float(np.median(epoch_precision) / np.sqrt(len(epoch_precision)))
                if epoch_precision
                else None
            )
            rank = [sum(prior.values()), int(noise["red_amplitude"] is not None), proxy, name]
            row = {
                "target": name,
                "toas": len(observations),
                "epochs": len(epochs),
                "span_days": span,
                "precision_proxy_us": proxy,
                "prior_search_membership": prior,
                "noise": noise,
                "exclusion_reasons": reasons,
                "rank_key": rank,
                "selected": False,
                "par_sha256": hashlib.sha256(par).hexdigest(),
                "tim_sha256": hashlib.sha256(tim).hexdigest(),
            }
            rows.append(row)
        ranked = sorted(
            (r for r in rows if not r["exclusion_reasons"]), key=lambda r: r["rank_key"]
        )
        selected = ranked[:10]
        for i, row in enumerate(selected):
            row["selected"] = True
            row["batch_index"] = i
            folder = data / row["target"] / "original"
            folder.mkdir(parents=True, exist_ok=False)
            for suffix in (".par", ".tim"):
                (folder / (row["target"] + suffix)).write_bytes(
                    archive.extractfile(members[row["target"] + suffix]).read()
                )
    selection = {
        "created_utc": now(),
        "selected": [r["target"] for r in selected],
        "rows": rows,
        "policy": POLICY,
        "eligible_targets": len(ranked),
        "observed_periodograms_inspected": False,
        "prior_membership_scope": "Named samples only; aliases explicit; absence is not exhaustive novelty",
        "source_hashes": {
            str(p.relative_to(data)): cal.digest(p)
            for p in research.iterdir()
            if p.is_file() and p.suffix in (".html", ".json", ".pdf")
        },
        "original_hashes": {p.name: cal.digest(p) for p in original.iterdir()},
    }
    cal.write(destination, selection)
    print(json.dumps({"selected": selection["selected"], "eligible": len(ranked)}), flush=True)


def inventory_next(data, previous):
    """Reuse the saved input inventory and exclude all previously selected targets."""
    prior = cal.read(previous / "selection.json")
    consumed = set(prior.get("previously_selected", [])) | set(prior["selected"])
    rows = prior["rows"]
    ranked = sorted(
        (r for r in rows if r["target"] not in consumed and not r["exclusion_reasons"]),
        key=lambda r: r["rank_key"],
    )
    selected = ranked[:10]
    if not selected:
        raise ValueError("No remaining targets meet the recorded batch model and coverage rules")
    data.mkdir(parents=True, exist_ok=False)
    original = data / "original"
    original.mkdir()
    for name, expected in prior["original_hashes"].items():
        source = previous / "original" / name
        if cal.digest(source) != expected:
            raise ValueError(f"Previous input digest changed: {name}")
        shutil.copy2(source, original / name)
    for row in rows:
        row["selected"] = False
        row.pop("batch_index", None)
    with tarfile.open(original / "mpta-partim.tar.gz") as archive:
        members = {Path(m.name).name: m for m in archive.getmembers() if m.isfile()}
        for index, row in enumerate(selected):
            row.update(selected=True, batch_index=index)
            folder = data / row["target"] / "original"
            folder.mkdir(parents=True)
            for suffix, key in ((".par", "par_sha256"), (".tim", "tim_sha256")):
                payload = archive.extractfile(members[row["target"] + suffix]).read()
                if hashlib.sha256(payload).hexdigest() != row[key]:
                    raise ValueError(f"Inventory input digest changed: {row['target']}{suffix}")
                (folder / (row["target"] + suffix)).write_bytes(payload)
    cal.write(data / "selection.json", {
        "created_utc": now(),
        "selected": [r["target"] for r in selected],
        "rows": rows,
        "policy": {**prior["policy"], "search_count": len(selected),
                   "seed": prior["policy"]["seed"] + 100},
        "eligible_targets": len(ranked),
        "previously_selected": sorted(consumed),
        "previous_selection": str(previous / "selection.json"),
        "previous_selection_sha256": cal.digest(previous / "selection.json"),
        "original_hashes": prior["original_hashes"],
        "source_hashes": prior["source_hashes"],
        "source_evidence_root": prior.get("source_evidence_root", str(previous)),
        "observed_periodograms_inspected": False,
        "prior_membership_scope": prior["prior_membership_scope"],
    })
    print(json.dumps({"selected": [r["target"] for r in selected],
                      "previously_selected": sorted(consumed)}), flush=True)


def prepare(data, target):
    import pint.logging
    import pint.observatory
    from astropy import units as u
    from pint.models import get_model
    from pint.observatory.clock_file import ClockFile
    from pint.toa import get_TOAs

    selection = cal.read(data / "selection.json")
    row = next(r for r in selection["rows"] if r["target"] == target and r["selected"])
    support = row.get("chromatic_support")
    if "published_deterministic_chromatic_structure" in row["exclusion_reasons"] and not support:
        raise ValueError("Published chromatic event requires an explicit support profile")
    root = data / target
    output = root / "prepared"
    output.mkdir(exist_ok=False)
    pint.logging.setup(level="INFO", sink=output / "pint.log", removeprior=True)
    par, tim = [root / "original" / (target + suffix) for suffix in (".par", ".tim")]
    assert cal.digest(par) == row["par_sha256"] and cal.digest(tim) == row["tim_sha256"]
    text = "\n".join(
        line
        for line in par.read_text().splitlines()
        if line.split() and line.split()[0] not in {"EPHVER", "NTOA", "CHI2R", "TRES"}
    )
    model = get_model(io.StringIO(text), allow_tcb=True)
    if any(c.category == "pulsar_system" for c in model.components.values()):
        raise ValueError("Selected model unexpectedly contains an orbit")
    bind_precise_spin_phase(model)
    resource_manifest = cal.read(RESOURCES / "metadata/resources.json")
    with ExitStack() as stack:
        deny = stack.enter_context(NetworkDeny())
        local = stack.enter_context(LocalPintRepository(RESOURCES, resource_manifest))
        local.bind_science_resources()
        pint.observatory._bipm_clock_versions["bipm2020"] = ClockFile.read(
            data / "original/tai2tt_bipm2020.clk", format="tempo2"
        )
        pint.observatory.Observatory.get("meerkat")._clock = [
            ClockFile.read(data / "original/mk2utc_observatory.clk", format="tempo2")
        ]
        toas = get_TOAs(
            tim,
            model=model,
            ephem="DE440",
            planets=True,
            usepickle=False,
            limits="error",
            include_bipm=True,
            bipm_version="BIPM2020",
        )
        phase = model.phase(toas, abs_phase=False)
        relative, arc = unwrap_cluster(phase.frac.to_value(u.dimensionless_unscaled))
        if arc >= 0.5:
            raise ValueError(f"Ambiguous pulse connection: arc={arc}")
        residuals = np.asarray(relative / model.F0.value, dtype=float)
        times = np.asarray(model.get_barycentric_toas(toas).to_value(u.day), dtype=float)
        radio = toas.get_freqs().to_value(u.MHz)
        groups, index = np.unique([f["name"] for f in toas.table["flags"]], return_inverse=True)
        dm = np.zeros((len(times), len(groups)))
        dm[np.arange(len(times)), index] = (1400.0 / radio) ** 2
        design, names, _ = model.designmatrix(toas)
        keep = [i for i, n in enumerate(names) if not n.startswith("DM") and n != "NE_SW"]
        names = [names[i] for i in keep]
        design = design[:, keep]
        base = [i for i, n in enumerate(names) if n == "Offset" or n.startswith(("JUMP", "FD"))]
        baseline = np.column_stack([design[:, base], dm])
        design = np.column_stack([design, dm])
        if support:
            extra = chromatic.event_design(times, radio, support["event"])
            baseline = np.column_stack([baseline, extra])
            design = np.column_stack([design, extra])
        errors = toas.get_errors().to_value(u.s)
        covariance = published_covariance(
            times, errors, index, row["noise"], radio=radio if support else None
        )
        if deny.attempts:
            raise RuntimeError("Unexpected scientific network access")
        (output / "timing-model.par").write_text(model.as_parfile())
    np.savez_compressed(output / "observed.npz", residuals=residuals)
    # Diagnostic metadata permits checks without reopening or changing source observations.
    np.savez_compressed(output / "metadata.npz", radio=radio, epoch_index=index, errors=errors)
    receipt = {
        "target": target,
        "toas": len(times),
        "epochs": len(groups),
        "span_days": float(np.ptp(times)),
        "phase_arc_cycles": arc,
        "timing_names": names,
        "epoch_dm_columns": len(groups),
        "observed_sha256": cal.digest(output / "observed.npz"),
        "noise": row["noise"],
        "noise_terms": "Published EFAC/EQUAD/ECORR; 120-mode intrinsic red plus fixed-13/3 red at Table 1 MAP",
        "dispersion_handling": "Independent epoch DM nuisance replaces DM and solar-wind models; no posterior noise waveform subtracted",
        "time_basis": "PINT barycentric TDB before binary; approximate TCB-to-TDB model conversion",
        "network_attempts": 0,
        "selection_sha256": cal.digest(data / "selection.json"),
        "resource_manifest_sha256": cal.digest(RESOURCES / "metadata/resources.json"),
        "code_sha256": cal.digest(__file__),
    }
    if support:
        receipt["chromatic_support"] = {
            **support,
            "module_sha256": cal.digest(chromatic.__file__),
            "nuisance_columns": extra.shape[1],
            "shape_time_basis": "Barycentric TDB MJD; published event epochs approximate",
            "fit": "Gaussian amplitude or annual sine/cosine coefficients; fixed shape/index",
            "limitations": "Conditional MAP shape/noise; no hyperparameter uncertainty propagation",
        }
        receipt["noise_terms"] += "; optional 120-mode Table 1 scattering covariance"
    profile = cal.create_profile(
        root / "profile",
        target,
        {"times": times, "covariance": covariance, "design": design, "baseline_design": baseline},
        {
            "timing_model": "Published no-orbit model; epoch dispersion nuisance",
            "noise_model": receipt["noise_terms"],
            "preparation": receipt,
        },
        {**selection["policy"], "seed": selection["policy"]["seed"] + row["batch_index"]},
        reference_epoch=float(model.PEPOCH.value),
    )
    cal.write(output / "receipt.json", receipt)
    print(
        json.dumps(
            {"status": "PREPARED", "target": target, "toas": len(times), "profile": str(profile)}
        ),
        flush=True,
    )


def freeze(data):
    output = data / "execution-freeze.json"
    if output.exists():
        raise FileExistsError("Execution freeze already exists")
    selection = cal.read(data / "selection.json")
    targets = {}
    for target in selection["selected"]:
        root = data / target
        result = cal.run(root / "profile/profile.json", cache=data / "calibration-cache")
        targets[target] = {
            "profile_sha256": cal.digest(root / "profile/profile.json"),
            "observed_sha256": cal.digest(root / "prepared/observed.npz"),
            "calibration": result,
        }
    record = {
        "created_utc": now(),
        "selection_sha256": cal.digest(data / "selection.json"),
        "code_sha256": cal.digest(__file__),
        "implementation": cal.implementation(),
        "targets": targets,
        "search": "One 30-400 day circular grid per selected target; fixed noise; no period seeds",
        "batch_alpha_conditional": selection["policy"]["false_alarm_probability"],
        "max_targets": selection["policy"]["search_count"],
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip(),
    }
    if any(r.get("chromatic_support") for r in selection["rows"] if r["selected"]):
        record["chromatic_module_sha256"] = cal.digest(chromatic.__file__)
    cal.write(output, record)
    print("FROZEN " + cal.digest(output), flush=True)


def circular_template(times, reference_epoch, frequency, data_dimension):
    """Achromatic delay in TOA rows; auxiliary DM measurements receive zero signal."""
    if data_dimension < len(times):
        raise ValueError("Residual vector has fewer rows than TOAs")
    phase = 2 * np.pi * (times - reference_epoch) * frequency
    template = np.zeros((data_dimension, 2))
    template[:len(times)] = np.column_stack([np.sin(phase), np.cos(phase)])
    return template


def run(data, target):
    frozen = cal.read(data / "execution-freeze.json")
    assert frozen["code_sha256"] == cal.digest(__file__)
    assert frozen["implementation"] == cal.implementation()
    if "chromatic_module_sha256" in frozen:
        assert frozen["chromatic_module_sha256"] == cal.digest(chromatic.__file__)
    assert frozen["selection_sha256"] == cal.digest(data / "selection.json")
    binding = frozen["targets"][target]
    root = data / target
    profile_path = root / "profile/profile.json"
    observed = root / "prepared/observed.npz"
    assert cal.digest(profile_path) == binding["profile_sha256"]
    assert cal.digest(observed) == binding["observed_sha256"]
    profile, arrays = cal.load_profile(profile_path)
    calibration = binding["calibration"]
    cache = Path(calibration["path"])
    cal.verify_cache(cache, {"profile": profile, "implementation": cal.implementation()})
    output = root / "run01"
    output.mkdir(exist_ok=False)
    with np.load(cache / "projection-and-sensitivity.npz") as f:
        frequencies, eligible, best, worst = (
            f[k]
            for k in (
                "frequencies",
                "eligible",
                "best_phase_amplitude_us",
                "worst_phase_amplitude_us",
            )
        )
    with np.load(observed) as f:
        residuals = f["residuals"]
    scanner = prepare_covariance_gls_scanner(
        arrays["covariance"],
        arrays["design"],
        arrays["times"],
        frequencies,
        profile["reference_epoch_mjd_tdb"],
    )
    scan = scanner.scan(residuals)
    statistics = scan["all_delta_chi2"]
    # Preserve the one observed grid even if subsequent numerical verification fails.
    np.savez_compressed(
        output / "periodogram.npz",
        frequencies=frequencies,
        statistic=statistics,
        eligible=eligible,
        best_phase_amplitude_us=best,
        worst_phase_amplitude_us=worst,
    )
    peak = int(np.argmax(np.where(eligible, statistics, -np.inf)))
    statistic = float(statistics[peak])
    template = circular_template(arrays["times"], profile["reference_epoch_mjd_tdb"],
                                 frequencies[peak], len(residuals))
    whitened = solve_triangular(scanner.covariance_cholesky, template, lower=True)
    q = scanner.timing_projection_basis
    whitened -= q @ (q.T @ whitened)
    projected = scanner.whiten_and_project(residuals)
    coefficient = np.linalg.lstsq(whitened, projected, rcond=None)[0]
    null_chi2 = float(projected @ projected)
    remaining = projected - whitened @ coefficient
    post_chi2 = float(remaining @ remaining)
    dof = len(residuals) - scanner.timing_design_rank
    # Single frequency likelihood audit, independent full-design QR/SVD fit.
    full = np.column_stack([arrays["design"], template])
    full = solve_triangular(scanner.covariance_cholesky, full, lower=True)
    scale = np.linalg.norm(full, axis=0)
    y = solve_triangular(scanner.covariance_cholesky, residuals, lower=True)
    independent, _, rank, _ = np.linalg.lstsq(full / scale, y, rcond=1e-12)
    error = y - (full / scale) @ independent
    independent_chi2 = float(error @ error)
    if not np.isclose(independent_chi2, post_chi2, rtol=1e-7, atol=1e-5):
        raise ValueError("Independent full-design likelihood verification disagrees")
    if not np.isclose(null_chi2 - post_chi2, statistic, rtol=1e-7, atol=1e-5):
        raise ValueError("Saved peak statistic disagrees with likelihood improvement")
    trigger = statistic > calibration["threshold"]
    noise_flag = null_chi2 / dof >= 2
    result = {
        "target": target,
        "completed_utc": now(),
        "status": "CANDIDATE" if trigger else "NO_TRIGGER",
        "candidate": bool(trigger),
        "new_discovery": False,
        "peak_period_days": float(1 / frequencies[peak]),
        "peak_statistic": statistic,
        "threshold": calibration["threshold"],
        "peak_amplitude_us": float(np.linalg.norm(coefficient) * 1e6),
        "null_chi2": null_chi2,
        "null_dof": dof,
        "null_reduced_chi2": null_chi2 / dof,
        "null_chi2_upper_tail": float(chi2.sf(null_chi2, dof)),
        "noise_adequacy_flag": bool(noise_flag),
        "post_peak_chi2": post_chi2,
        "post_peak_dof": dof - 2,
        "independent_full_design_chi2": independent_chi2,
        "independent_full_design_rank": int(rank),
        "grid_cells": len(frequencies),
        "eligible_cells": int(eligible.sum()),
        "sensitivity_median_worst_phase_us": float(np.nanmedian(worst)),
        "sensitivity_range_worst_phase_us": [float(np.nanmin(worst)), float(np.nanmax(worst))],
        "sensitivity_definition": "95% detection probability; circular on-grid signal; fixed published noise; not a posterior upper limit",
        "threshold_scope": (
            "Conditional Gaussian fixed covariance/design; "
            f"{frozen['batch_alpha_conditional']:.1%} union-bound allowance for "
            f"at most {frozen['max_targets']} fixed grids"
        ),
        "calibration_key": calibration["cache_key"],
        "observed_sha256": binding["observed_sha256"],
        "execution_freeze_sha256": cal.digest(data / "execution-freeze.json"),
        "code_sha256": cal.digest(__file__),
    }
    result["periodogram_sha256"] = cal.digest(output / "periodogram.npz")
    cal.write(output / "result.json", result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "prepare", "freeze", "run"))
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--target")
    parser.add_argument("--previous-data", type=Path,
                        help="For inventory: reuse this batch's inventory and exclude its targets")
    args = parser.parse_args()
    if args.previous_data is not None:
        if args.command != "inventory":
            parser.error("--previous-data is only valid for inventory")
        inventory_next(args.data.resolve(), args.previous_data.resolve())
    elif args.command in ("prepare", "run"):
        if not args.target:
            parser.error("--target is required")
        globals()[args.command](args.data.resolve(), args.target)
    else:
        globals()[args.command](args.data.resolve())


if __name__ == "__main__":
    main()
