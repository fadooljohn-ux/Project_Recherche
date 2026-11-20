"""Model-level screen of binary par files (synthetic par text only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import binary_inventory as inv

BASE = "PSR J0000+0000\nSTART 50000\nFINISH 53652.5\nPB 5.0 1 1e-9\nA1 3.0 1 1e-7\n"
ELL1 = "TASC 50000 1\nEPS1 1e-6 1\nEPS2 1e-6 1\n"


def row(text):
    return inv.classify(inv.fields(BASE + text))


def test_isolated_pulsar_has_no_row():
    assert inv.classify(inv.fields("PSR J0000+0000\nF0 100 1\n")) is None


def test_classes():
    assert row("BINARY ELL1\nTASC 50000 1\nEPS1 1e-6 1\nEPS2 1e-6 1\n")["class"] == "NATIVE"
    assert row("BINARY ELL1\n" + ELL1 + "M2 0.2 1 0.01\nSINI 0.9 1 0.01\n")["class"] == "NEEDS SHAPIRO BASIS"
    assert row("BINARY ELL1\n" + ELL1 + "M2 0.2\nSINI 0.9\n")["class"] == "NATIVE"            # Shapiro held fixed in the release
    dd = "BINARY DD\nT0 50000 1\nOM 10 1\nECC 1e-5 1\n"
    assert row(dd)["class"] == "NEEDS RE-EXPRESSION"
    assert row(dd + "H3 1e-7 1\nSTIG 0.5 1\n")["class"] == "NEEDS RE-EXPRESSION + SHAPIRO BASIS"
    assert "eccentric" in row(dd.replace("1e-5", "0.2"))["blocker"]
    assert "OMDOT" in row(dd + "OMDOT 0.01 1\n")["blocker"]
    assert "not supported" in row("BINARY DDGR\n")["blocker"]
    assert row("BINARY T2\n" + ELL1 + "PBDOT 1e-13 1\n")["class"] == "NEEDS MODEL TRANSLATION"
    assert row(dd.replace("DD", "T2") + "M2 0.2 1\n")["class"] == "NEEDS MODEL TRANSLATION + RE-EXPRESSION + SHAPIRO BASIS"
    assert "PBDOT" in row(dd + "PBDOT 1e-13 1\n")["blocker"] and "KIN" in row("BINARY ELL1\n" + ELL1 + "KIN 70 1\n")["blocker"]
    assert "not fitted" in row("BINARY ELL1\nTASC 50000\nEPS1 1e-6\nEPS2 1e-6\n")["blocker"]
    assert "FB1" in inv.classify(inv.fields("START 50000\nFINISH 52000\nBINARY ELL1\nA1 1 1\n" + ELL1 + "FB0 1e-4 1\nFB1 1e-20 1\n"))["blocker"]


def test_period_range_and_wide_orbits():
    r = row("BINARY ELL1\n" + ELL1)
    assert r["rough_outer_period_days"] == [50.0, 1826.25]
    wide = inv.classify(inv.fields("START 50000\nFINISH 51500\nBINARY ELL1\nPB 100 1\nA1 1 1\n" + ELL1))
    assert wide["class"] == "BLOCKED" and "no outer-period range" in wide["blocker"]
