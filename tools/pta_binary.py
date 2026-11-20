"""Parkes (PPTA DR3) and European (EPTA DR2) known binaries: one search each for an additional circular outer companion.

The released-noise preparation of tools/pta_campaign.py (used for the
isolated pulsars of these releases) with the binary procedure of
tools/mpta_binary.py: every free orbital parameter is projected with the
timing, dispersion and instrumental columns after its derivative and local
linearity have been checked. Three opt-in or automatic model steps come
first, each with its own check:

translation     `BINARY T2` or `BT` renamed to the supported model with the
                same parameters (tools/orbit_translate.py); automatic.
re-expression   nearly circular Keplerian orbits rewritten in the
                small-eccentricity form (tools/orbit_reexpress.py); opt-in.
Shapiro basis   free Shapiro parameters replaced by a verified nuisance
                basis (tools/shapiro_basis.py); opt-in.

A target that fails a check is held, not searched.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
from contextlib import ExitStack
from pathlib import Path

import numpy as np

import binary_wideband as wideband
import mpta_batch as observed
import mpta_binary
import ng15_binary
import orbit_reexpress as reexpress
import orbit_refine as refine
import orbit_translate as translate
import pta_campaign as campaign
import shapiro_basis as shapiro
import target_calibration as cal
from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

SOURCES = {"ppta": "PPTA DR3", "epta": "EPTA DR2full, Zenodo 8164425"}
POLICY = {**cal.DEFAULT_POLICY, "minimum_period_days": 30.0, "maximum_period_days": 2000.0, "seed": 2026112100}
COMPATIBLE = "BINARY_TIMING_NOISE_COMPATIBLE"
OMITTED = {"EPHVER", "NTOA", "CHI2R", "TRES", "TNsubtractRed", "TNsubtractDM", "TNsubtractChrom", "TNBandNoise"}
ASTROMETRY = {"RAJ", "DECJ", "ELONG", "ELAT", "PMRA", "PMDEC", "PMELONG", "PMELAT", "PX"}
MODULES = (wideband, observed, mpta_binary, ng15_binary, reexpress, refine, translate, campaign, shapiro)


def code():
    return {"adapter": cal.digest(__file__), **{m.__name__: cal.digest(m.__file__) for m in MODULES}}


def model_text(par_text, source, original, target):
    """Released par text with report-only lines dropped, repeated chromatic settings merged and EPTA noise added."""
    lines, chromatic = [], {}
    for line in par_text.splitlines():
        fields = line.split()
        if not fields or fields[0] in OMITTED:
            continue
        if fields[0].upper().startswith("TNCHROM"):
            key = fields[0].upper()
            if key in chromatic:
                if fields[1:] != chromatic[key]:
                    raise ValueError("Conflicting repeated chromatic parameter")
                continue
            chromatic[key] = fields[1:]
        lines.append(line)
    if source == "epta":
        lines += campaign.epta_noise_lines(original, target)
    return "\n".join(lines) + "\n"


def unimplemented_terms(text):
    """Par keys the timing library does not implement and would drop silently (for example tempo2 GAUS events).

    Found by comparison with native tempo2 (J1603-7202, Parkes): a chromatic Gaussian event in the release is
    ignored on loading. `DM_SERIES TAYLOR` is the one unrecognised key that is harmless: it names the
    convention the library already uses.
    """
    from pint.models.model_builder import ModelBuilder, parse_parfile

    unknown = ModelBuilder()._pintify_parfile(parse_parfile(io.StringIO(text)))[2]
    return sorted(k for k, v in unknown.items()
                  if not (k == "DM_SERIES" and [x.split()[0].upper() for x in v] == ["TAYLOR"]))


def nonzero_design(model, toas):
    """Design matrix without columns that are identically zero (empty released JUMP or DMX ranges)."""
    design, names, _ = model.designmatrix(toas)
    keep = np.linalg.norm(design, axis=0) > 0
    return design[:, keep], [n for n, k in zip(names, keep) if k], [n for n, k in zip(names, keep) if not k]


def fill_missing_uncertainties(model, component, design, names, covariance):
    """Give free orbital and Shapiro parameters without a released uncertainty the one under the search covariance.

    Never replaces an uncertainty the release does give. Returns {parameter: uncertainty used}.
    """
    from scipy.linalg import cholesky, solve_triangular

    missing = [p for p in component.params if p in model.free_params
               and not (getattr(model, p).uncertainty_value is not None and getattr(model, p).uncertainty_value > 0)]
    if not missing:
        return {}
    whitened = solve_triangular(cholesky(covariance, lower=True), design, lower=True)
    norm = np.linalg.norm(whitened, axis=0)
    normalized = whitened / norm
    if np.linalg.matrix_rank(normalized) != normalized.shape[1]:
        raise ValueError("Joint timing/binary design is rank deficient")
    own = np.sqrt(np.diag(np.linalg.inv(normalized.T @ normalized))) / norm
    filled = {}
    for name in missing:
        if name not in names:
            raise ValueError("Orbital parameter missing from the design: " + name)
        filled[name] = float(own[names.index(name)])
        getattr(model, name).uncertainty_value = filled[name]
    return filled


def searched_text(text, row):
    """Apply the recorded model steps in order; each must reproduce the record made at selection."""
    record = {}
    if row.get("translation"):
        text, record["translation"] = translate.translate(text)
        observed.require(record["translation"] == row["translation"], "translation matches the selection")
    if row.get("shapiro_recentring"):
        text, record["shapiro_recentring"] = translate.recentre_orthometric(text)
        observed.require(record["shapiro_recentring"] == row["shapiro_recentring"], "re-centring matches the selection")
    if row.get("reexpression"):
        cleaned, dropped = ng15_binary.drop_inert(text)
        text, record["reexpression"] = reexpress.convert(cleaned)
        observed.require(record["reexpression"] == row["reexpression"]
                         and dropped == row["zero_unfitted_terms_dropped"], "re-expression matches the selection")
    return text, record


def select(data, source, intake, targets, instruction, reexpressed=False, shapiro_basis=False, tims=None, development=False,
           refined=False):
    """Copy the released inputs of the listed binaries and record the model steps; reads no residuals.

    intake: the September source-compatibility directory. tims: for PPTA, the directory holding the
    released tim files of the binaries (they were not part of the September intake).
    """
    chosen = lambda option, target: option is True or (option and target in option)
    if source not in SOURCES:
        raise ValueError("Unknown source: " + source)
    if not targets or len(targets) != len(set(targets)):
        raise ValueError("Selection needs unique targets")
    data.mkdir(parents=True, exist_ok=False)
    rows = []
    for index, target in enumerate(targets):
        dest = data / target / "original"
        dest.mkdir(parents=True)
        if source == "ppta":
            if tims is None:
                raise ValueError("PPTA binaries need --tims")
            shutil.copy2(intake / "ppta" / (target + "_singlePsrNoise_fit.par"), dest / (target + ".par"))
            shutil.copy2(tims / (target + ".tim"), dest / (target + ".tim"))
        else:
            original = intake / "epta-noise/EPTA-DR2/DR2full" / target
            shutil.copy2(original / (target + ".par"), dest / (target + ".par"))
            shutil.copy2(original / (target + "_all.tim"), dest / (target + ".tim"))
            shutil.copytree(original / "tims", dest / "tims")
            noise = intake / "epta-noise/EPTA-DR2/noisefiles/DR2full"
            for name in (target + "_noise.json", "red_dict.json", "dm_dict.json", "chrom_dict.json"):
                shutil.copy2(noise / name, dest / name)
        text = model_text((dest / (target + ".par")).read_text(), source, dest, target)
        fields = ng15_binary.par_fields(text)
        if "BINARY" not in fields:
            raise ValueError("Not a binary: " + target)
        row = {"target": target, "batch_index": index, "binary_model": fields["BINARY"][0],
               "binary_period_days": ng15_binary.inner_period_days(fields),
               "input_hashes": {str(p.relative_to(dest)): cal.digest(p) for p in sorted(dest.rglob("*")) if p.is_file()}}
        if fields["BINARY"][0].upper() in translate.SOURCES:
            text, row["translation"] = translate.translate(text)
            translate.confirm(model_text((dest / (target + ".par")).read_text(), source, dest, target), row["translation"])
        # These releases were fitted with tempo2, whose H3/STIG form leaves two Shapiro harmonics in the orbit.
        text, recentring = translate.recentre_orthometric(text)
        if recentring:
            row["shapiro_recentring"] = recentring
        if chosen(shapiro_basis, target):
            free = ng15_binary.free_shapiro(fields)
            if not free:
                raise ValueError("No free Shapiro parameter: " + target)
            row["shapiro_basis"] = free
        if chosen(reexpressed, target):
            cleaned, dropped = ng15_binary.drop_inert(text)
            row["reexpression"] = reexpress.convert(cleaned)[1]
            row["zero_unfitted_terms_dropped"] = dropped
        if chosen(refined, target):
            if "reexpression" not in row:
                raise ValueError("Refinement applies to a re-expressed orbit: " + target)
            row["refine"] = True
        rows.append(row)
    cal.write(data / "selection.json", {
        "created_utc": observed.now(), "source": source, "dataset": SOURCES[source] + " binary",
        "owner_instruction": instruction, "selected": list(targets), "rows": rows,
        "policy": {**POLICY, "search_count": len(targets)}, "intake": str(intake), "development": bool(development),
        "observed_periodograms_inspected": False,
        "minimum_period_rule": "max(30 days, 10 inner binary periods)",
        "maximum_period_rule": "min(2000 days, half observation span)",
        "rule": "One frozen search per compatible target; the batch allowance counts every listed target, held or not"})
    print("SELECTED", source, " ".join(targets), flush=True)


def prepare(data, target):
    import pint.logging
    from astropy import units as u
    from pint.models import get_model
    from pint.toa import get_TOAs

    selection = cal.read(data / "selection.json")
    source = selection["source"]
    row = next(r for r in selection["rows"] if r["target"] == target)
    root = data / target
    output = root / "prepared"
    if (output / "failure.json").exists() and not (root / "profile").exists():
        output.rename(root / f"attempt{len(list(root.glob('attempt*-failed'))) + 1:02d}-failed")
    output.mkdir(exist_ok=False)
    pint.logging.setup(level="WARNING", sink=output / "pint.log", removeprior=True)
    try:
        original = root / "original"
        for relative, digest in row["input_hashes"].items():
            observed.require(cal.digest(original / relative) == digest, "released input " + relative)
        par_text = (original / (target + ".par")).read_text()
        released_text = model_text(par_text, source, original, target)
        text, steps = searched_text(released_text, row)
        (output / "searched.par").write_text(text)
        dropped_terms = unimplemented_terms(text)
        if dropped_terms:
            raise ValueError("Released model has terms the timing library does not implement: " + " ".join(dropped_terms))
        model = get_model(io.StringIO(text), allow_tcb=True)
        component, = [c for c in model.components.values() if c.category == "pulsar_system"]
        released = None
        if row.get("reexpression"):
            before = translate.translate(released_text)[0] if row.get("translation") else released_text
            released = get_model(io.StringIO(before), allow_tcb=True)
        released_free = list(model.free_params)
        for name in model.params:
            if name in ASTROMETRY and getattr(model, name).value is not None:
                getattr(model, name).frozen = False
        bind_precise_spin_phase(model)
        repaired = component.binary_model_name == "ELL1" and all(
            getattr(model, p).value not in (None, 0) for p in ("M2", "SINI"))
        if repaired:
            wideband.bind_ell1_derivative(model, "fitted")
        with ExitStack() as stack:
            deny = stack.enter_context(NetworkDeny())
            local = stack.enter_context(LocalPintRepository(
                observed.RESOURCES, cal.read(observed.RESOURCES / "metadata/resources.json")))
            local.bind_science_resources()
            campaign.ROOT = output          # derived clock files stay with this preparation (safe when run in parallel)
            bipm, clock_hashes = campaign.clock_binding(source)
            tim = output / "format1.tim"
            tim.write_text("\n".join(campaign.normalized_tim(original / (target + ".tim"))) + "\n")
            toas = get_TOAs(tim, model=model, ephem="DE440", planets=bool(model.PLANET_SHAPIRO.value),
                            include_bipm=True, bipm_version=bipm, usepickle=False, limits="error")
            if row.get("refine"):
                steps["refinement"] = refine.apply(model, released, toas)
            phase = model.phase(toas, abs_phase=False)
            if "delta_pulse_number" in toas.table.colnames:
                from pint.phase import Phase
                phase += Phase(toas.table["delta_pulse_number"])
            relative, arc = observed.unwrap_cluster(phase.frac.to_value(u.dimensionless_unscaled))
            if arc >= 0.5:
                raise ValueError(f"Ambiguous pulse connection: {arc}")
            residuals = np.asarray(relative / model.F0.value, float)
            times = np.asarray(toas.table["tdbld"].data, float)
            radio = toas.get_freqs().to_value(u.MHz)
            design, names, dropped = nonzero_design(model, toas)
            covariance = np.diag(model.scaled_toa_uncertainty(toas).to_value(u.s) ** 2)
            basis = model.noise_model_designmatrix(toas)
            if basis is not None:
                weights = np.asarray(model.noise_model_basis_weight(toas), dtype=float)
                basis = np.asarray(basis, dtype=float)
                covariance += (basis * weights) @ basis.T
                del basis, weights
            # Released TNEQ is added after EFAC scaling; the timing library puts it inside. Correct the diagonal.
            old_white = model.scaled_toa_uncertainty(toas).to_value(u.s) ** 2
            white = toas.get_errors().to_value(u.s) ** 2
            scale = model.components["ScaleToaError"]
            for name in scale.EFACs:
                p = getattr(model, name)
                white[p.select_toa_mask(toas)] *= float(p.value) ** 2
            for name in scale.EQUADs:
                p = getattr(model, name)
                white[p.select_toa_mask(toas)] += p.quantity.to_value(u.s) ** 2
            covariance[np.diag_indices_from(covariance)] += white - old_white
            bands = []
            for line in par_text.splitlines():
                fields = line.split()
                if fields and fields[0] == "TNBandNoise":
                    lo, hi, amp, gamma, modes = map(float, fields[1:])
                    mask = (radio >= lo) & (radio < hi)
                    covariance += observed.red_covariance(times, amp, gamma, int(modes)) * mask[:, None] * mask[None, :]
                    bands.append(fields[1:])
            # Owner rule (20 November 2026, "yes the searches own"): where the release gives no uncertainty for
            # an orbital or Shapiro parameter, the uncertainty under the search covariance stands in for it.
            filled = fill_missing_uncertainties(model, component, design, names, covariance)
            basis_start = {}
            if row.get("shapiro_basis"):
                basis_start = {p: (float(getattr(model, p).value), getattr(model, p).uncertainty_value)
                               for p in shapiro.PARAMETERS if p in model.free_params}
                observed.require(sorted(basis_start) == row["shapiro_basis"],
                                 "free Shapiro parameters match the selection")
                for name in basis_start:
                    getattr(model, name).frozen = True
                design, names, dropped = nonzero_design(model, toas)
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
                model.TASC.uncertainty_value = reexpress.own_uncertainty(design, list(names), covariance, ["TASC"])["TASC"]
            checks = mpta_binary.orbit_checks(model, toas, design, list(names), covariance, residuals)
            if released is not None:
                same = reexpress.equivalence(np.asarray(released.delay(toas).to_value(u.s), np.longdouble),
                                             np.asarray(model.delay(toas).to_value(u.s), np.longdouble), design, covariance)
                steps["reexpression"] = {**steps["reexpression"], "equivalence": same}
                if same["maximum_difference_in_TOA_sigma"] > reexpress.EQUIVALENCE_LIMIT:
                    raise ValueError("Re-expressed orbit does not reproduce the released model: " + json.dumps(same))
            if shapiro_report is not None:
                checks["shapiro_basis"] = shapiro_report
            checks["model_steps"] = steps
            checks["uncertainties_taken_from_search_covariance"] = filled
            baseline = design[:, [i for i, n in enumerate(names)
                                  if n == "Offset" or n.startswith(("DM", "JUMP", "FD")) or n == "NE_SW"]]
            if deny.attempts:
                raise RuntimeError("Scientific network request")
            (output / "timing-model.par").write_text(model.as_parfile())
            epoch = float(model.PEPOCH.value)
        minimum = max(30.0, 10 * row["binary_period_days"])
        policy = {**selection["policy"], "minimum_period_days": minimum,
                  "maximum_period_days": min(selection["policy"]["maximum_period_days"], float(np.ptp(times)) / 2),
                  "seed": selection["policy"]["seed"] + row["batch_index"]}
        if policy["minimum_period_days"] >= policy["maximum_period_days"]:
            raise ValueError("No outer-period range: %.1f to %.1f days" % (minimum, policy["maximum_period_days"]))
        np.savez_compressed(output / "observed.npz", residuals=residuals)
        noise_model = "Fixed released white and correlated noise of the release; band noise where released"
        receipt = {
            "status": COMPATIBLE, "target": target, "source": source, "toas": len(times),
            "epochs": len(np.unique(np.floor(times))), "span_days": float(np.ptp(times)), "phase_arc_cycles": arc,
            "binary_model": row["binary_model"], "searched_binary_model": component.binary_model_name,
            "binary_period_days": row["binary_period_days"], "policy": policy, "checks": checks,
            "ell1_shapiro_derivative_repair": bool(repaired), "timing_names": list(names),
            "released_free_parameters": released_free, "empty_columns_removed": dropped, "band_noise": bands,
            "model_components": list(model.components), "noise_model": noise_model,
            "astrometry": "Present position, proper motion and parallax columns projected",
            "clock_hashes": clock_hashes, "network_attempts": 0, "normalized_tim_sha256": cal.digest(tim),
            "observed_sha256": cal.digest(output / "observed.npz"), "selection_sha256": cal.digest(data / "selection.json"),
            "code_sha256": code()}
        cal.write(output / "receipt.json", receipt)
        cal.create_profile(
            root / "profile", target,
            {"times": times, "covariance": covariance, "design": design, "baseline_design": baseline},
            {"timing_model": "Released " + row["binary_model"] + " binary model searched as "
                             + component.binary_model_name + "; local linear marginalization of all free orbital "
                             "parameters" + ("; free Shapiro parameters replaced by a verified nuisance basis"
                                             if basis_start else ""),
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
    for path, digest in receipt["clock_hashes"].items():
        observed.require(cal.digest(path) == digest, "clock file unchanged")
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
        "search": "One circular outer-companion grid per compatible binary; individual profile bounds; joint free "
                  "orbital/timing projection; fixed released noise; the allowance counts every listed target"})
    print("FROZEN " + cal.digest(path), flush=True)


def run(data, target):
    frozen = cal.read(data / "execution-freeze.json")
    observed.require(frozen["binary_code_sha256"] == code()
                     and frozen["preparation_sha256"] == cal.digest(data / "preparation.json"),
                     "frozen implementation and preparation unchanged")
    observed.run(data, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("select", "prepare", "calibrate", "freeze", "run"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--target")
    parser.add_argument("--source", choices=sorted(SOURCES), help="select: the release")
    parser.add_argument("--intake", type=Path, help="select: the source-compatibility directory")
    parser.add_argument("--tims", type=Path, help="select (ppta): directory of released tim files for the binaries")
    parser.add_argument("--targets", nargs="+", help="select: approved targets in order")
    parser.add_argument("--instruction", help="select: the owner's instruction, verbatim")
    parser.add_argument("--development", action="store_true",
                        help="select: preparation-only compatibility check; the root cannot be calibrated, frozen or run")
    parser.add_argument("--reexpress", nargs="*", metavar="TARGET")
    parser.add_argument("--shapiro-basis", nargs="*", metavar="TARGET")
    parser.add_argument("--refine", nargs="*", metavar="TARGET",
                        help="select: refine these re-expressed orbits against the released model")
    args = parser.parse_args()
    data = args.data.resolve()
    if args.command == "select":
        if not (args.source and args.intake and args.targets and args.instruction):
            parser.error("select needs --source, --intake, --targets and --instruction")
        option = lambda value: False if value is None else (value or True)
        select(data, args.source, args.intake.resolve(), args.targets, args.instruction, option(args.reexpress),
               option(args.shapiro_basis), args.tims.resolve() if args.tims else None, args.development,
               option(args.refine))
    elif args.command in ("prepare", "run"):
        if not args.target:
            parser.error("--target is required")
        globals()[args.command](data, args.target)
    else:
        globals()[args.command](data)


if __name__ == "__main__":
    main()
