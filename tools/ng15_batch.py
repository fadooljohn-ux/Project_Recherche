"""NANOGrav 15-year wideband intake and frozen single-pulsar searches."""

import argparse
import hashlib
import json
import re
import tarfile
from contextlib import ExitStack
from pathlib import Path

import mpta_batch as mpta
import numpy as np
import target_calibration as cal

from pulsar_pilot.pilot1_runtime import prepare_covariance_gls_scanner
from pulsar_pilot.pilot2_offline_resources import LocalPintRepository, NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

TARGETS = ("J1911+1347", "J0645+5158", "J1923+2515", "J1944+0907", "J0340+4130",
           "J1453+1902", "J0030+0451", "J0931-1902", "J1730-2304", "J1744-1134",
           "J1747-4036", "J1832-0836", "J1843-1113", "J2010-1323", "J2124-3358", "J2322+2057")
RELEASE = "NANOGrav15yr_PulsarTiming_v2.1.0.tar.gz"
POLICY = {**cal.DEFAULT_POLICY, "minimum_period_days": 30.0, "maximum_period_days": 2000.0,
          "search_count": 16, "seed": 2026092100}


def inventory(data):
    destination = data / "selection.json"
    if destination.exists():
        raise FileExistsError("Selection already recorded")
    archive_path = data / "original" / RELEASE
    with archive_path.open("rb") as handle:
        assert hashlib.file_digest(handle, "md5").hexdigest() == "557d42dd8486a5f8272d90dec9b228a8"
    baseline = cal.read(data / "baseline.json")
    master = mpta.REPO / "outputs/recherche-master-20260908/Project-Recherche-Master.xlsx"
    assert cal.digest(master) == baseline["master_sha256"]
    rows, inventory_rows = [], []
    members = {}
    with tarfile.open(archive_path, "r|gz") as archive:
        for member in archive:
            name = member.name
            if member.isfile() and ("/wideband/par/" in name or "/wideband/tim/" in name
                                    or "/clock/" in name or "readme" in Path(name).name.lower()):
                members[name] = archive.extractfile(member).read()
    par_names = sorted(n for n in members if "/wideband/par/" in n and n.endswith(".wb.par") and "_PINT_" in n
                       and re.fullmatch(r"[JB]\d{4}[+\-]\d{2,4}", Path(n).name.split("_PINT_")[0]))
    if len(par_names) != 68:
        raise ValueError(f"Expected 68 PINT wideband models; found {len(par_names)}")
    for name in par_names:
        par = members[name]
        fields = {v[0]: v[1:] for line in par.decode().splitlines()
                  if (v := line.split()) and not v[0].startswith("#")}
        label = Path(name).name.split("_PINT_")[0]
        target = {"B1937+21": "J1939+2134"}.get(label, label)
        candidates = [n for n in members if "/wideband/tim/" in n
                      and Path(n).name.startswith(label + "_") and n.endswith(".wb.tim")]
        if len(candidates) != 1:
            raise ValueError(f"Ambiguous wideband TIM for {label}: {candidates}")
        tim = members[candidates[0]]
        reasons = (["known_binary"] if "BINARY" in fields or target == "J1024-0719" else [])
        if target == "J1939+2134":
            reasons.append("same_release_already_searched")
            prior = mpta.RESOURCES / "controlled/nanograv15yr-v2.1.0/wideband"
            assert par == (prior / "par" / Path(name).name).read_bytes()
            assert tim == (prior / "tim" / Path(candidates[0]).name).read_bytes()
        selected = target in TARGETS
        if selected and reasons:
            raise ValueError(f"Selected target is ineligible: {target}, {reasons}")
        inventory_rows.append({"target": target, "release_name": label, "selected": selected,
                               "exclusion_reasons": reasons, "par_member": name,
                               "tim_member": candidates[0], "par_sha256": hashlib.sha256(par).hexdigest(),
                               "tim_sha256": hashlib.sha256(tim).hexdigest()})
        if not selected:
            continue
        root = data / target / "original"
        root.mkdir(parents=True, exist_ok=False)
        (root / (target + ".par")).write_bytes(par)
        (root / (target + ".tim")).write_bytes(tim)
        obs = [line.split() for line in tim.decode().splitlines()
               if line.split() and line.split()[0] not in ("C", "#", "FORMAT", "MODE")]
        mjds = [float(v[2]) for v in obs]
        row = {**inventory_rows[-1], "batch_index": TARGETS.index(target), "aliases": [],
               "toas": len(obs), "epochs": len(set(int(m) for m in mjds)),
               "span_days": max(mjds) - min(mjds), "master_overlap": baseline["master_rows"].get(target),
               "prior_search_membership": {k: None for k in ("JBO800", "NANOGrav11", "EPTA_DR2")}}
        rows.append(row)
    # Keep release documentation and clocks with their internal paths, without extracting links.
    for name, member in members.items():
        if "clock" in name.lower() or "readme" in Path(name).name.lower():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Invalid archive member")
            output = data / "release-support" / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(member)
    assert {r["target"] for r in rows} == set(TARGETS)
    assert sum(not r["exclusion_reasons"] for r in inventory_rows) == 16
    cal.write(data / "release-inventory.json", inventory_rows)
    record = {"created_utc": mpta.now(), "dataset": "NANOGrav 15-year v2.1.0 wideband; DOI 10.5281/zenodo.16051178",
              "selected": list(TARGETS), "rows": sorted(rows, key=lambda r: r["batch_index"]),
              "policy": POLICY, "maximum_period_rule": "min(2000 days, prepared TDB span / 2)",
              "eligible_targets": 16, "remaining_after_selection": 0,
              "master_overlaps": sum(bool(r["master_overlap"]) for r in rows),
              "master_workbook_sha256": baseline["master_sha256"],
              "observed_periodograms_inspected": False,
              "source_hashes": {str(archive_path): cal.digest(archive_path),
                                str(data / "release-inventory.json"): cal.digest(data / "release-inventory.json")}}
    cal.write(destination, record)
    print(json.dumps({"status": "SELECTED", "targets": record["selected"], "overlaps": record["master_overlaps"]}), flush=True)


