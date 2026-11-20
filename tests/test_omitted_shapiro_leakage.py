"""Omitted-Shapiro leakage arithmetic (no observations read)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import omitted_shapiro_leakage as leak


def test_mass_function_and_companion_mass_are_consistent():
    # J1738+0333-like: x = 0.3434 lt-s, PB = 0.3548 d gives f of about 3.5e-4 solar masses.
    f = leak.mass_function(0.343429, 0.3547907)
    assert abs(f - 3.455e-4) < 5e-6
    for mp in leak.PULSAR_MASSES:
        for inc in leak.INCLINATIONS:
            m = leak.companion_mass(f, mp, inc)
            assert abs((m * np.sin(np.deg2rad(inc))) ** 3 / (mp + m) ** 2 - f) < 1e-12
    assert leak.companion_mass(f, 1.4, 30) > leak.companion_mass(f, 1.4, 85)      # face-on needs a heavier companion


def test_shapiro_delay_peaks_at_superior_conjunction_and_scales_with_mass():
    phase = np.linspace(0, 2 * np.pi, 3601)
    delay = leak.shapiro_delay(0.2, 85.0, phase)
    assert abs(phase[np.argmax(delay)] - np.pi / 2) < 1e-3
    assert np.allclose(leak.shapiro_delay(0.4, 85.0, phase), 2 * delay)
    expected = -2 * leak.T_SUN * 0.2 * np.log(1 - np.sin(np.deg2rad(85.0)))
    assert abs(delay.max() - expected) < 1e-15


def test_scenarios_cover_the_declared_grid():
    rows = leak.scenarios(1e-3)
    assert len(rows) == len(leak.INCLINATIONS) * len(leak.PULSAR_MASSES)
    assert {r["inclination_degrees"] for r in rows} == set(leak.INCLINATIONS)
