"""Known-companion recovery from public narrowband TOAs; no discovery claim."""

from __future__ import annotations

import argparse
import copy
import io
import json
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import target_calibration as calibration
from b1257_benchmark import unwrap_cluster
from scipy.optimize import minimize_scalar

from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

REPO = Path(__file__).resolve().parents[1]
DATA = REPO.parent / "Project Recherche Data/five-companion-benchmark-20260908"
RESOURCES = REPO.parent / "Project Recherche Data/operational-20260908"
TARGETS = ("J1719-1438", "J2322-2650", "J1544+4937")


def prepare(target, data=DATA, resources=RESOURCES):
    import pint.logging
    import pint.observatory
    from astropy import units as u
    from pint.models import get_model
    from pint.observatory.clock_file import ClockFile
    from pint.toa import get_TOAs

    root = data / target
    output = root / "prepared"
    output.mkdir(exist_ok=False)
    pint.logging.setup(level="INFO", sink=output / "pint.log", removeprior=True)
    original = root / "original"
    par = next(original.glob("*.par"))
    tim = (
        original / "J1544+4937_LOFAR_6chan_outliers_rejected.tim"
        if target == "J1544+4937"
        else original / f"{target}.tim"
    )
    # Drop reporting-only fields, preserving actual timing, instrument and orbit terms.
    lines = par.read_text().splitlines()
    content = "\n".join(
        line
        for line in lines
        if line.split() and line.split()[0] not in {"EPHVER", "NTOA", "CHI2R", "TRES"}
    )
    model = get_model(io.StringIO(content), allow_tcb=True)
    bind_precise_spin_phase(model)
    model.EPHEM.value = "DE440"
    for name in ("F0", "F1", "RAJ", "DECJ"):
        if name in model.params:
            getattr(model, name).frozen = False
    reference = {"period_days": float(model.PB.value), "amplitude_us": float(model.A1.value) * 1e6}
    epoch = float(model.PEPOCH.value)
    manifest = calibration.read(resources / "metadata/resources.json")
    with ExitStack() as stack:
        deny = stack.enter_context(NetworkDeny())
        local = stack.enter_context(LocalPintRepository(resources, manifest))
        local.bind_science_resources()
        if target != "J1544+4937":
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
            include_bipm=target != "J1544+4937",
            bipm_version="BIPM2020",
        )
        original_toa_count = len(toas)
        quality_cut = None
        if target == "J1544+4937":
            # Weak LOFAR channels can have uncertainty comparable to a whole rotation.
            # Select by measurement uncertainty alone, before examining orbital residuals.
            quality_cut = 0.05 / float(model.F0.value)
            toas = toas[toas.get_errors().to_value(u.s) <= quality_cut]
            if len(toas) < 3:
                raise ValueError("Insufficient precise TOAs to establish pulse numbering")
        # Published orbital parameters establish integer pulse numbering only.
        # No binary model is present in the subsequently searched timing model.
        full_phase = model.phase(toas, abs_phase=False)
        relative, arc = unwrap_cluster(full_phase.frac.to_value(u.dimensionless_unscaled))
        if arc >= 0.5:
            np.savez_compressed(
                output / "phase-diagnosis.npz",
                times=np.asarray(toas.table["tdbld"], dtype=float),
                phase=full_phase.frac.to_value(u.dimensionless_unscaled),
                errors=toas.get_errors().to_value(u.s),
                radio=toas.get_freqs().to_value(u.MHz),
                observatories=np.asarray(toas.table["obs"], dtype=str),
                groups=np.asarray([f["name"] for f in toas.table["flags"]], dtype=str),
            )
            raise ValueError(
                f"Published model does not establish unambiguous pulse numbering: arc={arc}"
            )
        # Hour-scale orbital templates require barycentric, dispersion-corrected times.
        times = np.asarray(model.get_barycentric_toas(toas).to_value(u.day), dtype=float)
        null_model = copy.deepcopy(model)
        removed = [
            name
            for name, component in null_model.components.items()
            if component.category == "pulsar_system"
        ]
        if len(removed) != 1:
            raise ValueError("Expected exactly one known binary component")
        null_model.remove_component(removed[0])
        null_model.remove_param("BINARY")
        phase_difference = null_model.phase(toas, abs_phase=False) - full_phase
        phase_difference = (phase_difference.int + phase_difference.frac).to_value(
            u.dimensionless_unscaled
        )
        residuals = np.asarray((phase_difference + relative) / model.F0.value, dtype=float)
        design, names, _ = null_model.designmatrix(toas)
        keep = [i for i, name in enumerate(names) if not name.startswith("DM") and name != "NE_SW"]
        design = design[:, keep]
        names = [names[i] for i in keep]
        radio = toas.get_freqs().to_value(u.MHz)
        flags = toas.table["flags"]
        groups, indices = np.unique([f["name"] for f in flags], return_inverse=True)
        dm = np.zeros((len(times), len(groups)))
        dm[np.arange(len(times)), indices] = radio**-2
        design = np.column_stack([design, dm])
        baseline_indices = [
            i for i, name in enumerate(names) if name == "Offset" or name.startswith(("JUMP", "FD"))
        ]
        baseline = np.column_stack([design[:, baseline_indices], dm])
        errors = toas.get_errors().to_value(u.s)
        scale = np.sqrt(max(1.0, float(next(l.split()[1] for l in lines if l.startswith("CHI2R")))))
        covariance = np.diag((errors * scale) ** 2)
        if deny.attempts:
            raise RuntimeError(f"Unexpected network attempts: {deny.attempts}")
        (output / "full-model.par").write_text(model.as_parfile())
        (output / "no-companion.par").write_text(null_model.as_parfile())
    np.savez_compressed(
        output / "observed.npz",
        residuals=residuals,
        published_model_residuals=relative / float(model.F0.value),
    )
    receipt = {
        "target": target,
        "toas": len(times),
        "input_toas": original_toa_count,
        "uncertainty_cut_seconds": quality_cut,
        "excluded_by_uncertainty": original_toa_count - len(times),
        "epochs": len(groups),
        "span_days": float(np.ptp(times)),
        "reference": reference,
        "reference_epoch_mjd_tdb": epoch,
        "timing_names": names,
        "epoch_dm_columns": len(groups),
        "uncertainty_scale": float(scale),
        "phase_arc_cycles": arc,
        "published_model_pulse_connection": True,
        "search_period_window": "published period +/- 1 percent; no exact-period grid insertion",
        "time_basis": "barycentric before binary delay, including dispersion corrections",
        "clock": "TT(TAI)"
        if target == "J1544+4937"
        else "TT(BIPM2020), published MeerKAT observatory clock",
        "ephemeris": "DE440; replaces published DE405 for J1544 only",
        "tcb_conversion": "PINT approximate TCB-to-TDB conversion for MPTA targets; J1544 already TDB",
        "network_attempts": 0,
        "observed_sha256": calibration.digest(output / "observed.npz"),
        "inputs": {
            str(p): calibration.digest(p) for p in [par, tim, resources / "metadata/resources.json"]
        },
        "code_sha256": calibration.digest(__file__),
    }
    if target != "J1544+4937":
        receipt["clock_inputs"] = calibration.read(data / "original/clock-acquisition.json")
    profile = calibration.create_profile(
        root / "profile",
        target,
        {"times": times, "covariance": covariance, "design": design, "baseline_design": baseline},
        {
            "timing_model": "published pulse connection; binary removed; per-epoch dispersion nuisance",
            "noise_model": "fixed independent TOA errors, scaled by max(1,sqrt(published CHI2R))",
            "preparation": receipt,
        },
        {
            "minimum_period_days": reference["period_days"] * 0.99,
            "maximum_period_days": reference["period_days"] * 1.01,
        },
        reference_epoch=epoch,
    )
    calibration.write(output / "receipt.json", receipt)
    print(
        json.dumps(
            {
                "target": target,
                "status": "PREPARED",
                "profile": str(profile),
                "toas": len(times),
                "epochs": len(groups),
                "phase_arc_cycles": arc,
            }
        ),
        flush=True,
    )


