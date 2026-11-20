"""MeerKAT (MPTA 4.5-year) known binaries: one search each for an additional circular outer companion.

Combines the MPTA fixed published-noise preparation (tools/mpta_batch.py) with
the binary procedure of tools/binary_wideband.py: every free orbital parameter
of the released model is projected together with the timing, instrumental and
per-observation dispersion columns, after its analytic derivative and local
linearity have been checked against the released uncertainties. A target that
fails a check is held, not searched. Targets are a fixed, owner-approved list.
"""
from __future__ import annotations

import argparse
import io
import json
import tarfile
from contextlib import ExitStack
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky, solve_triangular

import binary_wideband as wideband
import mpta_batch as observed
import orbit_reexpress as reexpress
import shapiro_basis as shapiro
import target_calibration as cal
from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

ARCHIVE_SHA256 = "172eb9472f4788f22bfe3b24faad2dc0169fca680b80340e4c829201fdafc393"
POLICY = {**cal.DEFAULT_POLICY, "minimum_period_days": 30.0, "maximum_period_days": 400.0, "seed": 2026111900}
SMALL_STEP = {"SINI", "STIG"}     # curved near edge-on: differentiate with a sub-sigma step
COMPATIBLE = "BINARY_TIMING_NOISE_COMPATIBLE"


def par_fields(text):
    return {v[0]: v[1:] for line in text.splitlines() if (v := line.split())}


def inner_period_days(fields):
    if "PB" in fields:
        return float(fields["PB"][0].replace("D", "e"))
    return 1 / float(fields["FB0"][0].replace("D", "e")) / 86400


def select(data, source, targets, instruction, reexpressed=False, shapiro_basis=False):
    chosen = lambda option, target: option is True or (option and target in option)
    """Record the approved list and copy its released inputs; reads no residuals."""
    data.mkdir(parents=True, exist_ok=False)
    inventory = cal.read(source / "selection.json")
    archive_path = source / "original/mpta-partim.tar.gz"
    observed.require(cal.digest(archive_path) == ARCHIVE_SHA256, "MPTA archive digest")
    by_target = {r["target"]: r for r in inventory["rows"]}
    rows = []
    with tarfile.open(archive_path) as archive:
        members = {m.name.split("/")[-1]: m for m in archive.getmembers() if m.isfile()}
        for index, target in enumerate(targets):
            source_row = by_target[target]
            if source_row["exclusion_reasons"] != ["supplied_binary_model"]:
                raise ValueError("Not a binary-only exclusion: " + target)
            folder = data / target / "original"
            folder.mkdir(parents=True)
            for suffix in (".par", ".tim"):
                payload = archive.extractfile(members[target + suffix]).read()
                (folder / (target + suffix)).write_bytes(payload)
                if cal.digest(folder / (target + suffix)) != source_row[suffix[1:] + "_sha256"]:
                    raise ValueError("Inventory input digest changed: " + target + suffix)
            fields = par_fields((folder / (target + ".par")).read_text())
            rows.append({**{k: source_row[k] for k in ("target", "noise", "par_sha256", "tim_sha256", "toas", "epochs",
                                                         "span_days", "precision_proxy_us")},
                         "batch_index": index, "binary_model": fields["BINARY"][0],
                         "binary_period_days": inner_period_days(fields)})
            if chosen(shapiro_basis, target):
                free = sorted({"STIG": "STIGMA"}.get(k, k) for k, v in fields.items()
                              if {"STIG": "STIGMA"}.get(k, k) in shapiro.PARAMETERS and len(v) > 1 and v[1] == "1")
                if not free:
                    raise ValueError("No free Shapiro parameter: " + target)
                rows[-1]["shapiro_basis"] = free
            if chosen(reexpressed, target):
                # Fails here, before any observation is read, if the orbit is not one the re-expression maps.
                rows[-1]["reexpression"] = reexpress.convert((folder / (target + ".par")).read_text())[1]
    cal.write(data / "selection.json", {
        "created_utc": observed.now(), "dataset": "MPTA 4.5-year binary", "owner_instruction": instruction,
        "selected": list(targets), "rows": rows, "policy": {**POLICY, "search_count": len(targets)},
        "source": str(source), "source_selection_sha256": cal.digest(source / "selection.json"),
        "archive_sha256": ARCHIVE_SHA256,
        "clock_sha256": {n: cal.digest(source / "original" / n) for n in ("mk2utc_observatory.clk", "tai2tt_bipm2020.clk")},
        "observed_periodograms_inspected": False,
        "rule": "Approved list in precision order; one frozen search per compatible target; the batch allowance "
                "counts every listed target, held or not"})
    print("SELECTED", " ".join(targets), flush=True)