def prepare(data, target):
    import pint.logging
    from pint.fitter import WidebandTOAFitter
    from pint.models import get_model_and_toas
    from pint.residuals import WidebandTOAResiduals

    selection = cal.read(data / "selection.json")
    row = next(r for r in selection["rows"] if r["target"] == target)
    root = data / target
    output = root / "prepared"
    output.mkdir(exist_ok=False)
    pint.logging.setup(level="INFO", sink=output / "pint.log", removeprior=True)
    par, tim = (root / "original" / (target + suffix) for suffix in (".par", ".tim"))
    assert cal.digest(par) == row["par_sha256"] and cal.digest(tim) == row["tim_sha256"]
    manifest = cal.read(mpta.RESOURCES / "metadata/resources.json")
    with ExitStack() as stack:
        deny = stack.enter_context(NetworkDeny())
        local = stack.enter_context(LocalPintRepository(mpta.RESOURCES, manifest))
        local.bind_science_resources()
        model, toas = get_model_and_toas(par, tim, ephem="DE440", include_bipm=True,
                                        bipm_version="BIPM2019", planets=True, usepickle=False, limits="error")
        if any(c.category == "pulsar_system" for c in model.components.values()):
            raise ValueError("Unexpected binary model")
        bind_precise_spin_phase(model)
        fitter = WidebandTOAFitter(toas, model)
        matrix = fitter.get_designmatrix()
        names = matrix.get_label_names(axis=1)
        baseline = [i for i, n in enumerate(names) if n.lower().startswith(("offset", "dm", "jump"))]
        if not baseline:
            raise ValueError("Dispersion and instrumental nuisance columns missing")
        covariance = fitter.get_noise_covariancematrix().matrix
        residuals = WidebandTOAResiduals(toas, model).calc_wideband_resids()
        times = np.asarray(toas.table["tdbld"].data, dtype=float)
        if len(residuals) != 2 * len(times) or matrix.matrix.shape[0] != len(residuals):
            raise ValueError("Wideband TOA/DM row layout differs from expected paired data")
        if deny.attempts:
            raise RuntimeError("Unexpected scientific network access")
        (output / "timing-model.par").write_text(model.as_parfile())
        model_components = list(model.components)
    np.savez_compressed(output / "observed.npz", residuals=np.asarray(residuals, dtype=float))
    span = float(np.ptp(times))
    policy = {**selection["policy"], "maximum_period_days": min(2000.0, span / 2),
              "seed": selection["policy"]["seed"] + row["batch_index"]}
    receipt = {"target": target, "toas": len(times), "epochs": len(set(np.floor(times).astype(int))),
               "span_days": span, "auxiliary_dm_measurements": len(residuals) - len(times),
               "timing_names": names, "model_components": model_components, "policy": policy,
               "noise_model": "Fixed full covariance from released PINT wideband model; no noise waveform subtracted",
               "dispersion": "Joint TOA seconds and DM pc/cm^3; free released timing/DM/instrument columns projected",
               "time_basis": "PINT tdbld, matching qualified B1937 wideband runtime",
               "epoch_definition": "Distinct integer TDB MJD days; not claimed independent observations",
               "network_attempts": 0, "observed_sha256": cal.digest(output / "observed.npz"),
               "selection_sha256": cal.digest(data / "selection.json"),
               "code_sha256": cal.digest(__file__), "shared_adapter_sha256": cal.digest(mpta.__file__),
               "resources_sha256": cal.digest(mpta.RESOURCES / "metadata/resources.json")}
    profile = cal.create_profile(root / "profile", target,
                                 {"times": times, "covariance": covariance, "design": matrix.matrix,
                                  "baseline_design": matrix.matrix[:, baseline]},
                                 {"timing_model": "Released NG15 wideband single-pulsar timing model",
                                  "noise_model": receipt["noise_model"], "preparation": receipt},
                                 policy, reference_epoch=float(model.PEPOCH.value))
    cal.write(output / "receipt.json", receipt)
    print(json.dumps({"target": target, "status": "PREPARED", "toas": len(times), "profile": str(profile)}), flush=True)


