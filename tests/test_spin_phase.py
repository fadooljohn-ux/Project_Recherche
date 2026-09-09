import copy
import math
from fractions import Fraction
from types import SimpleNamespace

import astropy.units as u
import numpy as np
import pytest

from pulsar_pilot.spin_phase import bind_precise_spin_phase, spin_phase_parts


class Spin:
    def __init__(self):
        self.PEPOCH = SimpleNamespace(
            value=56000.0, quantity=SimpleNamespace(tdb=SimpleNamespace(mjd_long=56000.0))
        )
        self.terms = [np.longdouble("641.928") * u.Hz, np.longdouble("-4.3e-14") * u.Hz / u.s]
        self.phase_funcs_component = [self.spindown_phase]

    def get_spin_terms(self):
        return self.terms

    def spindown_phase(self, toas, delay):
        raise AssertionError("Unsplit phase must not be called")


def exact(value):
    return Fraction(*np.longdouble(value).as_integer_ratio())


@pytest.mark.parametrize("mjd", [54000.25, 58000.25])
def test_split_phase_matches_exact_rational_polynomial(mjd):
    spin = Spin()
    toas = SimpleNamespace(table={"tdbld": np.array([mjd], dtype=np.longdouble)})
    delay = np.array(["432.1234567890123"], dtype=np.longdouble) * u.s
    whole, fractional = spin_phase_parts(spin, toas, delay)
    dt = (exact(mjd) - exact(56000)) * 86400 - exact(delay.value[0])
    reference = sum(
        exact(term.value) * dt ** (order + 1) / math.factorial(order + 1)
        for order, term in enumerate(spin.terms)
    )
    result = exact(whole[0]) + exact(fractional[0])
    assert abs(float(result - reference)) < 2e-19


def test_fractional_phase_resolves_delay_change_lost_in_large_spin_phase():
    spin = Spin()
    spin.terms = [np.longdouble(640) * u.Hz]
    toas = SimpleNamespace(table={"tdbld": np.array([58000.0], dtype=np.longdouble)})
    delay = np.array([500], dtype=np.longdouble) * u.s
    shifted = delay + np.longdouble("1e-13") * u.s
    a = spin_phase_parts(spin, toas, delay)
    b = spin_phase_parts(spin, toas, shifted)
    difference = exact(b[0][0]) - exact(a[0][0]) + exact(b[1][0]) - exact(a[1][0])
    expected = -640 * (exact(shifted.value[0]) - exact(delay.value[0]))
    assert abs(float(difference - expected)) < 2e-19
    assert difference != 0
    # Demonstrate the failure mechanism at the same input precision.
    t = np.longdouble(2000) * 86400
    assert (t - delay.value[0]) * 640 == (t - shifted.value[0]) * 640


def test_binding_survives_model_copy_and_is_idempotent():
    model = SimpleNamespace(components={"Spindown": Spin()})
    bind_precise_spin_phase(model)
    bind_precise_spin_phase(model)
    cloned = copy.deepcopy(model)
    spin = cloned.components["Spindown"]
    assert len(spin.phase_funcs_component) == 2
    assert all(function.__self__ is spin for function in spin.phase_funcs_component)
    assert spin is not model.components["Spindown"]