def orbit_checks(model, toas, design, names, covariance, residuals):
    """Derivative, local-linearity, rank and fitted-shift checks for every free orbital parameter."""
    import astropy.units as u

    component, = [c for c in model.components.values() if c.category == "pulsar_system"]
    params = [p for p in component.params if p in model.free_params]
    if not params:
        raise ValueError("No free orbital parameter: orbital uncertainty would not be projected")
    if not set(params).issubset(names):
        raise ValueError("Orbital parameters missing from joint design")
    sigma = np.sqrt(np.diag(covariance))
    # Uncertainty of each column under the covariance the search uses. The released MPTA par
    # uncertainties are several times smaller than this (they do not carry the published noise
    # model), so the checked neighbourhood is three times the larger of the two.
    lower = cholesky(covariance, lower=True)
    whitened = solve_triangular(lower, design, lower=True)
    norm = np.linalg.norm(whitened, axis=0)
    normalized = whitened / norm
    rank = int(np.linalg.matrix_rank(normalized))
    if rank != design.shape[1]:
        raise ValueError(f"Joint timing/binary design is rank deficient: {rank} of {design.shape[1]}")
    own = np.sqrt(np.diag(np.linalg.inv(normalized.T @ normalized))) / norm
    base = np.asarray(model.delay(toas).to_value(u.s), np.longdouble)
    checks = {}
    for name in params:
        parameter = getattr(model, name)
        value, uncertainty = parameter.value, parameter.uncertainty_value
        if uncertainty is None or not uncertainty > 0:
            raise ValueError("Released orbital uncertainty missing: " + name)
        width = max(float(uncertainty), float(own[names.index(name)]))
        step = np.longdouble(width) * 3
        small = np.longdouble(uncertainty) * (0.03 if name in SMALL_STEP else 1.0)
        analytic = np.asarray(model.d_delay_d_param(toas, name).to_value(u.s / parameter.units), np.longdouble)
        try:
            delays = []
            for offset in (small, -small, step, -step):
                parameter.value = value + offset
                delays.append((np.longdouble(parameter.value), np.asarray(model.delay(toas).to_value(u.s), np.longdouble)))
        finally:
            parameter.value = value
        (vp, dp), (vm, dm), (_, plus), (_, minus) = delays
        numeric = (dp - dm) / (vp - vm)
        relative = float(np.linalg.norm(numeric - analytic) / np.linalg.norm(analytic))
        nonlinearity = float(max(np.max(abs(plus - base - analytic * step) / sigma),
                                 np.max(abs(minus - base + analytic * step) / sigma)))
        checks[name] = {"step_in_parameter_units": float(step), "released_uncertainty": float(uncertainty),
                        "uncertainty_under_search_covariance": float(own[names.index(name)]),
                        "relative_derivative_error": relative,
                        "maximum_nonlinearity_in_TOA_sigma": nonlinearity}
        if relative > 1e-3 or nonlinearity > 0.1:
            raise ValueError("Binary derivative/local-linearity mismatch: " + name + " " + json.dumps(checks[name]))
    model.delay(toas)
    y = solve_triangular(lower, residuals, lower=True)
    beta = np.linalg.lstsq(normalized, y, rcond=1e-12)[0] / norm
    remainder = y - whitened @ beta
    shifts = {p: float(abs(beta[names.index(p)]) / checks[p]["step_in_parameter_units"] * 3) for p in params}
    published = {p: float(abs(beta[names.index(p)]) / getattr(model, p).uncertainty_value) for p in params}
    if max(shifts.values()) > 3:
        raise ValueError("Released orbit requires a shift outside the checked neighbourhood: " + json.dumps(shifts))
    return {"binary_parameters": params, "derivatives": checks, "fitted_binary_shift_in_checked_sigma": shifts,
            "fitted_binary_shift_in_published_sigma": published,
            "checked_neighbourhood": "Three times the larger of the released uncertainty and the uncertainty under "
                                     "the search covariance",
            "null_reduced_chi2": float(remainder @ remainder / (len(residuals) - rank)),
            "design_rank": rank, "design_columns": design.shape[1],
            "normalized_design_condition": float(np.linalg.cond(normalized))}


