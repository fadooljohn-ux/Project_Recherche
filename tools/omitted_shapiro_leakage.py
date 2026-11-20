"""Leakage of an omitted Shapiro delay into the outer-period search, for prepared NANOGrav binaries.

Some released models carry no Shapiro-delay terms. The delay is still there
in the data; the released orbit has absorbed its first two harmonics and the
rest is left over. This tool builds the Shapiro delay the companion would
produce for a grid of physically consistent companion masses and
inclinations (from the binary mass function), on the target's real sampling,
projects it exactly as the search does and scans it over the whole search
grid. The largest statistic it can produce is the deterministic
contamination.

Synthetic delays only: no observed residuals are loaded, no observed
periodogram is computed, and nothing is calibrated.
"""
from __future__ import annotations

import argparse
import json
from contextlib import ExitStack
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

import target_calibration as cal

T_SUN = 4.925490947e-6             # GM_sun / c^3 in seconds
INCLINATIONS = (30.0, 60.0, 75.0, 85.0, 88.0)
PULSAR_MASSES = (1.4, 2.0)
DECISION_INCLINATION = 85.0        # scenarios up to here decide; steeper ones are reported as stress cases
LIMIT = 0.1                        # largest allowed synthetic statistic (a chi-square difference)
SHAPIRO_TERMS = ("M2", "SINI", "H3", "H4", "STIGMA")


def mass_function(a1_light_seconds, period_days):
    """Binary mass function in solar masses."""
    return 4 * np.pi ** 2 * a1_light_seconds ** 3 / (T_SUN * (period_days * 86400.0) ** 2)


def companion_mass(function, pulsar_mass, inclination_degrees):
    """Companion mass (solar) satisfying the mass function at this pulsar mass and inclination."""
    s = np.sin(np.deg2rad(inclination_degrees))
    return float(brentq(lambda m: (m * s) ** 3 / (pulsar_mass + m) ** 2 - function, 1e-6, 50.0))


def shapiro_delay(mass, inclination_degrees, phase):
    """Shapiro delay in seconds at orbital phase measured from the ascending node."""
    return -2 * T_SUN * mass * np.log1p(-np.sin(np.deg2rad(inclination_degrees)) * np.sin(phase))


def scenarios(function):
    return [{"pulsar_mass_solar": mp, "inclination_degrees": inc, "companion_mass_solar": companion_mass(function, mp, inc)}
            for mp in PULSAR_MASSES for inc in INCLINATIONS]


def assess_target(arrays, profile, phase, function):
    """Rows of synthetic contamination for one prepared target."""
    from pulsar_pilot.pilot1_runtime import build_search_frequency_grid, prepare_covariance_gls_scanner

    policy = profile["policy"]
    frequencies, grid = build_search_frequency_grid(arrays["times"], policy["minimum_period_days"],
                                                    policy["maximum_period_days"], policy["oversampling"])
    scanner = prepare_covariance_gls_scanner(arrays["covariance"], arrays["design"], arrays["times"], frequencies,
                                             profile["reference_epoch_mjd_tdb"])
    rows = []
    for case in scenarios(function):
        delay = shapiro_delay(case["companion_mass_solar"], case["inclination_degrees"], phase)
        synthetic = np.zeros(len(arrays["covariance"]))
        synthetic[:len(phase)] = delay
        scan = scanner.scan(synthetic)
        projected = scanner.whiten_and_project(synthetic)
        bound = float(projected @ projected)
        if scan["trigger_statistic"] > bound + 1e-8:
            raise ValueError("Synthetic power exceeds its projection bound")
        rows.append({**case, "raw_delay_peak_to_peak_us": float(np.ptp(delay) * 1e6),
                     "projected_whitened_norm_squared": bound,
                     "maximum_synthetic_delta_chi2": float(scan["trigger_statistic"]),
                     "synthetic_peak_period_days": float(scan["peak_period_days"]),
                     "synthetic_peak_amplitude_us": float(scan["amplitude_us"])})
    deciding = max(r["maximum_synthetic_delta_chi2"] for r in rows if r["inclination_degrees"] <= DECISION_INCLINATION)
    return {"grid": grid, "scenarios": rows, "largest_deciding_delta_chi2": deciding,
            "largest_delta_chi2_any_scenario": max(r["maximum_synthetic_delta_chi2"] for r in rows),
            "status": "LEAKAGE_NEGLIGIBLE" if deciding <= LIMIT else "LEAKAGE_NOT_NEGLIGIBLE"}


