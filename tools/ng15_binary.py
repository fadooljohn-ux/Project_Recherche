"""NANOGrav 15-year wideband binaries: one search each for an additional circular outer companion.

The wideband preparation of tools/binary_wideband.py (released noise
covariance, joint projection of every free timing, dispersion, instrumental
and orbital column) with the two orbit treatments built for the MeerKAT
binaries: the small-eccentricity re-expression of nearly circular DD-type
orbits (tools/orbit_reexpress.py) and the verified nuisance basis for free
Shapiro-delay parameters (tools/shapiro_basis.py). Both are opt-in per
target. A target that fails a check is held, not searched.
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

import binary_noise_coverage as noise_coverage
import binary_wideband as wideband
import mpta_batch as observed
import orbit_reexpress as reexpress
import orbit_refine as refine
import shapiro_basis as shapiro
import target_calibration as cal
from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
from pulsar_pilot.pilot2_offline_resources import NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

POLICY = {**wideband.POLICY, "seed": 2026112000}
SMALL_STEP = {"SINI", "STIG", "STIGMA"}
COMPATIBLE = "BINARY_TIMING_NOISE_COMPATIBLE"
SIGN_TOLERANCE = 1e-3
INERT_WHEN_ZERO = ("OMDOT", "PBDOT", "EDOT", "GAMMA", "DR", "DTH", "A0", "B0", "XPBDOT")
BOUND = ("adapter", "binary_wideband", "orbit_reexpress", "shapiro_basis", "noise_coverage")


def code():
    return {"adapter": cal.digest(__file__), "binary_wideband": cal.digest(wideband.__file__),
            "orbit_reexpress": cal.digest(reexpress.__file__), "orbit_refine": cal.digest(refine.__file__),
            "shapiro_basis": cal.digest(shapiro.__file__),
            "noise_coverage": cal.digest(noise_coverage.__file__)}


def par_fields(text):
    return {v[0]: v[1:] for line in text.splitlines() if (v := line.split())}


def inner_period_days(fields):
    if "PB" in fields:
        return float(fields["PB"][0].replace("D", "e"))
    return 1 / float(fields["FB0"][0].replace("D", "e")) / 86400


def free_shapiro(fields):
    rename = {"STIG": "STIGMA"}
    return sorted(rename.get(k, k) for k, v in fields.items()
                  if rename.get(k, k) in shapiro.PARAMETERS and len(v) > 1 and v[1] == "1")


def drop_inert(text):
    """Remove orbital terms the release lists at exactly zero and does not fit; they do not enter the delay.

    The NANOGrav DD par files write out every DD term (OMDOT, PBDOT, GAMMA, ...) even when unused, and the
    re-expression refuses any such term by name. Returns the text and the names removed.
    """
    kept, dropped = [], []
    for line in text.splitlines():
        v = line.split()
        if (v and v[0] in INERT_WHEN_ZERO and len(v) > 1 and float(v[1].upper().replace("D", "E")) == 0.0
                and not (len(v) > 2 and v[2] == "1")):
            dropped.append(v[0])
        else:
            kept.append(line)
    return "\n".join(kept) + "\n", dropped


def padded(vector, rows):
    """A change in TOA delay as a full wideband data vector: TOA rows, then zero for the DM rows."""
    out = np.zeros(rows)
    out[:len(vector)] = np.asarray(vector, float)
    return out


def signature_sign(residual_change, delay_change, tolerance=SIGN_TOLERANCE):
    """+1 or -1: how a change in model delay appears in the residuals, apart from a constant. Raises if neither."""
    centred = delay_change - delay_change.mean()
    scale = np.linalg.norm(centred)
    for sign in (1.0, -1.0):
        difference = residual_change - sign * delay_change
        if np.linalg.norm(difference - difference.mean()) <= tolerance * scale:
            return sign
    raise ValueError("Residuals do not follow the change in orbital delay")


def select(data, archive, inventory, targets, instruction, reexpressed=False, shapiro_basis=False, refined=False):
    """Record the listed targets and copy their released inputs; reads no residuals."""
    chosen = lambda option, target: option is True or (option and target in option)
    if not targets or len(targets) != len(set(targets)):
        raise ValueError("Selection needs unique targets")
    admitted = {observed.ALIASES.get(r["target"], r["target"]): r for r in cal.read(inventory)}
    if not set(targets).issubset(admitted):
        raise ValueError("Inventory is missing: " + " ".join(sorted(set(targets) - set(admitted))))
    data.mkdir(parents=True, exist_ok=False)
    rows = []
    with tarfile.open(archive) as t:
        member, = [n for n in t.getnames() if n.endswith("/clock/vla2gps.clk")]
        resources = data / "resources"
        resources.mkdir()
        (resources / "vla2gps.clk").write_bytes(t.extractfile(member).read())
        cal.write(resources / "binding.json", {"archive_member": member, "filename": "vla2gps.clk",
                                               "sha256": cal.digest(resources / "vla2gps.clk")})
        for index, target in enumerate(targets):
            row = admitted[target]
            folder = data / target / "original"
            folder.mkdir(parents=True)
            for suffix in ("par", "tim"):
                path = folder / (target + "." + suffix)
                path.write_bytes(t.extractfile(row[suffix + "_member"]).read())
                if cal.digest(path) != row[suffix + "_sha256"]:
                    raise ValueError("Pinned input hash mismatch: " + target)
            text = (folder / (target + ".par")).read_text()
            fields = par_fields(text)
            rows.append({"target": target, "release_name": row["release_name"], "par_sha256": row["par_sha256"],
                         "tim_sha256": row["tim_sha256"], "batch_index": index, "binary_model": fields["BINARY"][0],
                         "binary_period_days": inner_period_days(fields)})
            if chosen(shapiro_basis, target):
                free = free_shapiro(fields)
                if not free:
                    raise ValueError("No free Shapiro parameter: " + target)
                rows[-1]["shapiro_basis"] = free
            if chosen(reexpressed, target):
                # Fails here, before any observation is read, if the orbit is not one the re-expression maps.
                cleaned, dropped = drop_inert(text)
                rows[-1]["reexpression"] = reexpress.convert(cleaned)[1]
                rows[-1]["zero_unfitted_terms_dropped"] = dropped
            if chosen(refined, target):
                if "reexpression" not in rows[-1]:
                    raise ValueError("Refinement applies to a re-expressed orbit: " + target)
                rows[-1]["refine"] = True
    cal.write(data / "selection.json", {
        "created_utc": observed.now(), "dataset": "NANOGrav15 v2.1.0 wideband binary", "owner_instruction": instruction,
        "selected": list(targets), "rows": rows, "policy": {**POLICY, "search_count": len(targets)},
        "noise_coverage_rule": noise_coverage.RULE, "archive_sha256": cal.digest(archive),
        "intake_inventory_sha256": cal.digest(inventory), "observed_periodograms_inspected": False,
        "minimum_period_rule": "max(30 days, 10 inner binary periods)",
        "maximum_period_rule": "min(2000 days, half observation span)",
        "rule": "One frozen search per compatible target; the batch allowance counts every listed target, held or not"})
    print("SELECTED", " ".join(targets), flush=True)


def orbit_checks(model, toas, design, names, covariance, residuals):
    """Derivative, local-linearity, rank and fitted-shift checks for every free orbital parameter (wideband layout)."""
    import astropy.units as u

    component, = [c for c in model.components.values() if c.category == "pulsar_system"]
    params = [p for p in component.params if p in model.free_params]
    count = toas.ntoas
    if not params:
        raise ValueError("No free orbital parameter: orbital uncertainty would not be projected")
    if not set(params).issubset(names):
        raise ValueError("Orbital parameters missing from joint design")
    if len(residuals) != 2 * count:
        raise ValueError("Unexpected TOA/DM layout")
    sigma = np.sqrt(np.diag(covariance)[:count])
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
                        "relative_derivative_error": relative, "maximum_nonlinearity_in_TOA_sigma": nonlinearity}
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
    if np.ptp(residuals[:count]) * float(model.F0.value) >= 0.5:
        raise ValueError("Unresolved pulse-phase connection")
    return {"binary_parameters": params, "derivatives": checks, "fitted_binary_shift_in_checked_sigma": shifts,
            "fitted_binary_shift_in_published_sigma": published,
            "checked_neighbourhood": "Three times the larger of the released uncertainty and the uncertainty under "
                                     "the search covariance",
            "null_reduced_chi2": float(remainder @ remainder / (len(residuals) - rank)),
            "design_rank": rank, "design_columns": design.shape[1],
            "normalized_design_condition": float(np.linalg.cond(normalized))}


def prepare(data, target):
    import astropy.units as u
    import pint.logging
    from pint.fitter import WidebandTOAFitter
    from pint.models import get_model, get_model_and_toas
    from pint.residuals import WidebandTOAResiduals

    selection = cal.read(data / "selection.json")
    row = next(r for r in selection["rows"] if r["target"] == target)
    root = data / target
    output = root / "prepared"
    if (output / "failure.json").exists() and not (root / "profile").exists():
        output.rename(root / f"attempt{len(list(root.glob('attempt*-failed'))) + 1:02d}-failed")
    output.mkdir(exist_ok=False)
    pint.logging.setup(level="INFO", sink=output / "pint.log", removeprior=True)
    try:
        par, tim = [root / "original" / (target + "." + suffix) for suffix in ("par", "tim")]
        observed.require(cal.digest(par) == row["par_sha256"] and cal.digest(tim) == row["tim_sha256"], "released inputs")
        with ExitStack() as stack:
            deny = stack.enter_context(NetworkDeny())
            local = stack.enter_context(wideband.BinaryResources(data))
            local.bind_science_resources()
            released, record, searched_par = None, None, par
            if row.get("reexpression"):
                released = get_model(str(par))
                cleaned, dropped = drop_inert(par.read_text())
                text, record = reexpress.convert(cleaned)
                observed.require(record == row["reexpression"] and dropped == row["zero_unfitted_terms_dropped"],
                                 "re-expression matches the selection")
                searched_par = output / "reexpressed.par"
                searched_par.write_text(text)
            model, toas = get_model_and_toas(str(searched_par), str(tim), ephem="DE440", include_bipm=True,
                                             bipm_version="BIPM2019", planets=True, usepickle=False, limits="error")
            component, = [c for c in model.components.values() if c.category == "pulsar_system"]
            bind_precise_spin_phase(model)
            refinement = refine.apply(model, released, toas) if row.get("refine") else None
            basis_start = {}
            if row.get("shapiro_basis"):
                basis_start = {p: (float(getattr(model, p).value), getattr(model, p).uncertainty_value)
                               for p in shapiro.PARAMETERS if p in model.free_params}
                observed.require(sorted(basis_start) == row["shapiro_basis"], "free Shapiro parameters match the selection")
                for name in basis_start:
                    getattr(model, name).frozen = True
            # The pinned timing library's ELL1 Shapiro derivative omits a term for every orbital parameter, so the
            # repair is needed whenever the model carries a Shapiro delay, whether or not M2 and SINI are fitted.
            repaired = component.binary_model_name == "ELL1" and all(
                getattr(model, p).value not in (None, 0) for p in ("M2", "SINI"))
            if repaired:
                wideband.bind_ell1_derivative(model, "fitted")
            minimum = max(30.0, 10 * row["binary_period_days"])
            coverage = noise_coverage.configure(model, toas, minimum)
            fitter = WidebandTOAFitter(toas, model)
            matrix = fitter.get_designmatrix()
            names = list(matrix.get_label_names(axis=1))
            design = matrix.matrix
            covariance = fitter.get_noise_covariancematrix().matrix
            wideband_residuals = lambda: np.asarray(WidebandTOAResiduals(toas, model).calc_wideband_resids(), float)
            residuals = wideband_residuals()
            rows, count = len(residuals), toas.ntoas
            shapiro_report = None
            if basis_start:
                earlier = model.delay(toas, cutoff_component=type(component).__name__, include_last=False)
                orbit = lambda: np.asarray(component.binarymodel_delay(toas, earlier).to_value(u.s), np.longdouble)
                nominal, nominal_total = orbit(), np.asarray(model.delay(toas).to_value(u.s), np.longdouble)

                def change(values, total=False, residual=False):
                    try:
                        for name, value in values.items():
                            getattr(model, name).value = value
                        if residual:
                            return wideband_residuals()
                        if total:
                            return np.asarray(model.delay(toas).to_value(u.s), np.longdouble) - nominal_total
                        return orbit() - nominal
                    finally:
                        for name, (value, _) in basis_start.items():
                            getattr(model, name).value = value

                probe = {n: v + (0.5 * e if n not in ("SINI", "STIGMA") else -0.5 * e) for n, (v, e) in basis_start.items()}
                moved = np.asarray(change(probe), float)
                observed.require(float(np.max(abs(moved - change(probe, total=True)))) < 1e-12,
                                 "orbit delay accounts for the whole Shapiro change")
                # Data whose true parameters are at `probe` leave minus this change when timed with the released model.
                trace = -(change(probe, residual=True) - residuals)
                observed.require(np.allclose(trace[count:], 0.0, atol=1e-12), "Shapiro change leaves the DM rows alone")
                sign = signature_sign(trace[:count], moved)
                columns, shapiro_report = shapiro.build(
                    lambda values: sign * padded(change(values), rows), basis_start, design, covariance, residuals,
                    selection["policy"]["seed"] + row["batch_index"] + 20000)
                shapiro_report["residual_sign_of_delay_change"] = sign
                model.delay(toas)
                design = np.column_stack([design, columns])
                names += [f"SHAPIRO_BASIS{i + 1}" for i in range(columns.shape[1])]
            if released is not None:
                model.TASC.uncertainty_value = reexpress.own_uncertainty(design, names, covariance, ["TASC"])["TASC"]
            checks = orbit_checks(model, toas, design, names, covariance, residuals)
            if released is not None:
                difference = (np.asarray(model.delay(toas).to_value(u.s), np.longdouble)
                              - np.asarray(released.delay(toas).to_value(u.s), np.longdouble))
                same = reexpress.equivalence(np.zeros(rows), padded(difference, rows), design, covariance)
                checks["reexpression"] = {**record, "equivalence": same}
                if same["maximum_difference_in_TOA_sigma"] > reexpress.EQUIVALENCE_LIMIT:
                    raise ValueError("Re-expressed orbit does not reproduce the released model: " + json.dumps(same))
            if shapiro_report is not None:
                checks["shapiro_basis"] = shapiro_report
            if refinement is not None:
                checks["refinement"] = refinement
            times = np.asarray(toas.table["tdbld"].data, float)
            baseline = [i for i, n in enumerate(names) if n.lower().startswith(("offset", "dm", "jump"))]
            if deny.attempts:
                raise RuntimeError("Scientific network access attempted")
            (output / "timing-model.par").write_text(model.as_parfile())
            epoch = float(model.PEPOCH.value)
        policy = {**selection["policy"], "minimum_period_days": minimum,
                  "maximum_period_days": min(selection["policy"]["maximum_period_days"], float(np.ptp(times)) / 2),
                  "seed": selection["policy"]["seed"] + row["batch_index"]}
        if policy["minimum_period_days"] >= policy["maximum_period_days"]:
            raise ValueError("No outer-period range: %.1f to %.1f days" % (
                policy["minimum_period_days"], policy["maximum_period_days"]))
        arrays = {"times": times, "covariance": covariance, "design": design, "baseline_design": design[:, baseline]}
        cal.validate_arrays(arrays)
        np.savez_compressed(output / "observed.npz", residuals=residuals)
        noise_model = ("Fixed NG15 wideband covariance with explicit red-frequency coverage: " + coverage["status"]
                       + "; all free binary, timing, DM and instrumental derivatives jointly projected")
        receipt = {
            "status": COMPATIBLE, "target": target, "toas": len(times), "epochs": len(set(np.floor(times).astype(int))),
            "span_days": float(np.ptp(times)), "binary_model": row["binary_model"],
            "searched_binary_model": component.binary_model_name, "binary_period_days": row["binary_period_days"],
            "policy": policy, "checks": checks, "ell1_shapiro_derivative_repair": bool(repaired),
            "timing_names": names, "noise_coverage": coverage, "noise_model": noise_model,
            "observed_sha256": cal.digest(output / "observed.npz"), "selection_sha256": cal.digest(data / "selection.json"),
            "code_sha256": code(), "network_attempts": 0, "additional_clock_binding": local.binding,
            "resources_sha256": cal.digest(observed.RESOURCES / "metadata/resources.json")}
        cal.write(output / "receipt.json", receipt)
        cal.create_profile(
            root / "profile", target, arrays,
            {"timing_model": "Released " + row["binary_model"] + " binary model"
                             + (" re-expressed as " + component.binary_model_name if released is not None else "")
                             + ("; free Shapiro parameters frozen and replaced by a verified nuisance basis"
                                if basis_start else "")
                             + "; local linear marginalization of all free orbital parameters",
             "noise_model": noise_model, "preparation_receipt_sha256": cal.digest(output / "receipt.json")},
            policy, reference_epoch=epoch)
        print(json.dumps({"target": target, "status": COMPATIBLE, "toas": len(times),
                          "orbital_parameters": checks["binary_parameters"]}), flush=True)
    except Exception as error:
        cal.write(output / "failure.json", {"target": target, "status": "PREPARATION_FAILED", "error": str(error),
                                            "code_sha256": code()})
        raise


def verify(data, target):
    root = data / target
    receipt = cal.read(root / "prepared/receipt.json")
    profile, arrays = cal.load_profile(root / "profile/profile.json")
    observed.require(receipt["status"] == COMPATIBLE, "compatible preparation")
    observed.require(receipt["code_sha256"] == code(), "implementation unchanged since preparation")
    observed.require(receipt["selection_sha256"] == cal.digest(data / "selection.json"), "selection unchanged")
    observed.require(receipt["observed_sha256"] == cal.digest(root / "prepared/observed.npz"), "observations unchanged")
    observed.require(profile["provenance"]["preparation_receipt_sha256"] == cal.digest(root / "prepared/receipt.json"),
                     "receipt bound to profile")
    return profile, arrays


def calibrate(data):
    """Threshold from fixed-noise nulls per compatible target, plus a bounded injection diagnostic."""
    selection = cal.read(data / "selection.json")
    if selection.get("development"):
        raise ValueError("Development root: not to be calibrated, frozen or run")
    results, held = [], []
    for target in selection["selected"]:
        root = data / target
        if not (root / "profile").exists():
            failure = root / "prepared/failure.json"
            held.append(cal.read(failure) if failure.exists() else {"target": target, "status": "NOT_PREPARED"})
            continue
        profile, arrays = verify(data, target)
        try:
            result = cal.run(root / "profile/profile.json", data / "calibration-cache")
        except ValueError as error:
            # For example no trial period keeps enough power after the projection: nothing to search.
            held.append({"target": target, "status": "CALIBRATION_HOLD", "error": str(error)})
            print(json.dumps(held[-1]), flush=True)
            continue
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
    observed.require(not selection.get("development"), "not a development root")
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
        "max_targets": selection["policy"]["search_count"], "binary_code_sha256": code(),
        "preparation_sha256": cal.digest(data / "preparation.json"),
        "held_targets": [r["target"] for r in preparation["held"]],
        "search": "One circular outer-companion grid per compatible NANOGrav wideband binary; individual profile "
                  "bounds; joint free orbital/timing projection; fixed released noise; the allowance counts every "
                  "listed target"})
    print("FROZEN " + cal.digest(path), flush=True)


def run(data, target):
    frozen = cal.read(data / "execution-freeze.json")
    observed.require(frozen["binary_code_sha256"] == code()
                     and frozen["preparation_sha256"] == cal.digest(data / "preparation.json"),
                     "frozen implementation and preparation unchanged")
    observed.run(data, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("select", "prepare", "calibrate", "freeze", "run"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--target")
    parser.add_argument("--archive", type=Path, help="select: the NANOGrav 15-year release tarball")
    parser.add_argument("--inventory", type=Path, help="select: the pinned parameter inventory of the release")
    parser.add_argument("--targets", nargs="+", help="select: approved targets in order")
    parser.add_argument("--instruction", help="select: the owner's instruction, verbatim")
    parser.add_argument("--development", action="store_true",
                        help="select: a preparation-only compatibility check; the root cannot be calibrated, frozen or run")
    parser.add_argument("--reexpress", nargs="*", metavar="TARGET",
                        help="select: re-express these DD orbits in the small-eccentricity form (no names: all)")
    parser.add_argument("--shapiro-basis", nargs="*", metavar="TARGET",
                        help="select: treat these targets' free Shapiro parameters with a verified basis (no names: all)")
    parser.add_argument("--refine", nargs="*", metavar="TARGET",
                        help="select: refine these re-expressed orbits against the released model (no names: all)")
    args = parser.parse_args()
    data = args.data.resolve()
    if args.command == "select":
        if not (args.archive and args.inventory and args.targets and args.instruction):
            parser.error("select needs --archive, --inventory, --targets and --instruction")
        option = lambda value: False if value is None else (value or True)
        select(data, args.archive.resolve(), args.inventory.resolve(), args.targets, args.instruction,
               option(args.reexpress), option(args.shapiro_basis), option(args.refine))
        if args.development:
            selection = cal.read(data / "selection.json")
            cal.write(data / "selection.json", {**selection, "development": True})
    elif args.command in ("prepare", "run"):
        if not args.target:
            parser.error("--target is required")
        globals()[args.command](data, args.target)
    else:
        globals()[args.command](data)


if __name__ == "__main__":
    main()
