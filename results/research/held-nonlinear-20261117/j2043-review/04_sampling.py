"""Check 2: sampling, spectral window, aliases, leakage. Review diagnostics only."""
import itertools
import numpy as np
from common import *
a = arrays(); m = np.load(HERE / "meta.npz")
C, N, J, y, t = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"]
rows, n = len(C), len(t); f = a["frequencies"]; out = {}
g = GLS(C, np.column_stack([N, J]))
F0 = 1 / 37.48056; FS = 1.0027379093; FY = 1 / 365.2422; FB = 1 / 1.4822907863872236
sig = np.sqrt(np.diag(C)[:n]); wts = 1 / sig**2

# (a) spectral window, epoch-level and weighted
def window(fr, w=None):
    w = np.ones(n) if w is None else w
    return np.abs(np.exp(2j * np.pi * np.outer(fr, t)) @ w)**2 / w.sum()**2
fr = np.arange(1e-4, 0.2, 1e-5)
W = window(fr, wts)
pk = [i for i in range(1, len(fr) - 1) if W[i] > W[i - 1] and W[i] > W[i + 1] and fr[i] > 2 / np.ptp(t)]
pk = sorted(pk, key=lambda i: -W[i])[:10]
out["window_top_peaks_period_days_power(<0.2 c/d, excluding main lobe)"] = [[float(1 / fr[i]), float(W[i])] for i in pk]
out["window_at_f0"] = float(window(np.array([F0]), wts)[0])
out["window_near_f0_max(+-3e-4)"] = float(window(np.arange(F0 - 3e-4, F0 + 3e-4, 5e-6), wts).max())
# window at difference frequencies between 37.48 d and named periods (how strongly each leaks into 37.48 d)
named = {"719 d": 1 / 718.68, "1 yr": FY, "0.5 yr": 2 * FY, "sidereal day": FS, "solar day": 1.0, "PB": FB, "PB/2": 2 * FB, "PB/3": 3 * FB,
         "PB/4": 4 * FB, "synodic month 29.53": 1 / 29.530589, "sidereal month 27.32": 1 / 27.321661, "anomalistic 27.55": 1 / 27.554550,
         "half synodic 14.77": 2 / 29.530589, "215 d (peak 3)": 1 / 214.67}
out["window_at_|f0 -/+ f_named|"] = {k: [float(window(np.array([abs(F0 - v)]), wts)[0]), float(window(np.array([F0 + v]), wts)[0])] for k, v in named.items()}
np.savez(HERE / "04_window.npz", fr=fr, W=W)

# (b) integer-combination coincidences: |f0 - (m fb + k fs + j fy + l fmoon)| < half resolution
res = 1 / np.ptp(t); hits = []; tried = 0
for mm, k, j in itertools.product(range(0, 7), range(-6, 7), range(-3, 4)):
    if mm == 0 and k == 0: continue
    tried += 1
    for sgn in (1, -1):
        d = sgn * (mm * FB + k * FS + j * FY) - F0
        if abs(d) < res / 2: hits.append({"m_fb": mm, "k_fsid": k, "j_fyr": j, "sign": sgn, "offset_in_resolution_units": d / res, "period": 1 / (F0 + d)})
out["alias_combinations"] = {"resolution_c_per_d": res, "combinations_tried": tried, "hits_within_half_resolution": hits,
                             "expected_chance_hits": tried * 2 * res / FS, "note": "aliases of orbital harmonics fold onto [0, f_sid); chance rate ~ tried*2*res/f_sid"}
cad = np.diff(np.unique(np.floor(t + 0.5)))
out["cadence"] = {"median_gap_d": float(np.median(cad)), "gaps_37_to_38d": int(((cad >= 36.5) & (cad <= 38.5)).sum()), "n_gaps": len(cad),
                  "note": "histogram mode is 7 d; 37.48/7 = 5.354"}
out["dmx_width_days"] = [float(x) for x in np.quantile(m["dmx"][:, 2] - m["dmx"][:, 1], [0, 0.5, 1])]

# (c) leakage: noiseless injections at named periods; response at 37.48 d on the frozen grid
kpk = int(np.argmin(np.abs(f - 1 / P0)))
def leak(period, phase=0.0, amp=1e-6, weight=None):
    s = np.zeros(rows); s[:n] = amp * np.sin(2 * np.pi * (t - EPOCH) / period + phase) * (1 if weight is None else weight)
    d, _ = scan(g, s, t, f, rows)
    tot = g.chi2(s)
    return {"surviving_chi2_per_us2": tot, "delta_at_37.48_fraction_of_surviving": float(d[kpk - 2:kpk + 3].max() / tot) if tot > 0 else None,
            "grid_peak_period": float(1 / f[d.argmax()]), "grid_peak_fraction": float(d.max() / tot) if tot > 0 else None,
            "amp_us_needed_for_26.87_at_37.48": float(np.sqrt(26.87 / d[kpk - 2:kpk + 3].max())) if d[kpk - 2:kpk + 3].max() > 0 else None}