def prepare(data, target):
    import pint.logging
    import pint.observatory
    from astropy import units as u
    from pint.models import get_model
    from pint.observatory.clock_file import ClockFile
    from pint.toa import get_TOAs

    selection = cal.read(data / "selection.json")
    row = next(r for r in selection["rows"] if r["target"] == target)
    source = Path(selection["source"])
    root = data / target
    output = root / "prepared"
    if (output / "failure.json").exists() and not (root / "profile").exists():
        output.rename(root / f"attempt{len(list(root.glob('attempt*-failed'))) + 1:02d}-failed")
    output.mkdir(exist_ok=False)
    pint.logging.setup(level="INFO", sink=output / "pint.log", removeprior=True)
    try:
        par, tim = [root / "original" / (target + suffix) for suffix in (".par", ".tim")]
        observed.require(cal.digest(par) == row["par_sha256"] and cal.digest(tim) == row["tim_sha256"], "released inputs")
        for name, digest in selection["clock_sha256"].items():
            observed.require(cal.digest(source / "original" / name) == digest, "clock file " + name)
        text = "\n".join(line for line in par.read_text().splitlines()
                         if line.split() and line.split()[0] not in {"EPHVER", "NTOA", "CHI2R", "TRES"})
        released = None
        if row.get("reexpression"):
            released = get_model(io.StringIO(text), allow_tcb=True)
            text, record = reexpress.convert(text)
            observed.require(record == row["reexpression"], "re-expression matches the selection")
        model = get_model(io.StringIO(text), allow_tcb=True)
        component, = [c for c in model.components.values() if c.category == "pulsar_system"]
        bind_precise_spin_phase(model)
        basis_start = {}
        if row.get("shapiro_basis"):
            basis_start = {p: (float(getattr(model, p).value), getattr(model, p).uncertainty_value)
                           for p in shapiro.PARAMETERS if p in model.free_params}
            observed.require(sorted(basis_start) == row["shapiro_basis"], "free Shapiro parameters match the selection")
            for name in basis_start:
                getattr(model, name).frozen = True
        repaired = component.binary_model_name == "ELL1" and {"M2", "SINI"} <= set(model.free_params)
        if repaired:
            wideband.bind_ell1_derivative(model, "fitted")
        resource_manifest = cal.read(observed.RESOURCES / "metadata/resources.json")
        with ExitStack() as stack:
            deny = stack.enter_context(NetworkDeny())
            local = stack.enter_context(LocalPintRepository(observed.RESOURCES, resource_manifest))
            local.bind_science_resources()
            pint.observatory._bipm_clock_versions["bipm2020"] = ClockFile.read(
                source / "original/tai2tt_bipm2020.clk", format="tempo2")
            pint.observatory.Observatory.get("meerkat")._clock = [
                ClockFile.read(source / "original/mk2utc_observatory.clk", format="tempo2")]
            toas = get_TOAs(tim, model=model, ephem="DE440", planets=True, usepickle=False, limits="error",
                            include_bipm=True, bipm_version="BIPM2020")
            phase = model.phase(toas, abs_phase=False)
            relative, arc = observed.unwrap_cluster(phase.frac.to_value(u.dimensionless_unscaled))
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
            errors = toas.get_errors().to_value(u.s)
            covariance = observed.published_covariance(times, errors, index, row["noise"])
            shapiro_report = None
            if basis_start:
                earlier = model.delay(toas, cutoff_component=type(component).__name__, include_last=False)
                orbit = lambda: np.asarray(component.binarymodel_delay(toas, earlier).to_value(u.s), np.longdouble)
                nominal, nominal_total = orbit(), np.asarray(model.delay(toas).to_value(u.s), np.longdouble)

                def change(values, total=False):
                    try:
                        for name, value in values.items():
                            getattr(model, name).value = value
                        if total:
                            return np.asarray(model.delay(toas).to_value(u.s), np.longdouble) - nominal_total
                        return orbit() - nominal
                    finally:
                        for name, (value, _) in basis_start.items():
                            getattr(model, name).value = value

                probe = {n: v + (0.5 * e if n not in ("SINI", "STIGMA") else -0.5 * e) for n, (v, e) in basis_start.items()}
                observed.require(float(np.max(abs(change(probe) - change(probe, total=True)))) < 1e-12,
                                 "orbit delay accounts for the whole Shapiro change")
                columns, shapiro_report = shapiro.build(change, basis_start, design, covariance, residuals,
                                                        selection["policy"]["seed"] + row["batch_index"] + 20000)
                model.delay(toas)
                design = np.column_stack([design, columns])
                names = list(names) + [f"SHAPIRO_BASIS{i + 1}" for i in range(columns.shape[1])]
            if released is not None:
                model.TASC.uncertainty_value = reexpress.own_uncertainty(design, names, covariance, ["TASC"])["TASC"]
            checks = orbit_checks(model, toas, design, names, covariance, residuals)
            if released is not None:
                same = reexpress.equivalence(np.asarray(released.delay(toas).to_value(u.s), np.longdouble),
                                             np.asarray(model.delay(toas).to_value(u.s), np.longdouble),
                                             design, covariance)
                checks["reexpression"] = {**record, "equivalence": same}
                if same["maximum_difference_in_TOA_sigma"] > reexpress.EQUIVALENCE_LIMIT:
                    raise ValueError("Re-expressed orbit does not reproduce the released model: " + json.dumps(same))
            if shapiro_report is not None:
                checks["shapiro_basis"] = shapiro_report
            if deny.attempts:
                raise RuntimeError("Unexpected scientific network access")
            (output / "timing-model.par").write_text(model.as_parfile())
            epoch = float(model.PEPOCH.value)
        policy = {**selection["policy"], "minimum_period_days": max(30.0, 10 * row["binary_period_days"]),
                  "maximum_period_days": min(selection["policy"]["maximum_period_days"], float(np.ptp(times)) / 2),
                  "seed": selection["policy"]["seed"] + row["batch_index"]}
        np.savez_compressed(output / "observed.npz", residuals=residuals)
        np.savez_compressed(output / "metadata.npz", radio=radio, epoch_index=index, errors=errors)
        receipt = {
            "status": COMPATIBLE, "target": target, "toas": len(times), "epochs": len(groups),
            "span_days": float(np.ptp(times)), "phase_arc_cycles": arc, "binary_model": row["binary_model"],
            "searched_binary_model": component.binary_model_name,
            "orbit_reexpress_sha256": cal.digest(reexpress.__file__),
            "shapiro_basis_sha256": cal.digest(shapiro.__file__),
            "binary_period_days": row["binary_period_days"], "policy": policy, "checks": checks,
            "ell1_shapiro_derivative_repair": bool(repaired), "timing_names": names, "epoch_dm_columns": len(groups),
            "noise": row["noise"],
            "noise_model": "Published EFAC/EQUAD/ECORR; 120-mode intrinsic red plus fixed-13/3 red at Table 1 MAP; "
                           "per-observation dispersion columns replace the DM and solar-wind models; all free "
                           "orbital, timing and instrumental derivatives jointly projected",
            "time_basis": "PINT barycentric TDB before the binary delay; approximate TCB-to-TDB model conversion",
            "observed_sha256": cal.digest(output / "observed.npz"), "selection_sha256": cal.digest(data / "selection.json"),
            "adapter_sha256": cal.digest(__file__), "mpta_batch_sha256": cal.digest(observed.__file__),
            "binary_wideband_sha256": cal.digest(wideband.__file__), "network_attempts": 0,
            "resources_sha256": cal.digest(observed.RESOURCES / "metadata/resources.json")}
        cal.write(output / "receipt.json", receipt)
        cal.create_profile(
            root / "profile", target,
            {"times": times, "covariance": covariance, "design": design, "baseline_design": baseline},
            {"timing_model": "Released " + row["binary_model"] + " binary model"
                             + (" re-expressed as " + component.binary_model_name if released is not None else "")
                             + ("; free Shapiro parameters frozen and replaced by a verified nuisance basis"
                                if basis_start else "")
                             + "; local linear marginalization of all "
                             "free orbital parameters; per-observation dispersion nuisance",
             "noise_model": receipt["noise_model"], "preparation_receipt_sha256": cal.digest(output / "receipt.json")},
            policy, reference_epoch=epoch)
        print(json.dumps({"target": target, "status": COMPATIBLE, "toas": len(times),
                          "orbital_parameters": checks["binary_parameters"]}), flush=True)
    except Exception as error:
        cal.write(output / "failure.json", {"target": target, "status": "PREPARATION_FAILED", "error": str(error),
                                            "adapter_sha256": cal.digest(__file__)})
        raise


