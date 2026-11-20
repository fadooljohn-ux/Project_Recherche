"""Translate a released orbit written in tempo2's general `T2` model, or in `BT`, into a model the search supports.

`BINARY T2` is a container: the parameters inside are either the
small-eccentricity set (TASC, EPS1, EPS2) or the Keplerian set (T0, ECC, OM),
with or without Shapiro terms. The translation only renames the model; it
changes no parameter value:

    TASC, EPS1, EPS2            -> ELL1   (ELL1H if the Shapiro delay is given as H3)
    T0, ECC, OM                 -> DD     (DDH if the Shapiro delay is given as H3)
    BT (no Shapiro, no DR/DTH)  -> DD

Anything else is refused: annual-orbital parallax (KOM, KIN), a second orbit,
orbital-frequency derivatives, SHAPMAX, MTOT, or both parameter sets at once.
The result still has to pass the re-expression, Shapiro and preparation
checks. No timing package that implements T2 natively is installed, so the
translation is confirmed two ways: the timing library's own independent
guess of the model must agree (`confirm`), and the target's null fit and
orbit-shift checks at preparation must pass. It reads no observations.
"""
from __future__ import annotations

from decimal import Decimal, getcontext

SMALL = ("TASC", "EPS1", "EPS2")
KEPLER = ("T0", "OM")
ECCENTRICITY = ("ECC", "E")
REFUSED = ("KOM", "KIN", "SHAPMAX", "MTOT", "DR", "DTH", "A0", "B0", "FB1", "FB2", "FB3", "BPJEP_1", "A1_2", "PB_2",
           "T0_2", "ECC_2", "OM_2", "XOMDOT", "AFAC", "DAOP")
HARMONIC = ("H3", "H4", "STIG", "STIGMA", "VARSIGMA")
SOURCES = ("T2", "BT")
getcontext().prec = 40


def number(text):
    return float(text.upper().replace("D", "E"))


def active(fields, name):
    """Present with a non-zero value, or fitted."""
    if name not in fields:
        return False
    v = fields[name]
    return (len(v) > 1 and v[1] == "1") or (len(v) > 0 and number(v[0]) != 0.0)


def translate(text):
    """Return (par text with the BINARY line renamed, record). Raises ValueError for anything not covered."""
    lines = text.splitlines()
    fields = {}
    for line in lines:
        v = line.split()
        if v and not v[0].startswith("#"):
            fields.setdefault(v[0], v[1:])
    source = fields["BINARY"][0].upper()
    if source not in SOURCES:
        raise ValueError("Translation covers T2 and BT only: " + source)
    refused = [k for k in REFUSED if active(fields, k)]
    if refused:
        raise ValueError("Translation does not cover: " + " ".join(refused))
    small = all(k in fields for k in SMALL)
    kepler = all(k in fields for k in KEPLER) and any(k in fields for k in ECCENTRICITY)
    if small == kepler:
        raise ValueError("Orbit must carry exactly one of the small-eccentricity and Keplerian parameter sets")
    harmonic = [k for k in HARMONIC if active(fields, k)]
    classic = [k for k in ("M2", "SINI") if active(fields, k)]
    if harmonic and classic:
        raise ValueError("Shapiro delay given in both forms: " + " ".join(classic + harmonic))
    if source == "BT":
        if not kepler or harmonic or classic:
            raise ValueError("BT translation needs a Keplerian orbit without Shapiro terms")
        target = "DD"
    else:
        if harmonic and "H3" not in harmonic:
            raise ValueError("Orthometric Shapiro terms without H3")
        target = ("ELL1" if small else "DD") + ("H" if harmonic else "")
    out = []
    for line in lines:
        v = line.split()
        out.append("BINARY " + target if v and v[0] == "BINARY" else line)
    record = {"from": source, "to": target, "parameter_set": "small-eccentricity" if small else "Keplerian",
              "shapiro_form": "orthometric" if harmonic else ("mass and inclination" if classic else "none"),
              "rule": "Model renamed only; no parameter value changed"}
    return "\n".join(out) + "\n", record


def confirm(text, record):
    """The timing library's independent guess for the original text must include the translated model."""
    import io

    from pint.models.model_builder import guess_binary_model, parse_parfile

    guesses = guess_binary_model(parse_parfile(io.StringIO(text)))
    if record["to"] not in guesses:
        raise ValueError("Timing library does not allow %s for this par: %s" % (record["to"], guesses))
    return guesses


def recentre_orthometric(text):
    """Re-centre a tempo2 small-eccentricity orbit with H3 and STIG for a library that keeps every Shapiro harmonic.

    tempo2 (T2model.C / ELL1Hmodel.C, mode 1) applies only the third and higher harmonics of the Shapiro
    delay, -2 r [ln(1 + s^2 - 2 s sin P) + 2 s sin P - s^2 cos 2P] with r = H3 / s^3 and s = STIG; the first
    two harmonics are left in the fitted orbit. The pinned timing library applies the whole logarithm for
    H3 with STIGMA. The same arrival times are therefore described by

        A1' = A1 - 4 r s        EPS1' = (A1 EPS1 - 4 r s^2) / A1'        EPS2' = A1 EPS2 / A1'

    Returns (text, record), or (text, None) when the orbit is not of this kind (no STIG, or H4 given: the
    harmonic-sum form is the same in both packages).
    """
    lines = text.splitlines()
    fields = {}
    for line in lines:
        v = line.split()
        if v and not v[0].startswith("#"):
            fields.setdefault(v[0], v[1:])
    stig_name = "STIG" if "STIG" in fields else ("STIGMA" if "STIGMA" in fields else None)
    if (fields.get("BINARY", [""])[0].upper() != "ELL1H" or stig_name is None or not active(fields, stig_name)
            or active(fields, "H4") or not active(fields, "H3")):
        return text, None
    value = lambda name: Decimal(fields[name][0].upper().replace("D", "E"))
    a1, eps1, eps2, h3, stig = (value(k) for k in ("A1", "EPS1", "EPS2", "H3", stig_name))
    if not 0 < stig <= 1:
        raise ValueError("STIG outside (0, 1]")
    r = h3 / stig ** 3
    new_a1 = a1 - 4 * r * stig
    new = {"A1": new_a1, "EPS1": (a1 * eps1 - 4 * r * stig ** 2) / new_a1, "EPS2": a1 * eps2 / new_a1}
    out = []
    for line in lines:
        v = line.split()
        if v and v[0] in new:
            out.append(" ".join([v[0], str(new[v[0]])] + v[2:]))
        else:
            out.append(line)
    record = {"rule": "A1' = A1 - 4 r s; EPS1' = (A1 EPS1 - 4 r s^2) / A1'; EPS2' = A1 EPS2 / A1'; r = H3 / STIG^3",
              "reason": "tempo2 applies the third and higher Shapiro harmonics only; the timing library applies all",
              "released": {k: str(v) for k, v in (("A1", a1), ("EPS1", eps1), ("EPS2", eps2))},
              "recentred": {k: str(v) for k, v in new.items()}}
    return "\n".join(out) + "\n", record
