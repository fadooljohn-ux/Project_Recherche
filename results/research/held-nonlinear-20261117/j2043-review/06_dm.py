"""Check 4: chromaticity and DM. Review diagnostics only."""
import numpy as np
from common import *
a = arrays(); m = np.load(HERE / "meta.npz"); ep = np.load(HERE / "epochs.npz")["ep"]
C, N, J, y, t, f = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"], a["frequencies"]
rows, n = len(C), len(t); out = {}; names = list(m["names"])
D = np.column_stack([N, J]); P = 37.48056; Tm = tmpl(t, P, rows)
class GLSr(GLS):
    """GLS with a rank-revealing projection (for designs with empty or redundant columns)."""
    def __init__(self, Cm, Dm):
        self.L = cholesky(Cm, lower=True)
        Dm = Dm[:, np.linalg.norm(Dm, axis=0) > 0]
        Dw = solve_triangular(self.L, Dm / np.linalg.norm(Dm, axis=0), lower=True)
        u, s, _ = np.linalg.svd(Dw, full_matrices=False); self.Q = u[:, s > 1e-10 * s[0]]; self.rank = self.Q.shape[1]
g = GLS(C, D); d0, c0, cov0 = g.fit(y, Tm); A0 = amp_phase(c0, cov0)
out["baseline"] = {"stat": d0, "amp_us": A0[0] * 1e6, "amp_err_us": A0[2] * 1e6, "phase": A0[1], "phase_err": A0[3]}
nu = m["freq"]; fe = m["flag_fe"]
# (a) chromatic templates on the time rows
def wfit(weight, gg=g):
    T2 = Tm.copy(); T2[:n] *= weight[:, None]; d, c, cov = gg.fit(y, T2); A = amp_phase(c, cov)
    return {"stat": d, "amp_us_at_weight_1": A[0] * 1e6, "amp_err_us": A[2] * 1e6, "phase": A[1], "phase_err": A[3]}
out["template_achromatic"] = wfit(np.ones(n))
out["template_nu^-2_(ref 1400 MHz)_time_rows_only"] = wfit((nu / 1400.0)**-2)
out["template_nu^-4_(ref 1400 MHz)"] = wfit((nu / 1400.0)**-4)
out["template_430_only"] = wfit((fe == "430").astype(float))
out["template_L-wide_only"] = wfit((fe == "L-wide").astype(float))
# joint two-band fit and consistency
T4 = np.column_stack([Tm * np.concatenate([(fe == "430"), np.zeros(n, bool)])[:, None], Tm * np.concatenate([(fe == "L-wide"), np.zeros(n, bool)])[:, None]])
d4, c4, cov4 = g.fit(y, T4); diff = c4[:2] - c4[2:]; cd = cov4[:2, :2] + cov4[2:, 2:] - cov4[:2, 2:] - cov4[2:, :2]
out["two_band_joint"] = {"stat_4dof": d4, "improvement_over_achromatic_2dof": d4 - d0, "consistency_chi2_2dof": float(diff @ np.linalg.solve(cd, diff)),
                         "430": [x * (1e6 if i in (0, 2) else 1) for i, x in enumerate(amp_phase(c4[:2], cov4[:2, :2]))],
                         "L-wide": [x * (1e6 if i in (0, 2) else 1) for i, x in enumerate(amp_phase(c4[2:], cov4[2:, 2:]))], "format": "[amp_us, phase, amp_err_us, phase_err]"}
# DM-like signal: periodic DM(t) appearing coherently in time rows (K*DM/nu^2) and DM rows
K = 4.148808e3  # s MHz^2 / (pc cm^-3)
Tdm = np.zeros((rows, 2)); Tdm[:n] = Tm[:n] * (K / nu**2)[:, None]; Tdm[n:] = Tm[:n]
dd, cdm, covdm = g.fit(y, Tdm)
out["periodic_DM_template(time+DM rows coherent)"] = {"stat": dd, "note": "per-epoch DMX absorbs any DM change that is constant within an epoch (windows 0.10-0.17 d), so this is ~0 by construction"}
# (b) information budget: effective weight of each receiver in the achromatic template
Tw = g.proj(Tm); share = np.einsum("ij,ij->i", Tw, Tw)
out["template_information_share"] = {"430_time_rows": float(share[:n][fe == "430"].sum() / share.sum()), "L-wide_time_rows": float(share[:n][fe == "L-wide"].sum() / share.sum()),
                                     "dm_rows": float(share[n:].sum() / share.sum())}
# (c) different DM treatments
isdmx = np.array([x.startswith("DMX_") for x in names]); isdmj = np.array([x.startswith("DMJUMP") for x in names])
def variant(Cm, Dm, label):
    gg = GLSr(Cm, Dm); d, c, cov = gg.fit(y, Tm); A = amp_phase(c, cov)
    dl, _ = scan(gg, y, t, np.linspace(1 / 37.75, 1 / 37.2, 23), rows)
    return {"stat": d, "stat_local_max": float(dl.max()), "amp_us": A[0] * 1e6, "amp_err_us": A[2] * 1e6, "phase": A[1], "phase_err": A[3], "null_chi2": gg.chi2(y), "rank": gg.rank}
