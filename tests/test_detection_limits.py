"""Detection-limit arithmetic on synthetic curves."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import detection_limits as dl


def test_crossing_interpolates_and_reports_unreached_levels():
    assert abs(dl.crossing([1.0, 2.0, 4.0], [0.0, 0.9, 1.0], 0.95) - 2.0 * 2 ** 0.5) < 1e-12
    assert dl.crossing([1.0, 2.0], [0.2, 0.6], 0.95) is None
    assert dl.crossing([1.0, 2.0], [0.97, 1.0], 0.95) == 1.0


def test_minimum_mass_matches_the_earth_sun_reflex():
    # The Sun's reflex about the Earth-Sun barycentre is 1.4960e11 m * 3.0035e-6 = 4.493e5 m = 1498.8 microseconds.
    assert abs(dl.minimum_mass_earth(1498.8, 365.256, 1.0) - 1.0) < 2e-3


def test_limits_take_the_largest_over_generators():
    cell = lambda ideal, fractions: {"period_days": 100.0, "ideal_amplitude_us": ideal, "detection_fractions": fractions}
    s = {"ladder_times_ideal": [1.0, 2.0, 4.0],
         "generators": [{"cells": [cell(1.0, [0.5, 1.0, 1.0])]}, {"cells": [cell(3.0, [0.0, 0.5, 1.0])]}]}
    row = dl.limits(s, 1.4)[0]
    assert row["reference_amplitude_50_us"] == 1.0 and row["largest_amplitude_50_us"] == 6.0
    assert row["largest_minimum_mass_95_earth"] > row["reference_minimum_mass_95_earth"]