def verify(data, target):
    root = data / target
    receipt = cal.read(root / "prepared/receipt.json")
    profile, arrays = cal.load_profile(root / "profile/profile.json")
    observed.require(receipt["status"] == COMPATIBLE, "compatible preparation")
    observed.require(receipt["adapter_sha256"] == cal.digest(__file__), "adapter unchanged since preparation")
    observed.require(receipt["orbit_reexpress_sha256"] == cal.digest(reexpress.__file__), "re-expression unchanged")
    observed.require(receipt["shapiro_basis_sha256"] == cal.digest(shapiro.__file__), "Shapiro treatment unchanged")
    observed.require(receipt["selection_sha256"] == cal.digest(data / "selection.json"), "selection unchanged")
    observed.require(receipt["observed_sha256"] == cal.digest(root / "prepared/observed.npz"), "observations unchanged")
    observed.require(profile["provenance"]["preparation_receipt_sha256"] == cal.digest(root / "prepared/receipt.json"),
                     "receipt bound to profile")
    return profile, arrays


def calibrate(data):
    """Threshold from 4,096 fixed-noise nulls per compatible target, plus a bounded injection diagnostic."""
    results, held = [], []
    for target in cal.read(data / "selection.json")["selected"]:
        root = data / target
        if not (root / "profile").exists():
            failure = root / "prepared/failure.json"
            held.append(cal.read(failure) if failure.exists() else {"target": target, "status": "NOT_PREPARED"})
            continue
        profile, arrays = verify(data, target)
        result = cal.run(root / "profile/profile.json", data / "calibration-cache")
        with np.load(Path(result["path"]) / "projection-and-sensitivity.npz") as z:
            indices = np.flatnonzero(z["eligible"])
            frequencies, amplitudes = z["frequencies"], z["worst_phase_amplitude_us"]
        chosen = indices[np.linspace(0, len(indices) - 1, 3).astype(int)]
        scanner = prepare_covariance_gls_scanner(arrays["covariance"], arrays["design"], arrays["times"],
                                                 frequencies[chosen], profile["reference_epoch_mjd_tdb"])
        generator = np.random.default_rng(profile["policy"]["seed"] + 10000)
        recovered = trials = 0
        maximum_error = 0.0
        for i, grid_index in enumerate(chosen):
            template = observed.circular_template(arrays["times"], profile["reference_epoch_mjd_tdb"],
                                                  frequencies[grid_index], len(arrays["covariance"]))
            for phase in (0, np.pi / 2):
                coefficient = amplitudes[grid_index] * 1e-6 * np.array([np.cos(phase), np.sin(phase)])
                injected = scanner.whiten_and_project(template @ coefficient)
                fit = scanner.template_gram_pseudoinverse[i] @ (scanner.projected_whitened_templates[:, i].T @ injected)
                maximum_error = max(maximum_error, float(np.linalg.norm(fit - coefficient) / np.linalg.norm(coefficient)))
                if maximum_error > 1e-6:
                    raise ValueError("Injected binary-projected amplitude recovery mismatch")
                for _ in range(16):
                    rhs = scanner.projected_whitened_templates[:, i].T @ (injected + generator.standard_normal(len(injected)))
                    recovered += bool(rhs @ scanner.template_gram_pseudoinverse[i] @ rhs > result["threshold"])
                    trials += 1
        results.append({"target": target, "calibration": result, "profile_sha256": cal.digest(root / "profile/profile.json"),
                        "noiseless_relative_amplitude_error": maximum_error,
                        "conditional_injection_recovered": recovered, "conditional_injection_trials": trials,
                        "injection_scope": "Three eligible periods, two phases, 16 fixed-noise realizations each; "
                                           "diagnostic, not occurrence completeness"})
        print(json.dumps({k: results[-1][k] for k in ("target", "conditional_injection_recovered")}
                         | {"threshold": result["threshold"]}), flush=True)
    if not results:
        raise ValueError("No compatible preparation; inspect retained holds")
    cal.write(data / "preparation.json", {"status": "PREPARED", "results": results, "held": held,
                                          "selection_sha256": cal.digest(data / "selection.json"),
                                          "observed_search_executed": False})