def orbital_phase(data, target, receipt, times):
    """Orbital phase from the ascending node at each TOA, from the searched model (reads arrival times, no residuals)."""
    import astropy.units as u
    from pint.models import get_model_and_toas

    import binary_wideband as wideband
    from pulsar_pilot.pilot2_offline_resources import NetworkDeny

    root = data / target
    par = root / "prepared/reexpressed.par"
    if not par.exists():
        par = root / "original" / (target + ".par")
    with ExitStack() as stack:
        deny = stack.enter_context(NetworkDeny())
        local = stack.enter_context(wideband.BinaryResources(data))
        local.bind_science_resources()
        model, toas = get_model_and_toas(str(par), str(root / "original" / (target + ".tim")), ephem="DE440",
                                         include_bipm=True, bipm_version="BIPM2019", planets=True, usepickle=False,
                                         limits="error")
        component, = [c for c in model.components.values() if c.category == "pulsar_system"]
        if component.binary_model_name != receipt["searched_binary_model"] or not component.binary_model_name.startswith("ELL1"):
            raise ValueError("Phase from the ascending node needs the searched ELL1-type model")
        if any(getattr(model, p, None) is not None and getattr(model, p).value not in (None, 0) for p in SHAPIRO_TERMS):
            raise ValueError("Model carries Shapiro terms; this assessment is for omitted ones")
        if not np.array_equal(np.asarray(toas.table["tdbld"].data, float), times):
            raise ValueError("Arrival times differ from the prepared profile")
        model.delay(toas)
        phase = np.asarray(component.binary_instance.Phi().to_value(u.rad), float)
        if deny.attempts:
            raise RuntimeError("Scientific network access attempted")
        return phase, float(model.A1.value), float(model.PB.value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="a prepared ng15-binary root")
    parser.add_argument("--targets", nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    data = args.data.resolve()
    results = []
    for target in args.targets:
        root = data / target
        receipt = cal.read(root / "prepared/receipt.json")
        profile, arrays = cal.load_profile(root / "profile/profile.json")
        if profile["provenance"]["preparation_receipt_sha256"] != cal.digest(root / "prepared/receipt.json"):
            raise ValueError("Receipt binding differs: " + target)
        phase, a1, period = orbital_phase(data, target, receipt, arrays["times"])
        function = mass_function(a1, period)
        result = assess_target(arrays, profile, phase, function)
        results.append({"target": target, "mass_function_solar": function, "inner_period_days": period,
                        "profile_sha256": cal.digest(root / "profile/profile.json"), **result})
        print("%-11s %-22s deciding %.4f  any %.4f" % (
            target, result["status"], result["largest_deciding_delta_chi2"],
            result["largest_delta_chi2_any_scenario"]), flush=True)
    cal.write(args.out, {
        "status": "LEAKAGE_ASSESSMENT_COMPLETE", "data": str(data), "selection_sha256": cal.digest(data / "selection.json"),
        "code_sha256": cal.digest(__file__), "limit_delta_chi2": LIMIT, "deciding_inclination_degrees": DECISION_INCLINATION,
        "inclinations_degrees": list(INCLINATIONS), "pulsar_masses_solar": list(PULSAR_MASSES),
        "rule": "Companion mass from the mass function at each pulsar mass and inclination; Shapiro delay on the real "
                "sampling, projected with every search nuisance column and scanned over the full search grid; "
                "negligible when the largest statistic for inclinations up to the deciding one is within the limit",
        "limitations": "A grid, not a posterior or a continuous bound; phase and nuisance design fixed at the released "
                       "model; a synthetic statistic also has a cross term with noise or a real signal",
        "observed_residuals_loaded": False, "calibration_executed": False, "observed_search_executed": False,
        "results": results})


if __name__ == "__main__":
    main()