L = {}
for name, per in [("719 d", 718.68), ("689 d", 688.74), ("1 yr", 365.2422), ("0.5 yr", 182.6211), ("215 d", 214.67), ("sidereal day", 1 / FS), ("solar day", 1.0),
                  ("PB", 1 / FB), ("PB/2", 0.5 / FB), ("PB/3", 1 / (3 * FB)), ("PB/4", 0.25 / FB), ("PB/5", 0.2 / FB), ("PB/6", 1 / (6 * FB)),
                  ("29.53 d", 29.530589), ("27.32 d", 27.321661), ("14.77 d", 14.7653), ("13.66 d", 13.6608)]:
    r0, r1 = leak(per, 0.0), leak(per, np.pi / 2)
    L[name] = {"phase0": r0, "phase90": r1}
out["leakage_noiseless_injection"] = L

# (d) which true frequencies would be indistinguishable from 37.48 d? scan DATA and the best-fit MODEL to 2.1 c/d
d0, c0, cov0 = g.fit(y, tmpl(t, 1 / F0, rows))
model = tmpl(t, 1 / F0, rows) @ c0
wide = np.arange(1 / 3000, 2.1, 6.0497185504983004e-05 / 2)
dd, _ = scan(g, y, t, wide, rows); dm, _ = scan(g, model, t, wide, rows)
np.savez(HERE / "04_wide.npz", freq=wide, data=dd, model=dm)
def peaks(v, k):
    idx = [i for i in range(1, len(v) - 1) if v[i] >= v[i - 1] and v[i] >= v[i + 1]]
    return sorted(idx, key=lambda i: -v[i])[:k]
out["wide_scan_0_to_2.1cpd"] = {
    "cells": len(wide), "data_mean": float(dd.mean()),
    "data_top12": [[float(1 / wide[i]), float(wide[i]), float(dd[i]), float(dm[i] / d0)] for i in peaks(dd, 12)],
    "model_alias_top12(fraction of 37.48 response)": [[float(1 / wide[i]), float(wide[i]), float(dm[i] / d0), float(dd[i])] for i in peaks(dm, 12)]}

# (e) orbital-phase structure: extra orbital harmonics as nuisance, then the 37.48 d statistic
phi = 2 * np.pi * m["orbphase"]
H = {}
def cols(ms):
    Z = np.zeros((rows, 2 * len(ms)))
    for i, k in enumerate(ms): Z[:n, 2 * i], Z[:n, 2 * i + 1] = np.sin(k * phi), np.cos(k * phi)
    return Z
for ms in ([1], [2], [3], [4], [5], [6], [3, 4], [3, 4, 5, 6], [1, 2, 3, 4, 5, 6, 7, 8]):
    Z = cols(ms)
    dz = g.fit(y, Z)[0]
    g2 = GLS(C, np.column_stack([N, J, Z]))
    H[str(ms)] = {"delta_chi2_of_harmonics": dz, "dof": 2 * len(ms), "stat_37.48_after": g2.fit(y, tmpl(t, 1 / F0, rows))[0]}
out["orbital_harmonics"] = H
# does the best-fit 37.48 d model correlate with orbital phase? fold model & data residual by orbital phase
ph = m["orbphase"] % 1; bins = np.floor(ph * 8).astype(int)
wr = y[:n] / sig**2
out["orbital_phase_binned_weighted_mean_residual_us"] = [float(wr[bins == b].sum() / wts[bins == b].sum() * 1e6) for b in range(8)]
out["orbital_phase_binned_err_us"] = [float(wts[bins == b].sum()**-0.5 * 1e6) for b in range(8)]
# phase of 37.48 d cycle vs orbital phase correlation (should be ~uniform joint coverage)
p37 = ((t - EPOCH) * F0) % 1
out["joint_coverage_orbital_x_37d_phase_4x4_counts"] = np.histogram2d(ph, p37, bins=4, range=[[0, 1], [0, 1]])[0].astype(int).tolist()
out["phase_coverage_37d_10bins"] = np.histogram(p37, bins=10, range=(0, 1))[0].tolist()
dump("04_sampling.json", out); print(json.dumps(out, indent=1, default=float))
