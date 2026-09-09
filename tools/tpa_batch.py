"""TPA inventory, fixed-noise preparation and frozen observed searches."""

import argparse
import hashlib
import io
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

import mpta_batch as mpta
import numpy as np
import target_calibration as cal

from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

DATA = mpta.REPO.parent / "Project Recherche Data/tpa-batch01-20260908"
PRIOR = mpta.DATA / "research"
POLICY = {**mpta.POLICY, "search_count": 25, "seed": 2026091100}


def fields(text):
    return {v[0]: v[1:] for line in text.splitlines()
            if (v := line.split()) and not v[0].startswith(("#", "@"))}


def noise_parameters(text):
    f = fields(text)
    for key in ("TNEF", "TNEQ", "TNECORR"):
        lines = [line.split() for line in text.splitlines() if line.split()[:1] == [key]]
        if len(lines) != 1 or lines[0][1:3] != ["-be", "MKBF"]:
            raise ValueError(f"Unsupported noise selector: {key}")
    ecorr = float(f["TNECORR"][-1]) * 1e-6  # TEMPO2 TNECORR is microseconds.
    n = {"efac": float(f["TNEF"][-1]), "log10_equad": float(f["TNEQ"][-1]),
         "log10_ecorr": float(np.log10(ecorr)) if ecorr > 0 else None,
         "red_amplitude": float(f["TNRedAmp"][0]), "red_gamma": float(f["TNRedGam"][0]),
         "red_modes": int(f["TNRedC"][0])}
    if ecorr < 0 or n["efac"] <= 0 or n["red_modes"] < 1:
        raise ValueError("Invalid published noise parameter")
    if any(v is not None and not np.isfinite(v) for v in n.values()):
        raise ValueError("Nonfinite published noise parameter")
    return n


def white_covariance(errors, epoch_seconds, noise):
    """TPA ECORR: one-second buckets anchored at their first TOA, excluding singletons."""
    groups = np.empty(len(epoch_seconds), dtype=int)
    group, first = -1, None
    for index in np.argsort(epoch_seconds):
        if first is None or epoch_seconds[index] - first >= 1:
            group += 1
            first = epoch_seconds[index]
        groups[index] = group
    covariance = mpta.white_covariance(errors, groups, {**noise, "log10_ecorr": None})
    if noise["log10_ecorr"] is not None:
        same_epoch = groups[:, None] == groups[None, :]
        same_epoch &= (same_epoch.sum(axis=1) > 1)[:, None]
        covariance += same_epoch * 10.0 ** (2 * noise["log10_ecorr"])
    return covariance


def catalogue(path):
    records, aliases = {}, {}
    for block in path.read_text().split("@"):
        f = fields(block)
        if "PSRJ" not in f:
            continue
        name = f["PSRJ"][0]
        records[name] = f
        aliases[name] = name
        if "PSRB" in f:
            aliases[f["PSRB"][0]] = name
    return records, aliases


def timing_rows(text):
    result = []
    for line in text.splitlines():
        v = line.split()
        if not v or v[0] in ("FORMAT", "MODE", "C", "#"):
            continue
        if len(v) < 5 or v[4] != "meerkat" or (len(v) - 5) % 2:
            raise ValueError("Unsupported TIM observation/directive")
        flags = dict(zip(v[5::2], v[6::2]))
        result.append((v[0], float(v[1]), float(v[2]), float(v[3]), flags))
    return result


