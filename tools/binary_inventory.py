"""Inventory of known binaries in timing releases on disk, classified against the binary search's orbit support.

Reads released par files only (timing models; no TOAs, no residuals) and, per
binary, reports the orbit model, what the current tools would need to take it
(native, small-eccentricity re-expression, Shapiro basis) or why they cannot,
and a rough outer-period range. A class here is a model-level screen: every
target must still pass the preparation checks, and each release needs its own
noise and clock adapter before anything can be prepared.
"""
import argparse
import json
from pathlib import Path

NATIVE = ("ELL1", "ELL1H")
REEXPRESSIBLE = ("DD", "DDH")
SHAPIRO = ("M2", "SINI", "H3", "H4", "STIG", "STIGMA")
# Terms no current treatment handles (orbital-frequency derivatives, annual-orbital parallax, second orbits).
UNSUPPORTED = ("KOM", "KIN", "SHAPMAX", "DR", "DTH", "A0", "B0", "GAMMA", "FB1", "FB2", "FB3", "A1_2", "PB_2",
               "T0_2", "BPJEP_1")
# Terms the small-eccentricity re-expression refuses (they are ordinary fitted columns in an ELL1-type model).
REFUSED_BY_REEXPRESSION = ("OMDOT", "PBDOT", "EDOT", "XPBDOT")
# Tempo2's general model and BT carry ELL1-type or DD-type parameters; they need a translation first.
TRANSLATED = ("T2", "BT")
MINIMUM_PERIOD_DAYS = 30.0
INNER_PERIOD_FACTOR = 10.0      # shortest outer period searched, in inner periods (as in the MeerKAT batches)


def fields(text):
    out = {}
    for line in text.splitlines():
        v = line.split()
        if v and not v[0].startswith("#") and v[0] not in out:
            out[v[0]] = v[1:]
    return out


def number(value):
    return float(value.upper().replace("D", "E"))


def fitted(values):
    return len(values) > 1 and values[1] == "1"


def classify(f, span_days=None):
    """Row for one par file's fields, or None if it has no BINARY line."""
    if "BINARY" not in f:
        return None
    model = f["BINARY"][0].upper()
    period = number(f["PB"][0]) if "PB" in f else (1 / number(f["FB0"][0]) / 86400 if "FB0" in f else None)
    if span_days is None and "START" in f and "FINISH" in f:
        span_days = number(f["FINISH"][0]) - number(f["START"][0])
    free_shapiro = [k for k in SHAPIRO if k in f and fitted(f[k])]
    present = lambda names: [k for k in names if k in f and (fitted(f[k]) or abs(number(f[k][0])) > 0)]
    extra = present(UNSUPPORTED)
    ecc = number(f["ECC"][0]) if "ECC" in f else (number(f["E"][0]) if "E" in f else None)
    needs, blocker = [], None
    kind = model
    if model in TRANSLATED:
        needs.append("model translation")
        kind = "ELL1" if "TASC" in f else "DD"
    orbit = ("TASC", "EPS1", "EPS2") if kind in NATIVE else ()
    unfitted = [k for k in ("A1",) + orbit if k not in f or not fitted(f[k])]
    if not any(k in f and fitted(f[k]) for k in ("PB", "FB0")):
        unfitted.insert(0, "PB")
    if kind in NATIVE + REEXPRESSIBLE and unfitted:
        blocker = "orbital parameters not fitted in the release: " + " ".join(unfitted)
    elif kind in NATIVE:
        pass
    elif kind in REEXPRESSIBLE:
        extra += present(REFUSED_BY_REEXPRESSION)
        if not all(k in f and fitted(f[k]) for k in ("T0", "OM")) or not any(k in f and fitted(f[k]) for k in ("ECC", "E")):
            blocker = "T0, OM or ECC not fitted"
        elif ecc is not None and ecc > 1e-3:
            blocker = "eccentric orbit (%.3g): re-expression does not apply; nonlinear orbit treatment needed" % ecc
        else:
            needs.append("re-expression")
    else:
        blocker = "orbit model %s not supported" % model
    if blocker is None and extra:
        blocker = "extra orbital terms: " + " ".join(extra)
    if blocker is None and free_shapiro:
        needs.append("Shapiro basis")
    low = high = None
    if period is not None and span_days:
        low, high = max(MINIMUM_PERIOD_DAYS, INNER_PERIOD_FACTOR * period), span_days / 2
        if blocker is None and low >= high:
            blocker = "no outer-period range (inner period %.1f d, span %.1f yr)" % (period, span_days / 365.25)
    return {"binary_model": model, "inner_period_days": period, "eccentricity": ecc, "span_days": span_days,
            "free_shapiro": free_shapiro, "extra_orbital_terms": extra,
            "parameter_form": kind,
            "class": "BLOCKED" if blocker else ("NATIVE" if not needs else "NEEDS " + " + ".join(needs).upper()),
            "blocker": blocker, "rough_outer_period_days": None if blocker or low is None else [low, high]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True,
                        help='{"data": root, "releases": {name: {"glob": pattern, "name": regex group or null}}, ...}')
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    import re
    config = json.loads(args.config.read_text())
    data = (args.config.parent / config["data"]).resolve()
    searched = set(config.get("searched", []))
    rows = []
    for release, spec in config["releases"].items():
        if "parameter_inventory" in spec:      # saved par fields (NANOGrav 15-year)
            items = [(r["target"], r["fields"]) for r in json.loads((data / spec["parameter_inventory"]).read_text())]
        else:
            items = [(re.search(spec["name"], p.name).group(1), fields(p.read_text(errors="replace")))
                     for p in sorted(data.glob(spec["glob"])) if re.search(spec["name"], p.name)]
        for name, f in items:
            name = config.get("aliases", {}).get(name, name)
            row = classify(f, spec.get("span_days", {}).get(name))
            if row:
                rows.append({"release": release, "target": name, "searched_before_in_any_data": name in searched, **row})
    args.out.write_text(json.dumps({"status": "BINARY_INVENTORY_COMPLETE", "observations_read": False,
                                    "rule": __doc__.split("\n\n")[1], "rows": rows}, indent=1) + "\n")
    for release in config["releases"]:
        mine = [r for r in rows if r["release"] == release]
        count = {}
        for r in mine:
            count[r["class"]] = count.get(r["class"], 0) + 1
        print(release, len(mine), "binaries:", ", ".join(f"{k} {v}" for k, v in sorted(count.items())))


if __name__ == "__main__":
    main()
