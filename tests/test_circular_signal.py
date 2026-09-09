from types import SimpleNamespace

import astropy.units as u
import numpy as np
import pytest

from pulsar_pilot.circular_signal import ProjectCircularSignal


def test_project_circular_signal_has_distinct_physical_category() -> None:
    signal = ProjectCircularSignal()
    assert signal.category == "project_circular_signal"
    assert signal.register is False


def test_project_circular_signal_delay_and_derivatives() -> None:
    signal = ProjectCircularSignal()
    signal.CSEPOCH.value = 56078.0
    signal.CSFREQ.value = 0.01
    signal.CSSIN.quantity = 10.0 * u.us
    signal.CSCOS.quantity = np.sqrt(300.0) * u.us
    toas = SimpleNamespace(table={"tdbld": np.array([56078.0, 56103.0])})
    delays = np.zeros(2) * u.s

    recovered = signal.circular_signal_delay(toas, delays).to_value(u.us)
    assert np.allclose(recovered, [np.sqrt(300.0), 10.0])
    assert np.allclose(
        signal.d_delay_d_cssin(toas, "CSSIN", delays).value,
        [0.0, 1.0],
        atol=1e-12,
    )
    assert np.allclose(
        signal.d_delay_d_cscos(toas, "CSCOS", delays).value,
        [1.0, 0.0],
        atol=1e-12,
    )


@pytest.mark.parametrize("parameter", ["CSSIN", "CSCOS"])
@pytest.mark.parametrize("attached", [False, True])
def test_signal_jacobian_matches_nonzero_delay_finite_difference(parameter, attached):
    signal = ProjectCircularSignal()
    signal.CSEPOCH.value = 56078.0
    signal.CSFREQ.value = 1 / 365.25
    signal.CSSIN.quantity = 5 * u.us
    signal.CSCOS.quantity = -3 * u.us
    toas = SimpleNamespace(table={"tdbld": np.array([56090.0, 56203.0, 56400.0])})
    upstream = np.array([430.0, -320.0, 170.0]) * u.s
    if attached:
        # PINT supplies None to component derivatives during design-matrix construction.
        def delay(toas, cutoff_component, include_last):
            assert cutoff_component == "ProjectCircularSignal" and not include_last
            return upstream
        signal._parent = SimpleNamespace(delay=delay)
    p = getattr(signal, parameter)
    original = p.quantity
    step = 0.01 * u.us
    p.quantity = original + step
    plus = signal.circular_signal_delay(toas, upstream)
    p.quantity = original - step
    minus = signal.circular_signal_delay(toas, upstream)
    p.quantity = original
    numerical = ((plus - minus) / (2 * step)).to_value(u.dimensionless_unscaled)
    derivative = getattr(signal, f"d_delay_d_{parameter.lower()}")(
        toas, parameter, None if attached else upstream
    ).value
    np.testing.assert_allclose(derivative, numerical, rtol=0, atol=1e-10)
