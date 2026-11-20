"""Translation of T2/BT orbit models (par text only; no observations read)."""
import io
import sys
from pathlib import Path

import pytest
from pint.models import get_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import orbit_translate as tr

HEAD = "PSR J0000+0000\nF0 100 1\nPEPOCH 56000\nRAJ 00:00:00\nDECJ 00:00:00\nPB 5.7 1 1e-10\nA1 3.3 1 1e-7\n"
SMALL = "TASC 55000.1 1 1e-8\nEPS1 1e-6 1 1e-8\nEPS2 -2e-6 1 1e-8\n"
KEPLER = "T0 55000.1 1 1e-4\nOM 100 1 0.1\nECC 1e-4 1 1e-8\n"


@pytest.mark.parametrize("body, expected", [
    (SMALL, "ELL1"),
    (SMALL + "M2 0.2 1 0.01\nSINI 0.9 1 0.01\n", "ELL1"),
    (SMALL + "H3 1e-7 1 1e-8\nSTIG 0.5 1 0.1\n", "ELL1H"),
    (KEPLER, "DD"),
    (KEPLER + "M2 0.2 1 0.01\nSINI 0.9 1 0.01\nPBDOT 1e-13 1 1e-14\n", "DD"),
    (KEPLER + "H3 1e-7 1 1e-8\nSTIG 0.5 1 0.1\n", "DDH"),
])
def test_t2_is_renamed_by_parameter_content_and_loads(body, expected):
    text = HEAD + "BINARY T2\n" + body
    new, record = tr.translate(text)
    assert record["to"] == expected and record["from"] == "T2"
    assert new.replace("BINARY " + expected, "BINARY T2") == text        # nothing else changed
    assert expected in tr.confirm(text, record)
    model = get_model(io.StringIO(new))
    component, = [c for c in model.components.values() if c.category == "pulsar_system"]
    assert component.binary_model_name == expected


def test_bt_becomes_dd_only_without_shapiro():
    new, record = tr.translate(HEAD + "BINARY BT\n" + KEPLER + "GAMMA 0.0\n")
    assert record["to"] == "DD" and "BINARY DD" in new
    with pytest.raises(ValueError, match="without Shapiro"):
        tr.translate(HEAD + "BINARY BT\n" + KEPLER + "M2 0.2 1\nSINI 0.9 1\n")


@pytest.mark.parametrize("body, message", [
    (KEPLER + "KOM 90 1\nKIN 70 1\n", "does not cover: KOM KIN"),
    (SMALL + "FB1 1e-20 1\n", "does not cover: FB1"),
    (SMALL + KEPLER, "exactly one"),
    ("", "exactly one"),
    (SMALL + "M2 0.2 1\nSINI 0.9 1\nH3 1e-7 1\n", "both forms"),
    (SMALL + "STIG 0.5 1\n", "without H3"),
])
def test_refusals(body, message):
    with pytest.raises(ValueError, match=message):
        tr.translate(HEAD + "BINARY T2\n" + body)


def test_other_models_and_unused_zero_terms():
    with pytest.raises(ValueError, match="T2 and BT only"):
        tr.translate(HEAD + "BINARY ELL1\n" + SMALL)
    assert tr.translate(HEAD + "BINARY T2\n" + SMALL + "KIN 0\nM2 0\n")[1]["shapiro_form"] == "none"


def test_recentred_orbit_gives_the_tempo2_delay_in_the_all_harmonics_form():
    import astropy.units as u
    import numpy as np

    old = (HEAD.replace("A1 3.3 1 1e-7", "A1 1.0914441 1 1e-7") + "BINARY ELL1H\nTASC 55000.1 1 1e-8\n"
           "EPS1 4.0e-6 1 1e-8\nEPS2 3.4e-6 1 1e-8\nH3 2.41e-07 1 2.7e-8\nSTIG 0.808 1 0.06\n")
    new, record = tr.recentre_orthometric(old)
    assert record["released"]["A1"] == "1.0914441" and float(record["recentred"]["A1"]) < 1.0914441

    def delay(text):
        model = get_model(io.StringIO(text))
        component, = [c for c in model.components.values() if c.category == "pulsar_system"]
        binary = component.binary_instance
        times = np.linspace(55000, 55020, 4000)
        updates = {"barycentric_toa": times * u.day}
        for name in binary.binary_params:
            parameter = getattr(model, name, None)
            if parameter is not None and parameter.value is not None and parameter.units is not None:
                updates[name] = parameter.value * parameter.units
        binary.update_input(**updates)
        return binary.binary_delay().to_value(u.s), binary.Phi().to_value(u.rad)

    # tempo2: orbit without Shapiro terms plus the third-and-higher harmonics; library: recentred orbit, all harmonics.
    no_shapiro = "\n".join(l for l in old.splitlines() if not l.startswith(("H3", "STIG"))).replace("ELL1H", "ELL1") + "\n"
    roemer, phase = delay(no_shapiro)
    r, s = 2.41e-07 / 0.808 ** 3, 0.808
    tempo2 = roemer - 2 * r * (np.log(1 + s * s - 2 * s * np.sin(phase)) + 2 * s * np.sin(phase) - s * s * np.cos(2 * phase))
    library, _ = delay(new)
    # Agreement to 0.1 ns (second-order cross terms remain); the uncorrected difference is microseconds.
    assert np.max(abs(library - tempo2)) < 1e-10
    assert np.max(abs(delay(old)[0] - tempo2)) > 1e-6


def test_recentring_leaves_other_orbits_alone():
    for body in ("BINARY ELL1\n" + SMALL, "BINARY ELL1H\n" + SMALL + "H3 1e-7 1\nH4 5e-8 1\n",
                 "BINARY ELL1H\n" + SMALL + "H3 1e-7 1\n", "BINARY DDH\n" + KEPLER + "H3 1e-7 1\nSTIG 0.5 1\n"):
        assert tr.recentre_orthometric(HEAD + body) == (HEAD + body, None)