def inventory(data, batch_size=25):
    destination = data / "selection.json"
    if destination.exists():
        raise FileExistsError("Inventory/selection already recorded")
    cat, aliases = catalogue(data / "research/psrcat.db")
    canonical = lambda name: aliases.get(name, name)
    jbo = {canonical(p.split("/")[1]) for p in cal.read(PRIOR / "jbo-archive-inventory.json")
           if "/" in p}
    ng = {canonical(r[0]) for r in cal.read(PRIOR / "nanograv-tables.json")
          if r and re.match(r"[JB]\d", r[0])}
    epta = {canonical(t) for t in re.findall(r"J\d{4}[+\-]\d{4}",
                                           (PRIOR / "epta-sample.html").read_text())}
    master = cal.read(data / "research/master-targets-before.json")
    known = {canonical(r["target"]): r for r in master["targets"]}
    handmade = set((data / "original/pulsars_with_handmade_templates.txt").read_text().split())
    rows = []
    with zipfile.ZipFile(data / "original/tpa_data.zip") as archive:
        names = sorted(n for n in archive.namelist()
                       if n.startswith("tpa_data/") and n.endswith("_full.par"))
        for name in names:
            target = Path(name).name.removesuffix("_full.par")
            par, tim = archive.read(name), archive.read(f"tpa_data/{target}.tim")
            f = fields(par.decode())
            obs = timing_rows(tim.decode())
            noise = noise_parameters(par.decode())
            groups = sorted({o[0] for o in obs})
            span = float(np.ptp([o[2] for o in obs]))
            catrow = cat.get(target)
            reasons = []
            if catrow is None:
                reasons.append("catalogue_identity_unresolved")
            if "BINARY" in f or (catrow and ("BINARY" in catrow or "PB" in catrow)):
                reasons.append("known_binary")
            if any(k.startswith("GL") for k in f):
                reasons.append("published_glitch")
            if "IPERHARM" in f:
                reasons.append("harmonic_timing_convention")
            if span < 1200 or len(groups) < 40:
                reasons.append("insufficient_span_or_epochs")
            if any("-pn" not in o[4] or o[4].get("-be") != "MKBF" for o in obs):
                reasons.append("unsupported_pulse_number_or_backend")
            precision = []
            for group in groups:
                subset = [o for o in obs if o[0] == group]
                radio = np.array([o[1] for o in subset])
                errors = np.array([o[3] for o in subset]) * 1e-6
                d = np.column_stack([np.ones(len(subset)), (1400 / radio) ** 2])
                c = mpta.white_covariance(errors, np.zeros(len(subset), dtype=int), noise)
                if np.linalg.matrix_rank(d) == 2:
                    precision.append(float(np.sqrt(np.linalg.inv(d.T @ np.linalg.solve(c, d))[0, 0])))
            if len(precision) < 40 and "insufficient_span_or_epochs" not in reasons:
                reasons.append("insufficient_frequency_coverage")
            white = float(np.median(precision) / np.sqrt(len(precision))) if precision else 1e99
            # Published 100-day noise PSD proxy, without reading residuals or fitting a periodogram.
            year = 365.25 * 86400
            red = np.sqrt(10 ** (2 * noise["red_amplitude"]) / (12 * np.pi**2)
                          * (365.25 / 100) ** -noise["red_gamma"] * year**3 / (span * 86400))
            prior = {"JBO800": target in jbo, "NANOGrav11": target in ng, "EPTA_DR2": target in epta}
            row = {"target": target, "aliases": catrow.get("PSRB", [])[:1] if catrow else [],
                   "toas": len(obs), "epochs": len(groups), "span_days": span,
                   "good_frequency_epochs": len(precision), "noise": noise,
                   "prior_search_membership": prior, "master_overlap": known.get(target),
                   "handmade_template": target in handmade, "exclusion_reasons": reasons,
                   "rank_key": [sum(prior.values()), float(np.hypot(white, red) * 1e6), target],
                   "rank_definition": "Prior sample membership count, then fixed-noise 100-day amplitude proxy",
                   "selected": False, "par_sha256": hashlib.sha256(par).hexdigest(),
                   "tim_sha256": hashlib.sha256(tim).hexdigest()}
            rows.append(row)
        if len(rows) != 597:
            raise ValueError("Release inventory does not contain 597 targets")
        ranked = sorted((r for r in rows if not r["exclusion_reasons"] and not r["master_overlap"]),
                        key=lambda r: r["rank_key"])
        selected = ranked[:batch_size]
        if not selected:
            raise ValueError("No eligible first-batch targets")
        for i, row in enumerate(selected):
            row.update(selected=True, batch_index=i)
            folder = data / row["target"] / "original"
            folder.mkdir(parents=True, exist_ok=False)
            for source, dest in (("_full.par", ".par"), (".tim", ".tim")):
                (folder / (row["target"] + dest)).write_bytes(
                    archive.read("tpa_data/" + row["target"] + source))
    record = {"created_utc": mpta.now(), "dataset": "TPA DR1; DOI 10.5281/zenodo.8430591",
              "selected": [r["target"] for r in selected], "rows": rows,
              "policy": {**POLICY, "search_count": len(selected)},
              "eligible_targets": len(ranked), "remaining_after_selection": len(ranked) - len(selected),
              "exclusion_counts": dict(Counter(x for r in rows for x in r["exclusion_reasons"])),
              "prior_membership_counts": {k: sum(r["prior_search_membership"][k] for r in rows)
                                           for k in ("JBO800", "NANOGrav11", "EPTA_DR2")},
              "master_overlaps": sum(bool(r["master_overlap"]) for r in rows),
              "observed_periodograms_inspected": False,
              "novelty_scope": "Three named samples only, ATNF B/J aliases resolved; absence is not exhaustive novelty",
              "source_hashes": {str(p.resolve()): cal.digest(p) for p in
                                [*(data / "original").iterdir(), *(data / "research").iterdir(),
                                 PRIOR / "jbo-archive-inventory.json", PRIOR / "nanograv-tables.json",
                                 PRIOR / "epta-sample.html"] if p.is_file()}}
    cal.write(destination, record)
    print(json.dumps({k: v for k, v in record.items() if k not in ("rows", "source_hashes")}), flush=True)