def run(target, data=DATA):
    root = data / target
    receipt = calibration.read(root / "prepared/receipt.json")
    observed_path = root / "prepared/observed.npz"
    if calibration.digest(observed_path) != receipt["observed_sha256"]:
        raise ValueError("Observed context changed")
    profile_path = root / "profile/profile.json"
    result = calibration.run(profile_path)
    profile, arrays = calibration.load_profile(profile_path)
    with np.load(observed_path) as archive:
        values = archive["residuals"]
    with np.load(Path(result["path"]) / "projection-and-sensitivity.npz") as archive:
        frequencies, eligible = archive["frequencies"], archive["eligible"]
    output = root / "run01"
    output.mkdir(exist_ok=False)
    make = prepare_covariance_gls_scanner
    times, covariance, design = (arrays[k] for k in ("times", "covariance", "design"))
    epoch = profile["reference_epoch_mjd_tdb"]
    scanner = make(covariance, design, times, frequencies, epoch)
    scan = scanner.scan(values)
    statistic = scan["all_delta_chi2"]
    peak = int(np.argmax(np.where(eligible, statistic, -np.inf)))
    threshold = result["threshold"]
    np.savez_compressed(
        output / "periodogram.npz", frequencies=frequencies, eligible=eligible, statistic=statistic
    )
    projected = scanner.whiten_and_project(values)
    # Reuse the already-whitened nuisance projection for cheap scalar frequency refinement.
    from scipy.linalg import solve_triangular

    def at_frequency(frequency):
        phase = 2 * np.pi * (times - epoch) * frequency
        columns = np.column_stack([np.sin(phase), np.cos(phase)])
        columns = solve_triangular(scanner.covariance_cholesky, columns, lower=True)
        basis = scanner.timing_projection_basis
        columns -= basis @ (basis.T @ columns)
        coef, _, _, _ = np.linalg.lstsq(columns, projected, rcond=None)
        residual = projected - columns @ coef
        return float(residual @ residual), coef, columns

    lo, hi = frequencies[max(0, peak - 1)], frequencies[min(len(frequencies) - 1, peak + 1)]
    fit = minimize_scalar(
        lambda f: at_frequency(f)[0], bounds=(lo, hi), method="bounded", options={"xatol": 1e-13}
    )
    chi2, coef, columns = at_frequency(fit.x)
    step = (frequencies[1] - frequencies[0]) * 1e-3
    # Profile curvature: chi-square = chi-square_min + (delta_f/sigma_f)^2.
    curvature = (at_frequency(fit.x + step)[0] + at_frequency(fit.x - step)[0] - 2 * chi2) / step**2
    frequency_sigma = np.sqrt(2 / curvature) if curvature > 0 else None
    amplitude = float(np.linalg.norm(coef) * 1e6)
    coefficient_covariance = np.linalg.inv(columns.T @ columns)
    amplitude_sigma = float(np.sqrt(coef @ coefficient_covariance @ coef / (coef @ coef)) * 1e6)
    reference = receipt["reference"]
    period = float(1 / fit.x)
    period_sigma = float(frequency_sigma / fit.x**2) if frequency_sigma is not None else None
    frequency_match = abs(fit.x - 1 / reference["period_days"]) < 1 / np.ptp(times)
    amplitude_match = abs(amplitude - reference["amplitude_us"]) < max(
        0.05 * reference["amplitude_us"], 5 * amplitude_sigma
    )
    edge = peak in (0, len(frequencies) - 1) or min(fit.x - lo, hi - fit.x) < 0.001 * (hi - lo)
    trigger = float(statistic[peak]) > threshold
    dof = len(values) - scanner.timing_design_rank - 3
    passed = bool(trigger and fit.success and not edge and frequency_match and amplitude_match)
    record = {
        "target": target,
        "status": "KNOWN_COMPANION_RECOVERED" if passed else "RECOVERY_NOT_ESTABLISHED",
        "observed_data": True,
        "blind_discovery": False,
        "published_model_pulse_connection": True,
        "published_period_window": True,
        "period_days": period,
        "conditional_period_sigma_days": period_sigma,
        "amplitude_us": amplitude,
        "conditional_amplitude_sigma_us": amplitude_sigma,
        "reference": reference,
        "grid_peak_period_days": float(1 / frequencies[peak]),
        "grid_peak_statistic": float(statistic[peak]),
        "threshold": threshold,
        "trigger": trigger,
        "period_match_within_independent_bin": bool(frequency_match),
        "amplitude_match_within_max_five_percent_or_five_sigma": bool(amplitude_match),
        "boundary_solution": bool(edge),
        "optimizer_success": bool(fit.success),
        "postfit_chi2": chi2,
        "postfit_dof": dof,
        "postfit_reduced_chi2": chi2 / dof,
        "fixed_noise_fit_adequate": bool(chi2 / dof < 2),
        "calibration": result,
        "profile_sha256": calibration.digest(profile_path),
        "observed_sha256": receipt["observed_sha256"],
        "code_sha256": calibration.digest(__file__),
        "interpretation": "Known-companion recovery conditional on published pulse numbering and period window; no new discovery or true companion mass measurement",
    }
    calibration.write(output / "result.json", record)
    print(json.dumps(record, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run"])
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--resources", type=Path, default=RESOURCES)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.target, args.data.resolve(), args.resources.resolve())
    else:
        run(args.target, args.data.resolve())


if __name__ == "__main__":
    main()
