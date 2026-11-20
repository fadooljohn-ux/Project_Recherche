"""Small-eccentricity re-expression of DD/DDH orbits, on simulated orbits only (no observations read)."""
import io
import sys
from pathlib import Path

import astropy.units as u
import numpy as np
import pytest
from pint.models import get_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import orbit_reexpress as reexpress

PAR = """PSR J0000+0000
F0 100
PEPOCH 56000
RAJ 00:00:00
DECJ 00:00:00
BINARY {model}
PB 11.050798515160829386 1 2e-10
T0 56030.849202961685716 1 0.047
A1 9.9388652801142905544 1 1e-6
OM {om} 1 1.5
ECC {ecc} 1 3.7e-8
{extra}"""
TIMES = np.sort(np.random.default_rng(7).uniform(58500, 60200, 2000)).astype(np.longdouble)


def par(model="DD", om="117.91878300574781382", ecc="7.15e-07", extra="XDOT -1.67e-14 1 1.3e-15\n"):
    return PAR.format(model=model, om=om, ecc=ecc, extra=extra)


def delay(text, times=TIMES):
    """Binary delay of the par's orbit at barycentric times, from the timing library's own orbit code."""
    model = get_model(io.StringIO(text))
    component, = [c for c in model.components.values() if c.category == "pulsar_system"]
    binary = component.binary_instance
    updates = {"barycentric_toa": times * u.day}
    for name in binary.binary_params:
        parameter = getattr(model, name, None)
        if parameter is not None and parameter.value is not None and parameter.units is not None:
            updates[name] = parameter.value * parameter.units
    binary.update_input(**updates)
    return np.asarray(binary.binary_delay().to_value(u.s), np.longdouble), model


def compare(text):
    """Equivalence of released and re-expressed delays under white 100 ns noise and the re-expressed orbit's own columns."""
    new, record = reexpress.convert(text)
    (released, _), (converted, model) = delay(text), delay(new)
    component, = [c for c in model.components.values() if c.category == "pulsar_system"]
    binary = component.binary_instance
    columns = [np.ones(len(TIMES)), np.asarray(TIMES - 59350, float)]
    columns += [np.asarray(binary.d_binarydelay_d_par(p).value, float) for p in ("PB", "A1", "TASC", "EPS1", "EPS2")]
    covariance = np.eye(len(TIMES)) * 1e-14
    return reexpress.equivalence(released, converted, np.column_stack(columns), covariance), record, new


@pytest.mark.parametrize("ecc", ["7.15e-07", "2.2e-05", "1.3e-04"])
@pytest.mark.parametrize("om", ["117.91878300574781382", "349.17", "-213019.78454079983148"])
def test_reexpressed_orbit_predicts_the_same_arrival_times(ecc, om):
    result, record, _ = compare(par(om=om, ecc=ecc))
    assert result["maximum_difference_in_TOA_sigma"] < 0.01
    assert record["from"] == "DD" and record["to"] == "ELL1"
    assert abs(np.hypot(record["eps1"], record["eps2"]) - float(ecc)) < 1e-18


def test_equivalence_check_catches_an_orbit_that_is_not_nearly_circular():
    result, _, _ = compare(par(ecc="0.02"))
    assert result["maximum_difference_in_TOA_sigma"] > reexpress.EQUIVALENCE_LIMIT


def test_ascending_node_and_semi_major_axis_follow_the_stated_relations():
    new, record = reexpress.convert(par())
    fields = {v[0]: v[1:] for line in new.splitlines() if (v := line.split())}
    assert "T0" not in fields and "OM" not in fields and "ECC" not in fields
    expected = 56030.849202961685716 - 117.91878300574781382 / 360 * 11.050798515160829386
    assert abs(float(fields["TASC"][0]) - expected) < 1e-9 and fields["TASC"] == [fields["TASC"][0], "1"]
    shift = -1.67e-14 * (float(fields["TASC"][0]) - 56030.849202961685716) * 86400
    assert abs(float(fields["A1"][0]) - 9.9388652801142905544 - shift) < 1e-15
    assert fields["PB"] == ["11.050798515160829386", "1", "2e-10"]
    assert float(fields["EPS1"][2]) > 0 and float(fields["EPS2"][2]) > 0


def test_orthometric_shapiro_parameters_are_carried_unchanged():
    new, record = reexpress.convert(par(model="DDH", extra="H3 5.77e-07 1 2.4e-8\nSTIG 0.557 1 0.039\n"))
    assert record["to"] == "ELL1H" and "H3 5.77e-07 1 2.4e-8" in new and "STIG 0.557 1 0.039" in new
    get_model(io.StringIO(new))


@pytest.mark.parametrize("text, message", [
    (par(extra="OMDOT 0.005 1 0.001\n"), "does not map: OMDOT"),
    (par(extra="PBDOT 1e-13 1 1e-14\n"), "does not map: PBDOT"),
    (par(model="ELL1"), "DD and DDH only"),
    (par(model="T2"), "DD and DDH only"),
    (par().replace("T0 56030.849202961685716 1 0.047", "T0 56030.849202961685716"), "all fitted"),
    (par(ecc="-1e-6"), "outside"),
])
def test_refuses_what_it_does_not_map(text, message):
    with pytest.raises(ValueError, match=message):
        reexpress.convert(text)


def test_own_uncertainty_matches_generalized_least_squares():
    rng = np.random.default_rng(3)
    design = rng.standard_normal((50, 3)) * [1, 1e-6, 1e3]
    covariance = np.diag(rng.uniform(1, 2, 50))
    expected = np.sqrt(np.diag(np.linalg.inv(design.T @ np.linalg.solve(covariance, design))))
    got = reexpress.own_uncertainty(design, ["a", "b", "c"], covariance, ["b", "c"])
    assert np.allclose([got["b"], got["c"]], expected[1:], rtol=1e-8)