def inventory_next(data, previous, batch_size=25):
    """Advance the saved ranking, excluding previous selections and master work."""
    prior = cal.read(previous / "selection.json")
    consumed = set(prior.get("previously_selected", [])) | set(prior["selected"])
    for target in prior["selected"]:
        if not (previous / target / "run01/result.json").exists():
            raise ValueError("Close the previous batch before advancing")
    master = mpta.REPO / "outputs/recherche-master-20260908/Project-Recherche-Master.xlsx"
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(master) as book:
        sheets = ET.fromstring(book.read("xl/workbook.xml")).find("s:sheets", ns)
        assert sheets[1].attrib["name"] == "Targets"
        strings = ["".join(node.itertext()) for node in ET.fromstring(book.read("xl/sharedStrings.xml"))]
        master_rows = {}
        for row in ET.fromstring(book.read("xl/worksheets/sheet2.xml")).findall(".//s:sheetData/s:row", ns):
            values = {}
            for cell in row:
                value = cell.find("s:v", ns)
                if value is not None:
                    values[re.sub(r"\d", "", cell.attrib["r"])] = strings[int(value.text)] if cell.get("t") == "s" else value.text
            if values.get("A"):
                master_rows[values["A"]] = values
    ranked = sorted((r for r in prior["rows"] if r["target"] not in consumed
                     and not r["exclusion_reasons"]
                     and master_rows.get(r["target"], {}).get("G") == "TPA ELIGIBLE"
                     and master_rows[r["target"]].get("C") == "NOT_SEARCHED"), key=lambda r: r["rank_key"])
    chosen = ranked[:batch_size]
    if not chosen:
        raise ValueError("No remaining eligible targets in the master")
    for row in chosen:
        assert master_rows[row["target"]]["S"] == row["par_sha256"]
        assert master_rows[row["target"]]["T"] == row["tim_sha256"]
    data.mkdir(parents=True, exist_ok=False)
    (data / "original").mkdir()
    for name in ("tpa_data.zip", "tai2tt_bipm2019.clk", "mk2utc_observatory.clk"):
        source = previous / "original" / name
        assert cal.digest(source) == prior["source_hashes"][str(source.resolve())]
        shutil.copy2(source, data / "original" / name)
    for row in prior["rows"]:
        row["selected"] = False
        row.pop("batch_index", None)
    with zipfile.ZipFile(data / "original/tpa_data.zip") as archive:
        for i, row in enumerate(chosen):
            row.update(selected=True, batch_index=i)
            folder = data / row["target"] / "original"
            folder.mkdir(parents=True)
            for suffix, source, key in ((".par", "_full.par", "par_sha256"), (".tim", ".tim", "tim_sha256")):
                payload = archive.read("tpa_data/" + row["target"] + source)
                assert hashlib.sha256(payload).hexdigest() == row[key]
                (folder / (row["target"] + suffix)).write_bytes(payload)
    record = {**prior, "created_utc": mpta.now(), "selected": [r["target"] for r in chosen],
              "policy": {**prior["policy"], "search_count": len(chosen),
                         "seed": prior["policy"]["seed"] + max(100, prior["policy"]["search_count"])},
              "eligible_targets": len(ranked), "remaining_after_selection": len(ranked) - len(chosen),
              "total_eligible_targets": prior.get("total_eligible_targets", prior["eligible_targets"]),
              "previously_selected": sorted(consumed),
              "previous_completed_count": prior.get("previous_completed_count", 0) + len(prior["selected"]),
              "previous_selection": str(previous / "selection.json"),
              "previous_selection_sha256": cal.digest(previous / "selection.json"),
              "master_workbook_sha256": cal.digest(master),
              "source_hashes": {**prior["source_hashes"], **{str(p.resolve()): cal.digest(p) for p in (data / "original").iterdir()}}}
    cal.write(data / "selection.json", record)
    print(json.dumps({"selected": record["selected"], "remaining_after_selection": record["remaining_after_selection"]}), flush=True)


