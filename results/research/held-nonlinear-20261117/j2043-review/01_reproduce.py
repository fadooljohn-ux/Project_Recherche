"""Check 1: independent reproduction near 37.48 d. Review diagnostic only."""
import sys
import numpy as np
from common import *
import nonlinear_statistic as ns

a = arrays(); C, N, J, y, t = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"]
rows = len(C)
out = {"shapes": {k: list(v.shape) for k, v in a.items()}}
g = GLS(C, np.column_stack([N, J]))
out["linear_null_chi2"] = g.chi2(y); out["dof_linear"] = rows - N.shape[1] - J.shape[1]
# frozen grid, own GLS
f = a["frequencies"]
lin = np.array([g.fit(y, tmpl(t, 1 / fi, rows))[0] for fi in f])
out["frozen_grid"] = {"max_abs_diff_linear_vs_run": float(np.max(np.abs(lin - a["run_delta"]))),
                      "linear_peak": float(lin.max()), "linear_peak_period": float(1 / f[lin.argmax()]),
                      "run_peak": float(a["run_delta"].max()),
                      "cells_above_threshold_run": [[float(1 / fi), float(d)] for fi, d in zip(f, a["run_delta"]) if d > THRESHOLD],
                      "top10_run": sorted([[float(d), float(1 / fi), bool(e)] for fi, d, e in zip(f, a["run_delta"], a["eligible"])], reverse=True)[:10]}
# fine grid 36.5-38.5 d
fine = np.linspace(1 / 38.6, 1 / 36.4, 1201)
linf = np.array([g.fit(y, tmpl(t, 1 / fi, rows))[0] for fi in fine])
delay = ns.PolynomialDelay(a["surrogate_coefficients"], a["surrogate_exponents"], a["orbit_lower"], a["orbit_upper"])
scan = ns.NonlinearScan(C, N, delay, ns.periodic_templates(t, fine, EPOCH, rows))
r = scan.scan(y)
k = int(r["delta_chi2"].argmax()); kl = int(linf.argmax())
d2, c, cov = g.fit(y, tmpl(t, 1 / fine[kl], rows))
A, ph, sA, sph = amp_phase(c, cov)
# period uncertainty from delta chi2 drop of 1
def width(d, fr):
    k0 = d.argmax(); ok = d > d[k0] - 1
    i = k0
    while i > 0 and ok[i - 1]: i -= 1
    j = k0
    while j < len(d) - 1 and ok[j + 1]: j += 1
    return [float(1 / fr[j]), float(1 / fr[i])]
out["fine_grid"] = {
    "nonlinear": {"peak_period": float(1 / fine[k]), "peak": float(r["delta_chi2"][k]),
                  "amp_us": float(np.hypot(*r["template_coefficients"][k]) * 1e6),
                  "phase_rad_atan2(cos,sin)": float(np.arctan2(r["template_coefficients"][k][1], r["template_coefficients"][k][0])),
                  "null_chi2": r["null_chi2"], "unconverged": int(r["unconverged"].sum()), "on_boundary": int(r["on_boundary"].sum()),
                  "orbit_at_peak_sigma_units": r["orbit"][k].tolist(), "null_orbit": r["null_orbit"].tolist(),
                  "period_interval_dchi2_1": width(r["delta_chi2"], fine)},
    "linear": {"peak_period": float(1 / fine[kl]), "peak": float(linf[kl]), "amp_us": A * 1e6, "amp_err_us": sA * 1e6,
               "phase_rad": ph, "phase_err_rad": sph, "sin_coeff_us": c[0] * 1e6, "cos_coeff_us": c[1] * 1e6,
               "period_interval_dchi2_1": width(linf, fine)},
    "max_abs_nonlinear_minus_linear": float(np.max(np.abs(r["delta_chi2"] - linf))),
    "nonlinear_minus_linear_at_peak": float(r["delta_chi2"][k] - linf[k])}
np.savez(HERE / "01_fine.npz", freq=fine, linear=linf, nonlinear=r["delta_chi2"], frozen_linear=lin)
# harmonics / subharmonics at the peak
P = 1 / fine[k]
out["harmonics_linear"] = {str(m): g.fit(y, tmpl(t, P * m, rows))[0] for m in (0.25, 1 / 3, 0.5, 2, 3)}
# extended linear scan below the search floor (periods 5-30 d) for context only
ext = np.arange(1 / 30, 1 / 3.0, 6.0497185504983004e-05 )
le = np.array([g.fit(y, tmpl(t, 1 / fi, rows))[0] for fi in ext])
np.savez(HERE / "01_extended.npz", freq=ext, linear=le)
top = np.argsort(le)[::-1][:8]
out["extended_3_to_30d_linear_top"] = [[float(1 / ext[i]), float(le[i])] for i in top]
out["extended_cells"] = len(ext); out["extended_mean"] = float(le.mean())
dump("01_reproduce.json", out); print(json.dumps(out, indent=1, default=float))
