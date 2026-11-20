"""Re-express a nearly circular DD/DDH orbit in the small-eccentricity (ELL1/ELL1H) form.

A nearly circular orbit written with a periastron time T0 and angle OM has
those two almost perfectly degenerate, so the search's linear treatment of the
orbit fails its local-linearity check. The same orbit written with the time of
ascending node and the two Laplace-Lagrange parameters

    TASC = T0 - (OM / 360) PB       EPS1 = ECC sin OM       EPS2 = ECC cos OM

is linear in every parameter. This module makes that change of variables in the
released par text and provides the check that the re-expressed model predicts
the same arrival times as the released one. It reads no observations.
"""
from __future__ import annotations

import math
from decimal import Decimal, getcontext

import numpy as np
from scipy.linalg import cholesky, solve_triangular

getcontext().prec = 40
MODELS = {"DD": "ELL1", "DDH": "ELL1H"}
REPLACED = ("T0", "OM", "ECC", "E")
CARRIED = ("PB", "A1", "XDOT", "A1DOT", "M2", "SINI", "H3", "H4", "STIG", "STIGMA")
DERIVED = ("TASC", "EPS1", "EPS2")
EQUIVALENCE_LIMIT = 0.1      # TOA sigma; the same bound as the local-linearity check
SECONDS_PER_DAY = Decimal(86400)


def number(text):
    return Decimal(text.upper().replace("D", "E"))


def parse(line):
    """(value, fitted, uncertainty) of a par line; tempo2 allows the flag to be omitted."""
    v = line.split()
    value = number(v[1])
    if len(v) == 2:
        return value, False, None
    if v[2] in ("0", "1"):
        return value, v[2] == "1", number(v[3]) if len(v) > 3 else None
    return value, False, number(v[2])


def convert(text):
    """Return the par text in ELL1/ELL1H form and a record of the change. Refuses anything it does not map."""
    lines = [line for line in text.splitlines() if line.split()]
    fields = {line.split()[0]: line for line in lines}
    source = fields["BINARY"].split()[1]
    if source not in MODELS:
        raise ValueError("Re-expression supports DD and DDH only: " + source)
    orbital = {"OMDOT", "PBDOT", "EDOT", "GAMMA", "DR", "DTH", "A0", "B0", "KOM", "KIN", "SHAPMAX", "XPBDOT",
               "EPS1DOT", "EPS2DOT", "TASC", "EPS1", "EPS2"} | {k for k in fields if k.startswith("FB")}
    unmapped = sorted(orbital & set(fields))
    if unmapped:
        raise ValueError("Re-expression does not map: " + " ".join(unmapped))
    ecc_name = "ECC" if "ECC" in fields else "E"
    (pb, _, _), (t0, t0_fit, _) = parse(fields["PB"]), parse(fields["T0"])
    (om, om_fit, om_err), (ecc, ecc_fit, ecc_err) = parse(fields["OM"]), parse(fields[ecc_name])
    if not (t0_fit and om_fit and ecc_fit):
        raise ValueError("Re-expression needs T0, OM and ECC all fitted in the release")
    if not 0 <= ecc < 1:
        raise ValueError("Eccentricity outside [0, 1)")
    turn = (om % 360) / 360
    tasc = t0 - turn * pb
    angle = float(turn) * 2 * math.pi
    e, sin, cos = float(ecc), math.sin(angle), math.cos(angle)
    # First-order propagation, T0 excluded: the released T0 and OM uncertainties are almost fully
    # correlated, so TASC carries no released uncertainty and is given the search's own (see prepare).
    se = float(ecc_err) if ecc_err else 0.0
    so = math.radians(float(om_err)) if om_err else 0.0
    eps = {"EPS1": (e * sin, math.hypot(sin * se, e * cos * so)), "EPS2": (e * cos, math.hypot(cos * se, e * sin * so))}
    new = [f"TASC {tasc} 1"] + [f"{k} {v!r} 1 {s!r}" for k, (v, s) in eps.items()]
    out, placed = [], False
    for line in lines:
        key = line.split()[0]
        if key == "BINARY":
            out.append("BINARY " + MODELS[source])
        elif key in REPLACED:
            if not placed:
                out.extend(new)
                placed = True
        elif key == "A1" and ("XDOT" in fields or "A1DOT" in fields):
            # The projected semi-major axis is referred to TASC instead of T0.
            rate = parse(fields.get("XDOT", fields.get("A1DOT")))[0]
            if abs(rate) > Decimal("1e-7"):      # tempo convention: units of 1e-12
                rate *= Decimal("1e-12")
            a1, fit, err = parse(line)
            a1 += rate * (tasc - t0) * SECONDS_PER_DAY
            out.append(f"A1 {a1} {int(fit)}" + (f" {err}" if err is not None else ""))
        else:
            out.append(line)
    record = {"from": source, "to": MODELS[source], "replaced": [k for k in REPLACED if k in fields],
              "derived": list(DERIVED), "tasc_mjd": str(tasc), "eps1": eps["EPS1"][0], "eps2": eps["EPS2"][0],
              "eccentricity": e,
              "relations": "TASC = T0 - (OM mod 360)/360 * PB; EPS1 = ECC sin OM; EPS2 = ECC cos OM; "
                           "A1 referred to TASC when XDOT is present",
              "uncertainties": "EPS1, EPS2 by first-order propagation of the released ECC and OM uncertainties; "
                               "TASC has no released uncertainty and takes the uncertainty under the search covariance"}
    return "\n".join(out) + "\n", record


def own_uncertainty(design, names, covariance, wanted):
    """Uncertainty of the named design columns under the search covariance."""
    lower = cholesky(covariance, lower=True)
    whitened = solve_triangular(lower, design, lower=True)
    norm = np.linalg.norm(whitened, axis=0)
    normalized = whitened / norm
    own = np.sqrt(np.diag(np.linalg.inv(normalized.T @ normalized))) / norm
    return {name: float(own[names.index(name)]) for name in wanted}


def equivalence(released_delay, reexpressed_delay, design, covariance):
    """Largest difference between the two models' arrival times, in TOA sigma, after the projection the search applies."""
    difference = np.asarray(reexpressed_delay - released_delay, float)
    lower = cholesky(covariance, lower=True)
    whitened = solve_triangular(lower, design, lower=True)
    normalized = whitened / np.linalg.norm(whitened, axis=0)
    y = solve_triangular(lower, difference, lower=True)
    remainder = y - normalized @ np.linalg.lstsq(normalized, y, rcond=1e-12)[0]
    left = lower @ remainder
    sigma = np.sqrt(np.diag(covariance))
    return {"maximum_difference_seconds_before_projection": float(np.max(abs(difference - difference.mean()))),
            "maximum_difference_seconds_after_projection": float(np.max(abs(left))),
            "maximum_difference_in_TOA_sigma": float(np.max(abs(left) / sigma)), "limit_in_TOA_sigma": EQUIVALENCE_LIMIT}