def prepare(data, target):
    import pint.logging
    import pint.observatory
    from astropy import units as u
    from pint.models import get_model
    from pint.observatory.clock_file import ClockFile
    from pint.residuals import Residuals
    from pint.toa import get_TOAs

    selection = cal.read(data / "selection.json")
    row = next(r for r in selection["rows"] if r["target"] == target and r["selected"])
    root = data / target
    output = root / "prepared"
    output.mkdir(exist_ok=False)
    pint.logging.setup(level="INFO", sink=output / "pint.log", removeprior=True)
    par, tim = (root / "original" / (target + s) for s in (".par", ".tim"))
    assert cal.digest(par) == row["par_sha256"] and cal.digest(tim) == row["tim_sha256"]
    content = "\n".join(line for line in par.read_text().splitlines()
                        if line.split() and line.split()[0] not in {"EPHVER", "NTOA", "CHI2R", "TRES"})
    model = get_model(io.StringIO(content), allow_tcb=True)
    # DMXR boundaries select site-MJD observations, not barycentric epochs.
    # PINT's generic TCB conversion shifts these narrow windows off their TOAs.
    for key, value in fields(content).items():
        if key.startswith(("DMXR1_", "DMXR2_")):
            getattr(model, key).value = value[0]
    # TPA equation 2 adds EQUAD after EFAC; PINT applies EFAC to both terms.
    # Translate the model parameter so its saved covariance uses the published convention.
    model.EQUAD1.quantity = model.EQUAD1.quantity / row["noise"]["efac"]
    if any(c.category == "pulsar_system" for c in model.components.values()):
        raise ValueError("Unexpected binary timing model")
    bind_precise_spin_phase(model)
    manifest = cal.read(mpta.RESOURCES / "metadata/resources.json")
    with ExitStack() as stack:
        deny = stack.enter_context(NetworkDeny())
        local = stack.enter_context(LocalPintRepository(mpta.RESOURCES, manifest))
        local.bind_science_resources()
        pint.observatory._bipm_clock_versions["bipm2019"] = ClockFile.read(
            data / "original/tai2tt_bipm2019.clk", format="tempo2")
        pint.observatory.Observatory.get("meerkat")._clock = [ClockFile.read(
            data / "original/mk2utc_observatory.clk", format="tempo2")]
        toas = get_TOAs(tim, model=model, ephem="DE440", planets=True, usepickle=False,
                       limits="error", include_bipm=True, bipm_version="BIPM2019")
        residual = Residuals(toas, model, track_mode="use_pulse_numbers", use_weighted_mean=False)
        values = residual.time_resids.to_value(u.s)
        times = np.asarray(model.get_barycentric_toas(toas).to_value(u.day), dtype=float)
        names = np.unique([f["name"] for f in toas.table["flags"]])
        design, columns, _ = model.designmatrix(toas)
        dm_columns = [i for i, name in enumerate(columns) if name.startswith("DMX_")]
        dm_membership = design[:, dm_columns] != 0
        if not dm_columns or not np.all(dm_membership.sum(axis=1) == 1) or not np.all(dm_membership.any(axis=0)):
            raise ValueError("Published epoch DM windows do not cover each TOA exactly once")
        baseline_columns = [i for i, n in enumerate(columns)
                            if n == "Offset" or n.startswith(("DM", "JUMP"))]
        baseline = design[:, baseline_columns]
        errors = toas.get_errors().to_value(u.s)
        n = row["noise"]
        ecorr_seconds = (toas.table["tdbld"].quantity * u.day).to_value(u.s)
        white = white_covariance(errors, ecorr_seconds, n)
        covariance = white + mpta.red_covariance(
            np.asarray(toas.table["tdbld"], dtype=float), n["red_amplitude"], n["red_gamma"],
            modes=n["red_modes"])
        # Independent unit/selector check against the installed PINT white-noise implementation.
        expected_white = (model.components["ScaleToaError"].sigma_scaled_cov_matrix(toas)
                          + model.components["EcorrNoise"].ecorr_cov_matrix(toas))
        np.testing.assert_allclose(white, expected_white,
                                   rtol=1e-10, atol=1e-24)
        if deny.attempts:
            raise RuntimeError("Unexpected scientific network access")
        (output / "timing-model.par").write_text(model.as_parfile())
    np.savez_compressed(output / "observed.npz", residuals=np.asarray(values, dtype=float))
    receipt = {"target": target, "toas": len(times), "epochs": len(names),
               "span_days": float(np.ptp(times)), "timing_names": columns, "noise": n,
               "pulse_connection": "Published TIM pulse numbers and full timing model; no nearest-pulse reassignment",
               "dispersion": "Published epoch DMX values retained and all free DMX columns projected",
               "profile_evolution": "Published six sub-band JUMP terms retained and fitted",
               "noise_model": "Published TPA fixed EFAC/EQUAD/ECORR and 100-mode red covariance; no red waveform subtracted",
               "white_covariance_verified_against_pint": True, "network_attempts": 0,
               "ecorr_epoch_convention": "One-second TDB buckets anchored at first TOA, at least two TOAs, matching PINT",
               "equad_translation": "PINT EQUAD = published EQUAD / EFAC; TPA equation 2",
               "dm_epoch_windows": "Original site-MJD boundaries preserved across TCB conversion; every TOA covered once",
               "active_dm_columns": len(dm_columns),
               "observed_sha256": cal.digest(output / "observed.npz"),
               "selection_sha256": cal.digest(data / "selection.json"), "code_sha256": cal.digest(__file__),
               "shared_adapter_sha256": cal.digest(mpta.__file__),
               "resources_sha256": cal.digest(mpta.RESOURCES / "metadata/resources.json")}
    profile = cal.create_profile(root / "profile", target,
                                 {"times": times, "covariance": covariance, "design": design,
                                  "baseline_design": baseline},
                                 {"timing_model": "TPA full timing model, free spin/astrometry/DMX/JUMPs",
                                  "noise_model": receipt["noise_model"], "preparation": receipt},
                                 {**selection["policy"], "seed": selection["policy"]["seed"] + row["batch_index"]},
                                 reference_epoch=float(model.PEPOCH.value))
    cal.write(output / "receipt.json", receipt)
    print(json.dumps({"target": target, "status": "PREPARED", "profile": str(profile)}), flush=True)