def freeze(data):
    preparation = cal.read(data / "preparation.json")
    selection = cal.read(data / "selection.json")
    observed.require(preparation["status"] == "PREPARED"
                     and preparation["selection_sha256"] == cal.digest(data / "selection.json"), "preparation matches")
    path = data / "execution-freeze.json"
    if path.exists():
        raise FileExistsError("Execution already frozen")
    targets = {}
    for row in preparation["results"]:
        target = row["target"]
        root = data / target
        if (root / "run01").exists():
            raise FileExistsError("Consumed observed destination")
        verify(data, target)
        observed.require(cal.digest(root / "profile/profile.json") == row["profile_sha256"], "profile unchanged")
        targets[target] = {"profile_sha256": row["profile_sha256"],
                           "observed_sha256": cal.digest(root / "prepared/observed.npz"),
                           "calibration": cal.run(root / "profile/profile.json", data / "calibration-cache")}
    cal.write(path, {
        "created_utc": observed.now(), "selection_sha256": cal.digest(data / "selection.json"),
        "code_sha256": cal.digest(observed.__file__), "implementation": cal.implementation(), "targets": targets,
        "batch_alpha_conditional": selection["policy"]["false_alarm_probability"],
        "max_targets": selection["policy"]["search_count"],
        "binary_adapter_sha256": cal.digest(__file__), "binary_wideband_sha256": cal.digest(wideband.__file__),
        "orbit_reexpress_sha256": cal.digest(reexpress.__file__),
        "shapiro_basis_sha256": cal.digest(shapiro.__file__),
        "preparation_sha256": cal.digest(data / "preparation.json"),
        "held_targets": [r["target"] for r in preparation["held"]],
        "search": "One circular outer-companion grid per compatible MeerKAT binary; individual profile bounds; joint "
                  "free orbital/timing projection; fixed published noise; the allowance counts every listed target"})
    print("FROZEN " + cal.digest(path), flush=True)