def calibrate(data):
    output = data / "preparation.json"
    if output.exists():
        raise FileExistsError("Preparation already complete")
    results = []
    for target in cal.read(data / "selection.json")["selected"]:
        root = data / target
        result = cal.run(root / "profile/profile.json", data / "calibration-cache")
        profile, arrays = cal.load_profile(root / "profile/profile.json")
        scanner = prepare_covariance_gls_scanner(arrays["covariance"], arrays["design"], arrays["times"],
                                                np.array([0.01]), profile["reference_epoch_mjd_tdb"])
        template = mpta.circular_template(arrays["times"], profile["reference_epoch_mjd_tdb"],
                                           0.01, len(arrays["covariance"]))
        injected = template[:, 0] * 1e-3 + arrays["baseline_design"] @ np.full(arrays["baseline_design"].shape[1], 1e-4)
        y = scanner.whiten_and_project(injected)
        fitted = scanner.template_gram_pseudoinverse[0] @ (scanner.projected_whitened_templates[:, 0].T @ y)
        np.testing.assert_allclose(fitted, [1e-3, 0], rtol=1e-7, atol=1e-10)
        results.append({"target": target, "calibration": result,
                        "profile_sha256": cal.digest(root / "profile/profile.json"),
                        "noiseless_injected_amplitude_us": 1000,
                        "recovered_amplitude_us": float(np.linalg.norm(fitted) * 1e6)})
        print(json.dumps(results[-1]), flush=True)
    cal.write(output, {"status": "PREPARED", "created_utc": mpta.now(), "results": results,
                       "selection_sha256": cal.digest(data / "selection.json"), "observed_search_executed": False})


def freeze(data):
    preparation = cal.read(data / "preparation.json")
    assert preparation["status"] == "PREPARED" and not preparation["observed_search_executed"]
    assert preparation["selection_sha256"] == cal.digest(data / "selection.json")
    for row in preparation["results"]:
        root = data / row["target"]
        assert cal.digest(root / "profile/profile.json") == row["profile_sha256"]
        receipt = cal.read(root / "prepared/receipt.json")
        assert receipt["code_sha256"] == cal.digest(__file__)
        assert receipt["shared_adapter_sha256"] == cal.digest(mpta.__file__)
        assert cal.digest(root / "prepared/observed.npz") == receipt["observed_sha256"]
        if (root / "run01").exists():
            raise FileExistsError("Observed destination already consumed")
    mpta.freeze(data)
    path = data / "execution-freeze.json"
    frozen = cal.read(path)
    frozen.update(ng15_adapter_sha256=cal.digest(__file__),
                  search="One circular grid per target; 30 to min(2000, span/2) days; fixed published noise; no period seeds",
                  preparation_sha256=cal.digest(data / "preparation.json"),
                  preparation_receipts={r["target"]: cal.digest(data / r["target"] / "prepared/receipt.json")
                                        for r in preparation["results"]})
    cal.write(path, frozen)
    print("NG15 FROZEN " + cal.digest(path), flush=True)


def run(data, target):
    frozen = cal.read(data / "execution-freeze.json")
    assert frozen["ng15_adapter_sha256"] == cal.digest(__file__)
    assert frozen["preparation_sha256"] == cal.digest(data / "preparation.json")
    assert frozen["preparation_receipts"][target] == cal.digest(data / target / "prepared/receipt.json")
    mpta.run(data, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "prepare", "calibrate", "freeze", "run"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--target", choices=TARGETS)
    args = parser.parse_args()
    if args.command in ("prepare", "run"):
        if not args.target:
            parser.error("--target is required")
        globals()[args.command](args.data.resolve(), args.target)
    else:
        globals()[args.command](args.data.resolve())
