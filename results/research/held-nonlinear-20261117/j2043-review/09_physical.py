"""Check 7: physical plausibility of a circular 37.48 d outer orbit, and the DMX-series amplitude limit. Review diagnostics only."""
import numpy as np
from common import *
out = {}
G, c, Msun, Mearth, day = 6.6743e-11, 299792458.0, 1.98841e30, 5.9722e24, 86400.0
TSUN = 4.925490947e-6
PB, A1, M2, SINI = 1.4822907863872236, 1.6239581062963941, 0.18956002845614828, 0.9901823268544552
fm = 4 * np.pi**2 * A1**3 / (TSUN * (PB * day)**2)                      # mass function, Msun
Mtot = np.sqrt((M2 * SINI)**3 / fm); Mp = Mtot - M2
out["inner_binary"] = {"mass_function_Msun": fm, "pulsar_mass_Msun": Mp, "companion_Msun": M2, "total_Msun": Mtot,
                       "a_inner_AU": float((Mtot * (PB / 365.25)**2)**(1 / 3)), "a_inner_lt_s": float((Mtot * (PB / 365.25)**2)**(1 / 3) * 499.004784)}
def companion(P, amp_us):
    x = amp_us * 1e-6                                                    # light-seconds
    a_rel = (Mtot * (P / 365.25)**2)**(1 / 3)                            # AU, m << Mtot
    msini = x / (a_rel * 499.004784) * Mtot
    return {"period_d": P, "amp_us": amp_us, "a_AU": float(a_rel), "a_over_a_inner": float(a_rel / out["inner_binary"]["a_inner_AU"]),
            "m_sin_i_Msun": float(msini), "m_sin_i_Mearth": float(msini * Msun / Mearth), "m_sin_i_kg": float(msini * Msun),
            "m_sin_i_lunar": float(msini * Msun / 7.342e22), "m_sin_i_ceres": float(msini * Msun / 9.38e20)}
out["outer_37.48d"] = companion(37.48056, 0.0892)
out["outer_37.48d_red_modelled_amp"] = companion(37.48056, 0.078)
out["daily_alias_1.0245d(inside the binary; not a valid circumbinary orbit)"] = {"period_ratio_to_PB": 1.02452 / PB}
mu = M2 / Mtot
# Holman & Wiegert (1999) P-type critical semi-major axis for e_bin = 0
acrit = 1.60 + 4.12 * mu - 5.09 * mu**2
out["stability"] = {"mass_ratio_mu": float(mu), "holman_wiegert_a_crit_over_a_bin": float(acrit), "a_outer_over_a_bin": out["outer_37.48d"]["a_over_a_inner"],
                    "period_ratio": 37.48056 / PB, "stable_by_this_criterion": bool(out["outer_37.48d"]["a_over_a_inner"] > acrit)}
out["context"] = {"B1257+12 A (smallest known pulsar planet)": "about 0.02 Earth masses", "sensitivity_95pct_worst_phase_us": 0.125,
                  "note": "the fitted amplitude is below the calibrated 95% worst-phase amplitude, so recovered amplitude is biased upward if real (selection at threshold)"}
# DMX series: explicit amplitude and uncertainty at 37.48 d, errors scaled by the smooth-model reduced chi2
m = np.load(HERE / "meta.npz"); dmx = m["dmx"]; td = 0.5 * (dmx[:, 1] + dmx[:, 2]); v = dmx[:, 3]; e = dmx[:, 4]; K = 4.148808e3
for deg in (3, 8):
    x = (td - td.mean()) / np.ptp(td)
    B = np.column_stack([x**k for k in range(deg + 1)] + [np.sin(2 * np.pi * td / 365.25), np.cos(2 * np.pi * td / 365.25), np.sin(4 * np.pi * td / 365.25), np.cos(4 * np.pi * td / 365.25),
                         np.sin(2 * np.pi * (td - EPOCH) / 37.48056), np.cos(2 * np.pi * (td - EPOCH) / 37.48056)])
    W = 1 / e; cf, *_ = np.linalg.lstsq(B * W[:, None], v * W, rcond=None); r = (v - B @ cf) * W; red = float(r @ r / (len(v) - B.shape[1]))
    cov = np.linalg.inv((B * W[:, None]).T @ (B * W[:, None])) * red
    A, ph, sA, sp = amp_phase(cf[-2:], cov[-2:, -2:])
    out["dmx_amplitude_poly%d" % deg] = {"amp_pc_cm3": A, "amp_err_pc_cm3": sA, "reduced_chi2": red,
                                        "implied_430MHz-only_delay_us": K * A / 430**2 * 1e6, "its_error_us": K * sA / 430**2 * 1e6,
                                        "430-only_alternative_needs_us": 0.707, "tension_sigma": (0.707 - K * A / 430**2 * 1e6) / (K * sA / 430**2 * 1e6)}
dump("09_physical.json", out); print(json.dumps(out, indent=1, default=float))
