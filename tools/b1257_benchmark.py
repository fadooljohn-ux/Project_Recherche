"""Narrowband B1257+12 recovery benchmark; preserves the qualified source tree."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from contextlib import ExitStack
from pathlib import Path

import numpy as np
from scipy.linalg import lstsq, solve_triangular
from scipy.optimize import least_squares

from pulsar_pilot.pilot1_runtime import (
    build_search_frequency_grid,
    circular_signal_templates,
    prepare_covariance_gls_scanner,
)
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DATA = REPO.parent / "Project Recherche Data/b1257-benchmark-20260908"
DEFAULT_RESOURCES = REPO.parent / "Project Recherche Data/operational-20260908"
SEED = 1257122026
REFERENCE = [
    {"planet": "b", "period_days": 25.262, "amplitude_us": 3.0},
    {"planet": "c", "period_days": 66.5419, "amplitude_us": 1310.6},
    {"planet": "d", "period_days": 98.2114, "amplitude_us": 1413.4},
]


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unwrap_cluster(phase):
    """Choose the shortest phase arc, without using orbital periods or templates."""
    values = np.remainder(np.asarray(phase, dtype=float), 1.0)
    ordered = np.sort(values)
    gaps = np.diff(np.r_[ordered, ordered[0] + 1])
    origin = ordered[(np.argmax(gaps) + 1) % len(ordered)]
    unwrapped = np.remainder(values - origin, 1.0)
    return unwrapped - np.mean(unwrapped), float(1 - gaps.max())


def prepare(data, resources):
    import pint.logging
    from astropy import units as u
    from pint.models import get_model
    from pint.observatory.topo_obs import TopoObs
    from pint.toa import get_TOAs

    output = data / "prepared"
    output.mkdir(exist_ok=False)
    pint.logging.setup(level="INFO", sink=output / "pint.log", removeprior=True)
    original = data / "original"
    par = original / "J1300+1240_final.par"
    tim = original / "J1300+1240_toa.tim"
    # Authoritative upstream station entry, including the alias in the release.
    sites = (original / "tempo2-observatories.dat").read_text().splitlines()
    site = next(
        line.split() for line in sites if len(line.split()) >= 5 and line.split()[3] == "IE613"
    )
    TopoObs(
        "ie613",
        aliases=[site[4]],
        itrf_xyz=list(map(float, site[:3])),
        clock_file="",
        apply_gps2utc=True,
        origin="TEMPO2 observatories.dat",
        overwrite=True,
    )
    remove = {"BINARY", "PB", "T0", "A1", "OM", "ECC", "M2", "NTOA", "CHI2R", "TRES", "EPHVER"}
    kept, removed = [], []
    for line in par.read_text().splitlines():
        key = line.split()[0]
        if key.split("_")[0] in remove:
            removed.append(line)
        else:
            kept.append(line)
    # PINT performs the documented TCB conversion; all timing terms are then
    # nuisance-projected/refitted. No orbit values enter the search model.
    model = get_model(io.StringIO("\n".join(kept)), allow_tcb=True)
    model.CLOCK.value = "TT(BIPM2025)"
    bind_precise_spin_phase(model)
    (output / "no-planets-tdb.par").write_text(model.as_parfile())
    manifest = json.loads((resources / "metadata/resources.json").read_text())
    with ExitStack() as stack:
        deny = stack.enter_context(NetworkDeny())
        local = stack.enter_context(LocalPintRepository(resources, manifest))
        local.bind_science_resources()
        import pint.observatory
        from pint.observatory.clock_file import ClockFile

        pint.observatory._bipm_clock_versions["bipm2025"] = ClockFile.read(
            original / "tai2tt_bipm2025.clk", format="tempo2"
        )
        toas = get_TOAs(
            tim,
            model=model,
            ephem="DE440",
            include_bipm=True,
            bipm_version="BIPM2025",
            planets=True,
            usepickle=False,
            limits="error",
        )
        # Relative phase avoids injecting any published planetary TZR delay.
        phases = model.phase(toas, abs_phase=False).frac.to_value(u.dimensionless_unscaled)
        phase, arc = unwrap_cluster(phases)
        residuals = phase / float(model.F0.value)
        design, names, _units = model.designmatrix(toas)
        achromatic = [i for i, name in enumerate(names) if name not in {"DM", "NE_SW"}]
        design = design[:, achromatic]
        names = [names[i] for i in achromatic]
        times = np.asarray(toas.table["tdbld"], dtype=float)
        errors = toas.get_errors().to_value(u.s)
        freqs = toas.get_freqs().to_value(u.MHz)
        groups, epochs = np.unique([f["name"] for f in toas.table["flags"]], return_inverse=True)
        dm = np.zeros((len(toas), len(groups)))
        dm[np.arange(len(toas)), epochs] = 1.0 / freqs**2
        # Epoch DM replaces global DM/solar wind, avoiding almost duplicate
        # columns created by sub-millisecond inter-channel timestamp differences.
        design = np.column_stack([design, dm])
        scale = np.sqrt(
            max(1.0, float(next(l.split()[1] for l in removed if l.startswith("CHI2R"))))
        )
        covariance = np.diag((errors * scale) ** 2)
        np.savez_compressed(
            output / "context.npz",
            times=times,
            residuals=residuals,
            covariance=covariance,
            design=design,
            epochs=epochs,
            errors=errors,
            radio_frequencies_mhz=freqs,
        )
        if deny.attempts:
            raise RuntimeError(f"Unexpected network attempts: {deny.attempts}")
    receipt = {
        "target": "B1257+12",
        "toas": len(times),
        "epochs": len(groups),
        "span_days": float(np.ptp(times)),
        "mjd_min": float(times.min()),
        "mjd_max": float(times.max()),
        "median_toa_error_us": float(np.median(errors) * 1e6),
        "uncertainty_scale": float(scale),
        "phase_arc_cycles": arc,
        "phase_arc_method": "shortest_contiguous_arc_without_period_information",
        "removed_parameters": removed,
        "timing_design_names": names,
        "epoch_dm_columns": len(groups),
        "site_entry": site,
        "clock_assumption": "IE613 timestamps GPS-referenced; no separate station clock supplied; apply GPS-to-UTC and TT(BIPM2025)",
        "clock_change": "BIPM2019 has no valid coverage for the complete 2022-2024 observations; use published BIPM2025 with strict coverage checks",
        "resource_manifest_sha256": sha(resources / "metadata/resources.json"),
        "inputs": {
            str(p): sha(p)
            for p in [
                par,
                tim,
                original / "tempo2-observatories.dat",
                original / "tai2tt_bipm2025.clk",
            ]
        },
        "context_sha256": sha(output / "context.npz"),
        "network_attempts": 0,
    }
    write(output / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


def project(values, basis):
    return values - basis @ (basis.T @ values)


def eligible_mask(scanner, dispersion_scanner):
    # Annual identifiability is additional loss to timing/astrometry after DM
    # separation. Absolute DM separation costs information at every period and
    # belongs in the calibrated sensitivity, not an all-frequency annual mask.
    white = dispersion_scanner.projected_whitened_templates
    retained = []
    for before, after in zip(
        white.transpose(1, 0, 2),
        scanner.projected_whitened_templates.transpose(1, 0, 2),
        strict=True,
    ):
        from scipy.linalg import eigvalsh

        retained.append(float(np.clip(eigvalsh(after.T @ after, before.T @ before)[0], 0, 1)))
    return np.asarray(retained) > 0.2, np.asarray(retained)


def calibrate(scanner, mask, output, seed):
    rng = np.random.default_rng(seed)
    maxima = []
    for start in range(0, 4096, 128):
        white = rng.standard_normal((scanner.covariance_cholesky.shape[0], 128))
        rhs = np.einsum("nfi,nb->fib", scanner.projected_whitened_templates, white)
        stat = np.einsum("fib,fij,fjb->fb", rhs, scanner.template_gram_pseudoinverse, rhs)
        maxima.extend(np.max(stat[mask], axis=0).tolist())
    empirical = float(np.quantile(maxima, 0.99, method="higher"))
    analytical = float(2 * np.log(3 * len(mask) / 0.01))
    result = {
        "seed": seed,
        "null_count": len(maxima),
        "empirical_99_percentile": empirical,
        "analytical_three_search_bound": analytical,
        "threshold": max(empirical, analytical),
        "noise_model": "Gaussian with fixed supplied scaled TOA covariance; conditional on nuisance design",
    }
    np.save(output / "null-maxima.npy", maxima)
    write(output / "calibration.json", result)
    return result


def circular_columns(times, frequencies, epoch):
    if len(frequencies) == 0:
        return np.empty((len(times), 0))
    return circular_signal_templates(times, frequencies, epoch, len(times)).reshape(len(times), -1)


def kepler_columns(times, parameters, epoch):
    """Independent eccentric Roemer delays; coefficients are x*sin(omega), x*cos(omega)."""
    cols = []
    for frequency, eccentricity, mean_phase in np.asarray(parameters).reshape(-1, 3):
        mean = 2 * np.pi * (times - epoch) * frequency + mean_phase
        eccentric = mean.copy()
        for _ in range(10):
            eccentric -= (eccentric - eccentricity * np.sin(eccentric) - mean) / (
                1 - eccentricity * np.cos(eccentric)
            )
        cols += [np.cos(eccentric) - eccentricity, np.sqrt(1 - eccentricity**2) * np.sin(eccentric)]
    return np.column_stack(cols)


def fit_orbits(scanner, times, values, initial, epoch, grid_step):
    white = scanner.whiten_and_project(values)
    factor, basis = scanner.covariance_cholesky, scanner.timing_projection_basis

    def solve(params):
        columns = kepler_columns(times, params, epoch)
        matrix = project(solve_triangular(factor, columns, lower=True), basis)
        coefficients = lstsq(matrix, white)[0]
        return white - matrix @ coefficients, coefficients, columns

    x0 = np.array([[f, 0.02, 0.0] for f in initial]).ravel()
    # One independent frequency bin, rather than one oversampled cell: the
    # single-signal maximum can shift while a second strong orbit is unmodelled.
    lower = np.array([[f - 5 * grid_step, 0.0, -4 * np.pi] for f in initial]).ravel()
    upper = np.array([[f + 5 * grid_step, 0.3, 4 * np.pi] for f in initial]).ravel()
    fit = least_squares(
        lambda p: solve(p)[0],
        x0,
        bounds=(lower, upper),
        x_scale="jac",
        ftol=1e-10,
        xtol=1e-10,
        gtol=1e-9,
        max_nfev=500,
    )
    residual, coefficients, columns = solve(fit.x)
    if not fit.success or not np.all(np.isfinite(fit.x)):
        raise RuntimeError(f"Joint Kepler fit did not converge: {fit.message}")
    dof = len(values) - scanner.timing_design_rank - 5 * len(initial)
    active = np.flatnonzero(fit.active_mask).tolist()
    if len(initial) > 1 and any(i % 3 == 0 for i in active):
        raise RuntimeError("Joint orbital frequency remains at a fitting boundary")
    norms = np.linalg.norm(fit.jac, axis=0)
    normalized = fit.jac / norms
    param_covariance = np.linalg.pinv(normalized.T @ normalized) / np.outer(norms, norms)
    period_errors = np.sqrt(np.maximum(0, np.diag(param_covariance)[::3])) / fit.x[::3] ** 2
    # Include nonlinear orbital derivatives as nuisance directions in subsequent scans.
    tangent = -factor @ fit.jac
    return (
        {
            "parameters": fit.x.tolist(),
            "periods_days": (1 / fit.x.reshape(-1, 3)[:, 0]).tolist(),
            "conditional_period_errors_days": period_errors.tolist(),
            "eccentricities": fit.x.reshape(-1, 3)[:, 1].tolist(),
            "amplitudes_us": (np.linalg.norm(coefficients.reshape(-1, 2), axis=1) * 1e6).tolist(),
            "chi2": float(residual @ residual),
            "dof": dof,
            "reduced_chi2": float(residual @ residual / dof),
            "optimizer_evaluations": fit.nfev,
            "optimizer_message": fit.message,
            "active_parameter_bounds": active,
        },
        columns @ coefficients,
        np.column_stack([columns, tangent]),
    )


def run(data, refine_existing=False):
    started = time.monotonic()
    output = data / ("refinement01" if refine_existing else "run01")
    output.mkdir(exist_ok=False)
    receipt = json.loads((data / "prepared/receipt.json").read_text())
    if sha(data / "prepared/context.npz") != receipt["context_sha256"]:
        raise RuntimeError("Prepared context changed")
    with np.load(data / "prepared/context.npz") as archive:
        times, y, covariance, design, epochs = [
            archive[k] for k in ("times", "residuals", "covariance", "design", "epochs")
        ]
    epoch = float(np.mean(times))
    frequencies, grid = build_search_frequency_grid(times, 10.0, 400.0, 5)
    scanner = prepare_covariance_gls_scanner(covariance, design, times, frequencies, epoch)
    dispersion_scanner = prepare_covariance_gls_scanner(
        covariance,
        np.column_stack([np.ones(len(y)), design[:, -receipt["epoch_dm_columns"] :]]),
        times,
        frequencies,
        epoch,
    )
    mask, retained = eligible_mask(scanner, dispersion_scanner)
    if not np.any(mask):
        raise RuntimeError("No identifiable frequency remains after timing projection")
    np.savez_compressed(
        output / "projection-map.npz",
        frequencies=frequencies,
        eligible=mask,
        retained_power=retained,
    )
    write(
        output / "manifest.json",
        {
            "grid": grid,
            "reference_epoch_mjd_tdb": epoch,
            "context_sha256": receipt["context_sha256"],
            "code_sha256": sha(__file__),
            "policy_sha256": sha(REPO / "docs/B1257_BENCHMARK_2026-09-08.md"),
            "timing_rank": scanner.timing_design_rank,
            "excluded_cells": int((~mask).sum()),
        },
    )
    if refine_existing:
        prior = data / "run01"
        prior_manifest = json.loads((prior / "manifest.json").read_text())
        if prior_manifest["context_sha256"] != receipt["context_sha256"]:
            raise RuntimeError("Refinement cannot change the observed context")
        with np.load(prior / "projection-map.npz") as saved:
            if not np.array_equal(saved["frequencies"], frequencies) or not np.array_equal(
                saved["eligible"], mask
            ):
                raise RuntimeError("Refinement cannot change the grid or mask")
        calibration = json.loads((prior / "calibration.json").read_text())
        write(output / "calibration.json", calibration)
        write(
            output / "predecessor.json",
            {
                "result_sha256": sha(prior / "result.json"),
                "calibration_sha256": sha(prior / "calibration.json"),
                "reason": "Repair local frequency bound; retain first two observed scans and threshold",
            },
        )
    else:
        calibration = calibrate(scanner, mask, output, SEED)
    threshold = calibration["threshold"]
    print(f"Calibrated {len(frequencies)} frequencies; threshold {threshold:.6f}", flush=True)
    stages, found = [], []
    current, remaining, orbit_design = scanner, y, np.empty((len(y), 0))
    fit_result = None
    if refine_existing:
        previous = json.loads((data / "run01/result.json").read_text())
        stages = previous["scans"][:2]
        if len(stages) != 2 or not all(s["trigger"] for s in stages):
            raise RuntimeError("Refinement requires two selected predecessor signals")
        found = [1 / s["period_days"] for s in stages]
        fit_result, orbit, orbit_design = fit_orbits(
            scanner, times, y, found, epoch, grid["frequency_step_per_day"]
        )
        remaining = y - orbit
        write(output / "orbit-fit-2.json", fit_result)
        current = prepare_covariance_gls_scanner(
            covariance, np.column_stack([design, orbit_design]), times, frequencies, epoch
        )
    for stage in range(2 if refine_existing else 0, 3):
        scan = current.scan(remaining)
        eligible = mask & (current.template_condition_numbers < 1e10)
        statistics = scan["all_delta_chi2"].copy()
        statistics[~eligible] = -np.inf
        peak = int(np.argmax(statistics))
        value = {
            "stage": stage + 1,
            "period_days": float(1 / frequencies[peak]),
            "statistic": float(statistics[peak]),
            "threshold": threshold,
            "trigger": bool(statistics[peak] > threshold),
        }
        np.savez_compressed(
            output / f"scan-{stage + 1}.npz",
            frequencies=frequencies,
            statistics=scan["all_delta_chi2"],
            eligible=eligible,
        )
        stages.append(value)
        print(json.dumps(value), flush=True)
        if not value["trigger"]:
            break
        if stage == 2:
            break  # benchmark reports third candidate without automatic further expansion
        found.append(float(frequencies[peak]))
        fit_result, orbit, orbit_design = fit_orbits(
            scanner, times, y, found, epoch, grid["frequency_step_per_day"]
        )
        found = [1 / p for p in fit_result["periods_days"]]
        remaining = y - orbit
        write(output / f"orbit-fit-{stage + 1}.json", fit_result)
        current = prepare_covariance_gls_scanner(
            covariance, np.column_stack([design, orbit_design]), times, frequencies, epoch
        )
    # Targeted estimate and a bounded sensitivity experiment for the inner planet.
    exact = prepare_covariance_gls_scanner(
        covariance,
        np.column_stack([design, orbit_design]),
        times,
        np.array([1 / REFERENCE[0]["period_days"]]),
        epoch,
    )
    target = exact.scan(remaining)
    coef = target["all_coefficients_seconds"][0]
    coefficient_covariance = exact.template_gram_pseudoinverse[0]
    rng = np.random.default_rng(SEED + 1)
    template = circular_columns(times, [1 / REFERENCE[0]["period_days"]], epoch)
    recoveries, exact_recoveries = 0, 0
    trials = 256
    for i in range(trials):
        angle = rng.uniform(0, 2 * np.pi)
        injected = template @ (3e-6 * np.array([np.cos(angle), np.sin(angle)]))
        simulated = injected + scanner.covariance_cholesky @ rng.standard_normal(len(y))
        result = current.scan(simulated)
        stats = result["all_delta_chi2"].copy()
        stats[~mask] = -np.inf
        peak = int(np.argmax(stats))
        recoveries += bool(
            stats[peak] > threshold and abs(frequencies[peak] - 1 / 25.262) < 1 / np.ptp(times)
        )
        exact_recoveries += bool(exact.scan(simulated)["trigger_statistic"] > threshold)
    target_record = {
        "period_days": 25.262,
        "amplitude_us": float(np.linalg.norm(coef) * 1e6),
        "sine_cosine_coefficients_us": (coef * 1e6).tolist(),
        "coefficient_covariance_us2": (coefficient_covariance * 1e12).tolist(),
        "statistic": target["trigger_statistic"],
        "threshold": threshold,
        "trigger": target["trigger_statistic"] > threshold,
        "interpretation": "Fixed-published-period diagnostic; not an independent discovery",
    }
    sensitivity = {
        "seed": SEED + 1,
        "trials": trials,
        "injected_amplitude_us": 3.0,
        "injected_period_days": 25.262,
        "global_grid_recoveries": recoveries,
        "fixed_period_recoveries": exact_recoveries,
        "conditional_on": "fitted large-orbit nuisance design and supplied scaled Gaussian errors",
    }
    result = {
        "status": "complete",
        "scope": "known-system benchmark",
        "scans": stages,
        "joint_orbit_fit": fit_result,
        "inner_planet": target_record,
        "inner_sensitivity": sensitivity,
        "elapsed_seconds": time.monotonic() - started,
        "reference": REFERENCE,
    }
    write(output / "result.json", result)
    np.savez_compressed(
        output / "postfit.npz",
        times=times,
        remaining=remaining,
        projected_whitened=current.whiten_and_project(remaining),
        epochs=epochs,
    )
    print(json.dumps(result, indent=2), flush=True)


def assess(data):
    """Fixed-size two-planet injection recovery, with no observed residual input."""
    output = data / "sensitivity01"
    output.mkdir(exist_ok=False)
    with np.load(data / "prepared/context.npz") as archive:
        times, covariance, design = [archive[k] for k in ("times", "covariance", "design")]
    with np.load(data / "refinement01/projection-map.npz") as saved:
        frequencies, mask = saved["frequencies"], saved["eligible"]
    calibration = json.loads((data / "run01/calibration.json").read_text())
    epoch, step = float(np.mean(times)), 1 / (5 * np.ptp(times))
    scanner = prepare_covariance_gls_scanner(covariance, design, times, frequencies, epoch)
    rng = np.random.default_rng(SEED + 2)
    records = []
    for trial in range(32):
        parameters = np.array(
            [
                [1 / 66.5419, 0.0186, rng.uniform(-np.pi, np.pi)],
                [1 / 98.2114, 0.0252, rng.uniform(-np.pi, np.pi)],
            ]
        )
        angles = rng.uniform(0, 2 * np.pi, 2)
        coefficients = np.array(
            [
                [amplitude * np.sin(angle), amplitude * np.cos(angle)]
                for amplitude, angle in zip([0.0013106, 0.0014134], angles, strict=True)
            ]
        ).ravel()
        y = kepler_columns(times, parameters, epoch) @ coefficients
        angle = rng.uniform(0, 2 * np.pi)
        y += circular_columns(times, [1 / 25.262], epoch) @ (
            3e-6 * np.array([np.sin(angle), np.cos(angle)])
        )
        y += scanner.covariance_cholesky @ rng.standard_normal(len(times))
        current, remaining, found = scanner, y, []
        record = {"trial": trial, "recovered_both": False}
        try:
            for _ in range(2):
                stats = current.scan(remaining)["all_delta_chi2"].copy()
                stats[~mask] = -np.inf
                peak = int(np.argmax(stats))
                if stats[peak] <= calibration["threshold"]:
                    break
                found.append(float(frequencies[peak]))
                fit, orbit, tangent = fit_orbits(scanner, times, y, found, epoch, step)
                found = [1 / p for p in fit["periods_days"]]
                remaining = y - orbit
                current = prepare_covariance_gls_scanner(
                    covariance, np.column_stack([design, tangent]), times, frequencies, epoch
                )
            record["recovered_periods_days"] = sorted(1 / f for f in found)
            record["recovered_both"] = len(found) == 2 and all(
                abs(f - r) < 1 / np.ptp(times)
                for f, r in zip(sorted(found), sorted(parameters[:, 0]), strict=True)
            )
        except RuntimeError as error:
            record["fit_error"] = str(error)
        records.append(record)
    write(
        output / "result.json",
        {
            "seed": SEED + 2,
            "trials": len(records),
            "recovered_both": sum(r["recovered_both"] for r in records),
            "records": records,
            "observed_residuals_used": False,
            "threshold": calibration["threshold"],
            "code_sha256": sha(__file__),
            "context_sha256": sha(data / "prepared/context.npz"),
        },
    )
    print(
        f"Recovered both large planets in {sum(r['recovered_both'] for r in records)}/{len(records)} injections",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "refine-existing", "assess"])
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--resources", type=Path, default=DEFAULT_RESOURCES)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.data, args.resources)
    elif args.command == "assess":
        assess(args.data)
    else:
        run(args.data, refine_existing=args.command == "refine-existing")


if __name__ == "__main__":
    main()