def calibrate(data):
    output = data / "preparation.json"
    if output.exists():
        raise FileExistsError("Completed preparation receipt already exists")
    results = []
    for target in cal.read(data / "selection.json")["selected"]:
        root = data / target
        result = cal.run(root / "profile/profile.json", data / "calibration-cache")
        profile, arrays = cal.load_profile(root / "profile/profile.json")
        # One noiseless orbit plus arbitrary timing nuisance checks separation on actual sampling.
        scanner = prepare_covariance_gls_scanner(arrays["covariance"], arrays["design"],
                                                arrays["times"], np.array([0.01]),
                                                profile["reference_epoch_mjd_tdb"])
        phase = 2 * np.pi * (arrays["times"] - profile["reference_epoch_mjd_tdb"]) / 100
        injected = 1e-3 * np.sin(phase) + arrays["baseline_design"] @ np.full(arrays["baseline_design"].shape[1], 1e-4)
        y = scanner.whiten_and_project(injected)
        fitted = scanner.template_gram_pseudoinverse[0] @ (scanner.projected_whitened_templates[:, 0].T @ y)
        np.testing.assert_allclose(fitted, [1e-3, 0], rtol=1e-7, atol=1e-10)
        results.append({"target": target, "calibration": result,
                        "profile_sha256": cal.digest(root / "profile/profile.json"),
                        "noiseless_injected_amplitude_us": 1000,
                        "recovered_amplitude_us": float(np.linalg.norm(fitted) * 1e6)})
        print(json.dumps(results[-1]), flush=True)
    cal.write(output, {"status": "PREPARED", "created_utc": mpta.now(), "results": results,
                       "selection_sha256": cal.digest(data / "selection.json"),
                       "observed_search_executed": False})


