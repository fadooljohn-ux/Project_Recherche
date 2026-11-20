"""The orbit box is cut at declared physical floors and is otherwise unchanged."""

import sys
from pathlib import Path
from types import SimpleNamespace

import astropy.units as u
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from nonlinear_verification import BoundedOrbit  # noqa: E402


def model(mass, mass_sigma, sine, sine_sigma):
    parameter = lambda value, sigma: SimpleNamespace(value=value, uncertainty_value=sigma)  # noqa: E731
    return SimpleNamespace(M2=parameter(mass, mass_sigma), SINI=parameter(sine, sine_sigma),
                           delay=lambda toas: np.zeros(toas.ntoas) * u.s)


TOAS = SimpleNamespace(ntoas=3)


def test_without_floors_an_unphysical_mass_box_is_refused():
    with pytest.raises(ValueError, match="mass domain"):
        BoundedOrbit(model(0.2, 0.06, 0.9, 0.03), TOAS, ["M2", "SINI"], 5.0)


def test_floors_cut_the_box_and_keep_published_scales():
    source = model(0.2, 0.06, 0.9, 0.03)
    orbit = BoundedOrbit(source, TOAS, ["M2", "SINI"], 5.0, {"M2": 0.0, "COSI": 0.05})
    assert source.M2.uncertainty_value == 0.06
    assert float(orbit.scales["M2"]) == 0.06
    assert orbit.lower[0] == pytest.approx(-0.2 / 0.06)
    assert orbit.upper[0] == 5.0
    cosine = float(orbit.cos0 + orbit.lower[1] * orbit.cos_scale)
    assert cosine == pytest.approx(0.05)
    orbit.set(orbit.lower)
    assert float(source.M2.value) == pytest.approx(0.0, abs=1e-12)
    assert float(source.SINI.value) == pytest.approx(np.sqrt(1 - 0.05**2))


def test_floors_that_do_not_bind_leave_the_box_unchanged():
    plain = BoundedOrbit(model(0.26, 0.01, 0.9, 0.001), TOAS, ["M2", "SINI"], 5.0)
    floored = BoundedOrbit(model(0.26, 0.01, 0.9, 0.001), TOAS, ["M2", "SINI"], 5.0, {"M2": 0.0, "COSI": 0.05})
    assert np.array_equal(plain.lower, floored.lower) and np.array_equal(plain.upper, floored.upper)