def run(data, target):
    frozen = cal.read(data / "execution-freeze.json")
    observed.require(frozen["binary_adapter_sha256"] == cal.digest(__file__)
                     and frozen["orbit_reexpress_sha256"] == cal.digest(reexpress.__file__)
                     and frozen["shapiro_basis_sha256"] == cal.digest(shapiro.__file__)
                     and frozen["binary_wideband_sha256"] == cal.digest(wideband.__file__)
                     and frozen["preparation_sha256"] == cal.digest(data / "preparation.json"),
                     "frozen adapter and preparation unchanged")
    observed.run(data, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("select", "prepare", "calibrate", "freeze", "run"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--target")
    parser.add_argument("--source", type=Path, help="select: the MPTA inventory directory (mpta-batch01-20260908)")
    parser.add_argument("--targets", nargs="+", help="select: approved targets in order")
    parser.add_argument("--instruction", help="select: the owner's instruction, verbatim")
    parser.add_argument("--reexpress", nargs="*", metavar="TARGET",
                        help="select: re-express these DD/DDH orbits in the small-eccentricity form (no names: all)")
    parser.add_argument("--shapiro-basis", nargs="*", metavar="TARGET",
                        help="select: treat these targets' free Shapiro parameters with a verified basis (no names: all)")
    args = parser.parse_args()
    data = args.data.resolve()
    if args.command == "select":
        if not (args.source and args.targets and args.instruction):
            parser.error("select needs --source, --targets and --instruction")
        option = lambda value: False if value is None else (value or True)
        select(data, args.source.resolve(), args.targets, args.instruction, option(args.reexpress),
               option(args.shapiro_basis))
    elif args.command in ("prepare", "run"):
        if not args.target:
            parser.error("--target is required")
        globals()[args.command](data, args.target)
    else:
        globals()[args.command](data)


if __name__ == "__main__":
    main()