def freeze(data):
    preparation = cal.read(data / "preparation.json")
    assert preparation["status"] == "PREPARED" and not preparation["observed_search_executed"]
    assert preparation["selection_sha256"] == cal.digest(data / "selection.json")
    for row in preparation["results"]:
        root = data / row["target"]
        assert cal.digest(root / "profile/profile.json") == row["profile_sha256"]
        profile, _ = cal.load_profile(root / "profile/profile.json")
        cal.verify_cache(Path(row["calibration"]["path"]),
                         {"profile": profile, "implementation": cal.implementation()})
        receipt = cal.read(root / "prepared/receipt.json")
        assert receipt["active_dm_columns"] == receipt["epochs"]
        assert cal.digest(root / "prepared/observed.npz") == receipt["observed_sha256"]
        if (root / "run01").exists():
            raise FileExistsError("Selected observed destination already consumed")
    mpta.freeze(data)
    path = data / "execution-freeze.json"
    frozen = cal.read(path)
    frozen.update(tpa_adapter_sha256=cal.digest(__file__),
                  preparation_sha256=cal.digest(data / "preparation.json"),
                  preparation_receipts={r["target"]: cal.digest(data / r["target"] / "prepared/receipt.json")
                                        for r in preparation["results"]})
    cal.write(path, frozen)
    print("TPA FROZEN " + cal.digest(path), flush=True)


def run(data, target):
    frozen = cal.read(data / "execution-freeze.json")
    assert frozen["tpa_adapter_sha256"] == cal.digest(__file__)
    assert frozen["preparation_sha256"] == cal.digest(data / "preparation.json")
    assert frozen["preparation_receipts"][target] == cal.digest(data / target / "prepared/receipt.json")
    try:
        mpta.run(data, target)
    finally:
        selection = cal.read(data / "selection.json")
        completed = sum((data / t / "run01/result.json").exists() for t in selection["selected"])
        incomplete = sum((data / t / "run01").exists() for t in selection["selected"]) - completed
        queue = mpta.REPO / "docs/FUTURE_DATA_SOURCES.md"
        text = queue.read_text()
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("| 1 | MeerTime Thousand Pulsar Array |"):
                parts = line.split("|")
                parts[4] = (f" ACTIVE: {selection.get('total_eligible_targets', selection['eligible_targets'])} eligible, "
                            f"{completed + selection.get('previous_completed_count', 0)} searched, "
                            f"{incomplete} incomplete, {len(selection['selected']) - completed - incomplete} prepared, "
                            f"{selection['remaining_after_selection']} remaining ")
                lines[i] = "|".join(parts)
                break
        else:
            raise ValueError("TPA source queue row missing")
        queue.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "prepare", "calibrate", "freeze", "run"))
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--target")
    parser.add_argument("--previous-data", type=Path)
    parser.add_argument("--batch-size", type=int, default=25,
                        help="Maximum targets for a new inventory selection (default: 25)")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    if args.previous_data is not None:
        if args.command != "inventory":
            parser.error("--previous-data is only valid for inventory")
        inventory_next(args.data.resolve(), args.previous_data.resolve(), args.batch_size)
    elif args.command == "inventory":
        inventory(args.data.resolve(), args.batch_size)
    elif args.command in ("prepare", "run"):
        if not args.target:
            parser.error("--target is required")
        globals()[args.command](args.data.resolve(), args.target)
    else:
        globals()[args.command](args.data.resolve())
