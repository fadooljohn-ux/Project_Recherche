"""Refinement of a re-expressed orbit against the released model (simulated orbits; no observations read)."""
import io
import sys
from pathlib import Path

import astropy.units as u
import numpy as np
from pint.models import get_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import orbit_reexpress as reexpress
import orbit_refine as refine

PAR = """PSR J0000+0000
F0 100
PEPOCH 56000
RAJ 00:00:00
DECJ 00:00:00
BINARY DD
PB 175.46066190184385 1 1e-8
T0 56030.849202961685716 1 0.01
A1 55.3297209627269 1 1e-6
OM 50.7 1 0.01
ECC 7.972596e-04 1 1e-8
"""
TIMES = np.sort(np.random.default_rng(11).uniform(55000, 60500, 1500)).astype(np.longdouble)


def binary(text):
    model = get_model(io.StringIO(text))
    component, = [c for c in model.components.values() if c.category == "pulsar_system"]
    instance = component.binary_instance
    updates = {"barycentric_toa": TIMES * u.day}
    for name in instance.binary_params:
        parameter = getattr(model, name, None)
        if parameter is not None and parameter.value is not None and parameter.units is not None:
            updates[name] = parameter.value * parameter.units
    instance.update_input(**updates)
    return instance, model


def test_refinement_removes_the_first_order_offset_of_a_wide_slightly_eccentric_orbit():
    released, _ = binary(PAR)
    target = np.asarray(released.binary_delay().to_value(u.s), np.longdouble)
    new_text, _ = reexpress.convert(PAR)
    instance, model = binary(new_text)
    names = list(refine.PARAMETERS)
    units = [getattr(model, n).units for n in names]

    def delay(values):
        instance.update_input(**{n: v * unit for n, v, unit in zip(names, values, units)})
        return np.asarray(instance.binary_delay().to_value(u.s), np.longdouble)

    def derivatives(values):
        delay(values)
        return np.column_stack([np.asarray(instance.d_binarydelay_d_par(n).to_value(u.s / unit), float)
                                for n, unit in zip(names, units)])

    start = [getattr(model, n).value for n in names]
    values, record = refine.refine(delay, derivatives, target, start)
    assert record["rms_seconds_before"] > 1e-7                 # the first-order mapping is off by a fraction of a microsecond
    assert record["rms_seconds_after"] < 2e-8 and record["rms_seconds_after"] < 0.05 * record["rms_seconds_before"]
    assert abs(float(values[0] - start[0])) * 86400 < 1.0      # the change in TASC is a fraction of a second


def test_a_model_that_already_matches_is_left_alone():
    target = np.sin(np.linspace(0, 30, 300))
    values, record = refine.refine(lambda v: target + 0 * v[0], lambda v: np.cos(np.linspace(0, 30, 300))[:, None],
                                   target, [1.0])
    assert record["iterations"] == 0 and float(values[0]) == 1.0