Cbig = C.copy(); Cbig[np.arange(n, rows), np.arange(n, rows)] *= 1e12
out["dm_variants"] = {
    "released (DMX free, DM measurements used)": variant(C, D, ""),
    "DM measurements ignored (DMX from two-band timing only)": variant(Cbig, D, ""),
    "DM measurement errors x2": variant(np.diag(np.concatenate([np.diag(C)[:n], 4 * np.diag(C)[n:]])), D, ""),
    "DM measurement errors x0.5": variant(np.diag(np.concatenate([np.diag(C)[:n], 0.25 * np.diag(C)[n:]])), D, ""),
    "DMX fixed at released values (no DMX columns)": variant(C, np.column_stack([N[:, ~isdmx], J]), ""),
    "DMJUMPs fixed": variant(C, np.column_stack([N[:, ~isdmj], J]), "")}
# epochs with both receivers vs one receiver
both = np.array([len(set(fe[ep == e])) == 2 for e in ep])
def rowsel(sel):
    Cm = C.copy(); bad = np.concatenate([~sel, ~sel]); Cm[bad, bad] *= 1e12; return Cm
out["dm_variants"]["only epochs with both receivers (%d TOAs)" % both.sum()] = variant(rowsel(both), D, "")
out["dm_variants"]["only single-receiver epochs (%d TOAs)" % (~both).sum()] = variant(rowsel(~both), D, "")
# (d) DMX series: is there a 37.48 d periodicity in DM itself?
dmx = m["dmx"]; td = 0.5 * (dmx[:, 1] + dmx[:, 2]); v = dmx[:, 3]; e = dmx[:, 4]
def dmx_scan(freqs, deg):
    x = (td - td.mean()) / np.ptp(td)
    B = np.column_stack([x**k for k in range(deg + 1)] + [np.sin(2 * np.pi * td / 365.25), np.cos(2 * np.pi * td / 365.25), np.sin(4 * np.pi * td / 365.25), np.cos(4 * np.pi * td / 365.25)])
    W = 1 / e; q, _ = np.linalg.qr(B * W[:, None]); r = v * W; r = r - q @ (q.T @ r); c2 = float(r @ r); s = []; amp = []
    for fr in freqs:
        Tt = np.column_stack([np.sin(2 * np.pi * fr * (td - EPOCH)), np.cos(2 * np.pi * fr * (td - EPOCH))]) * W[:, None]
        Tt = Tt - q @ (q.T @ Tt); b = Tt.T @ r; cc = np.linalg.solve(Tt.T @ Tt, b); s.append(b @ cc); amp.append(np.hypot(*cc))
    return np.array(s), np.array(amp), c2 / (len(v) - B.shape[1])
k37 = int(np.argmin(np.abs(f - 1 / P)))
for deg in (3, 8, 15):
    s, amp, red = dmx_scan(f, deg); s_n = s / red   # scale by the reduced chi2 of the smooth fit so the units are comparable
    band = (1 / f > 30) & (1 / f < 60)
    out["dmx_series_poly%d" % deg] = {"reduced_chi2_of_smooth_model": red, "scaled_stat_at_37.48": float(s_n[k37 - 2:k37 + 3].max()),
                                     "amp_pc_cm3_at_37.48": float(amp[k37]), "equivalent_delay_us_at_1400MHz": float(K * amp[k37] / 1400**2 * 1e6),
                                     "equivalent_delay_us_at_430MHz": float(K * amp[k37] / 430**2 * 1e6),
                                     "rank_percentile_among_30_60d_cells": float((s_n[band] <= s_n[k37 - 2:k37 + 3].max()).mean()),
                                     "median_scaled_stat_30_60d": float(np.median(s_n[band])), "max_scaled_stat_30_60d": [float(s_n[band].max()), float(1 / f[band][s_n[band].argmax()])],
                                     "grid_max": [float(s_n.max()), float(1 / f[s_n.argmax()])]}
# DMX first differences vs the fitted 37.48 d timing model evaluated at epoch times (correlation)
mod = np.array([np.mean((Tm @ c0)[:n][ep == i]) for i in range(len(dmx))])
x = (td - td.mean()) / np.ptp(td); B = np.column_stack([x**k for k in range(9)]); W = 1 / e
q, _ = np.linalg.qr(B * W[:, None]); rv = v * W - q @ (q.T @ (v * W)); rm = mod * W - q @ (q.T @ (mod * W))
out["correlation_dmx_residual_vs_37.48d_model"] = {"pearson_r": float(rv @ rm / np.sqrt((rv @ rv) * (rm @ rm))), "n_epochs": len(v), "approx_sigma_r": float(1 / np.sqrt(len(v) - 9))}
# DM-row post-fit residuals vs the model
w = g.proj(y); r_dm = w[n:]; mw = (Tm @ c0)[:n]
out["correlation_dm_row_whitened_residual_vs_37.48d_model"] = {"pearson_r": float(np.corrcoef(r_dm, mw)[0, 1]), "approx_sigma_r": float(1 / np.sqrt(n))}
dump("06_dm.json", out); print(json.dumps(out, indent=1, default=float))
