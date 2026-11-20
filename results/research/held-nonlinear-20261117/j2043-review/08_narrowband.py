"""Check 6: the NANOGrav 15-yr NARROWBAND TOAs of J2043+1711 (same Arecibo observations, different TOA reduction and
noise model with ECORR). Linearised GLS at fixed released narrowband noise. NOT independent data; review diagnostic only."""
from contextlib import ExitStack
import numpy as np
from common import *
import binary_wideband as binary
import target_calibration as cal
from pulsar_pilot.pilot2_offline_resources import NetworkDeny
from pulsar_pilot.spin_phase import bind_precise_spin_phase

base = HERE / "ng15-extract/NANOGrav15yr_PulsarTiming_v2.1.0/narrowband"
par, tim = base / "par/J2043+1711_PINT_20220302.nb.par", base / "tim/J2043+1711_PINT_20220302.nb.tim"
out = {"par_sha256": cal.digest(par), "tim_sha256": cal.digest(tim)}
(HERE / "loadout_nb").mkdir(exist_ok=True)
with ExitStack() as stack:
    import pint.logging
    from pint.models import get_model_and_toas
    from pint.residuals import Residuals
    pint.logging.setup(level="WARNING", sink=HERE / "loadout_nb/pint.log", removeprior=True)
    deny = stack.enter_context(NetworkDeny())
    stack.enter_context(binary.BinaryResources(HERE.parent / "binary-pilot02-20260909")).bind_science_resources()
    model, toas = get_model_and_toas(str(par), str(tim), ephem="DE440", include_bipm=True, bipm_version="BIPM2019", planets=True, usepickle=False, limits="error")
    bind_precise_spin_phase(model); binary.bind_ell1_derivative(model)
    M, names, units = model.designmatrix(toas)
    res = np.asarray(Residuals(toas, model).time_resids.to_value("s"), float)
    Cn = np.asarray(model.toa_covariance_matrix(toas), float)  # PINT returns s^2 as a plain array
    t = np.asarray(toas.table["tdbld"].data, float)
    fl = np.array([str(f.get("f", "")) for f in toas.table["flags"]]); nu = np.asarray(toas.table["freq"].data, float)
    out["network_attempts"] = len(deny.attempts)
M = np.asarray(M, float); n = len(t)
out.update({"toas": n, "design_columns": M.shape[1], "noise_components": [c for c in model.components if "Noise" in c or "Scale" in c or "Ecorr" in c],
            "offdiag_nonzero": int(np.count_nonzero(Cn) - n), "span_d": float(np.ptp(t)), "flags": {k: int(v) for k, v in zip(*np.unique(fl, return_counts=True))}})
g = GLS(Cn, M); out["null_chi2"] = g.chi2(res); out["dof"] = n - M.shape[1]
f = arrays()["frequencies"]; elig = arrays()["eligible"]
d, co = scan(g, res, t, f, n, chunk=100)
k = int(np.argmin(np.abs(f - 1 / P0)))
top = np.argsort(np.where(elig, d, -1))[::-1][:8]
out["frozen_grid"] = {"stat_at_37.482": float(d[k]), "max_within_2_cells": float(d[k - 2:k + 3].max()), "grid_max_eligible": [float(d[top[0]]), float(1 / f[top[0]])],
                      "top8_eligible": [[float(1 / f[i]), float(d[i])] for i in top], "mean_stat_eligible": float(d[elig].mean()),
                      "rank_of_37.48_cell_among_eligible": int((d[elig] > d[k - 2:k + 3].max()).sum()) + 1}
fine = np.linspace(1 / 38.6, 1 / 36.4, 601); dfine, cf = scan(g, res, t, fine, n, chunk=100); kk = int(dfine.argmax())
Tm = tmpl(t, 37.48056, n); d37, c37, cov37 = g.fit(res, Tm); A = amp_phase(c37, cov37)
out["fine"] = {"local_peak_period": float(1 / fine[kk]), "local_peak_stat": float(dfine[kk]),
               "at_37.4806": {"stat": d37, "amp_us": A[0] * 1e6, "amp_err_us": A[2] * 1e6, "phase": A[1], "phase_err": A[3]}}
# compare with the wideband coefficients (same epoch convention)
a = arrays(); gw = GLS(a["covariance"], np.column_stack([a["nuisance"], a["jac"]])); dw, cw, covw = gw.fit(a["residuals"], tmpl(a["times"], 37.48056, len(a["covariance"])))
diff = c37 - cw
out["wideband_reference"] = {"stat": dw, "amp_us": float(np.hypot(*cw) * 1e6), "phase": float(np.arctan2(cw[1], cw[0]))}
out["coefficient_difference_nb_minus_wb_us"] = [float(x * 1e6) for x in diff]
out["note_on_difference"] = "the two TOA sets come from the same observations, so their noise is strongly correlated; no formal consistency chi2 is quoted"
# per-receiver within narrowband
for name, sel in (("430", np.char.startswith(fl, "430")), ("L-wide", np.char.startswith(fl, "L-wide"))):
    T2 = Tm * sel[:, None]; dd, cc, cv = g.fit(res, T2); AA = amp_phase(cc, cv)
    out["nb_template_%s_only" % name] = {"stat": dd, "amp_us": AA[0] * 1e6, "amp_err_us": AA[2] * 1e6, "phase": AA[1]}
# low-frequency structure and red-noise sensitivity in narrowband too
T = np.ptp(t); fk = np.arange(1, 112) / T; F = np.zeros((n, 222)); ph = 2 * np.pi * np.outer(t - t.min(), fk); F[:, 0::2], F[:, 1::2] = np.sin(ph), np.cos(ph)
out["low_modes_dchi2"] = {"lowest_1": g.fit(res, F[:, :2])[0], "lowest_3": g.fit(res, F[:, :6])[0]}
def phi(log10A, gamma):
    fhz = fk / 86400; fyrhz = 1 / (365.25 * 86400)
    return np.repeat((10**log10A)**2 / (12 * np.pi**2) * fyrhz**(gamma - 3) * fhz**(-gamma) / (T * 86400), 2)
for la, ga in ((-15.0, 13 / 3), (-14.6, 13 / 3), (-14.34, 3.05)):
    gr = GLS(Cn + (F * phi(la, ga)) @ F.T, M); dr, cr, cvr = gr.fit(res, Tm)
    out["nb_with_red_logA%.2f_g%.2f" % (la, ga)] = {"stat": dr, "amp_us": float(np.hypot(*cr) * 1e6), "null_chi2": gr.chi2(res)}
np.savez(HERE / "08_narrowband.npz", freq=f, stat=d, fine=fine, fine_stat=dfine)
dump("08_narrowband.json", out); print(json.dumps(out, indent=1, default=float))
