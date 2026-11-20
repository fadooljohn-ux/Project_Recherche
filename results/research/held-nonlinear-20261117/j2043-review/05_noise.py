"""Check 3: noise-model sensitivity at the peak. Review diagnostics only; thresholds are the frozen ones."""
import numpy as np
from scipy.stats import chi2 as chi2dist
from scipy.optimize import brentq
from common import *
a = arrays(); m = np.load(HERE / "meta.npz"); ep = np.load(HERE / "epochs.npz")["ep"]
C, N, J, y, t = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"]
rows, n = len(C), len(t); out = {}
D = np.column_stack([N, J]); D = D / np.linalg.norm(D, axis=0)
fine = np.linspace(1 / 37.75, 1 / 37.2, 45)
EMP = 20.457684779563266

def evaluate(Cm):
    """null chi2, marginal log-likelihood (up to a constant), statistic at 37.4806 d and its local maximum."""
    g = GLS(Cm, D)
    c2 = g.chi2(y)
    logdet = 2 * np.log(np.diag(g.L)).sum()
    Dw = solve_triangular(g.L, D, lower=True)
    lnl = -0.5 * (c2 + logdet + np.linalg.slogdet(Dw.T @ Dw)[1])
    d, co = scan(g, y, t, fine, rows)
    k = d.argmax()
    return {"null_chi2": c2, "lnL": lnl, "stat_at_37.4806": float(g.fit(y, tmpl(t, 37.48056, rows))[0]), "stat_local_max": float(d[k]),
            "period_local_max": float(1 / fine[k]), "amp_us": float(np.hypot(*co[k]) * 1e6)}

base = evaluate(C); out["baseline"] = base
def rel(r): r = dict(r); r["dlnL_vs_released"] = r.pop("lnL") - base["lnL"]; return r

# (1) chi2 partition with leverage
g = GLS(C, D); L = g.L
w = g.proj(y)  # whitened post-fit residual; C diagonal so rows map one-to-one
h = 1 - np.einsum("ij,ij->i", g.Q, g.Q)  # expected chi2 share of each row
parts = {"time_rows": np.arange(rows) < n, "dm_rows": np.arange(rows) >= n}
for fe in np.unique(m["flag_fe"]):
    parts["time_" + fe] = np.concatenate([m["flag_fe"] == fe, np.zeros(n, bool)])
    parts["dm_" + fe] = np.concatenate([np.zeros(n, bool), m["flag_fe"] == fe])
out["chi2_partition"] = {k: {"chi2": float((w[s]**2).sum()), "expected(effective dof)": float(h[s].sum()),
                             "ratio": float((w[s]**2).sum() / h[s].sum()), "implied_sigma_scale": float(np.sqrt((w[s]**2).sum() / h[s].sum()))}
                         for k, s in parts.items()}
out["null_chi2_tail"] = {"chi2": base["null_chi2"], "dof": 676, "upper_tail": float(chi2dist.sf(base["null_chi2"], 676))}

# (2) error inflation: all rows, time rows only, per receiver (time rows)
def scaled(k, sel):
    s = np.ones(rows); s[sel] = k
    return C * np.outer(s, s)
sels = {"all_rows": np.ones(rows, bool), "time_rows": parts["time_rows"], "time_430": parts["time_430"], "time_L-wide": parts["time_L-wide"]}
infl = {}
for name, sel in sels.items():
    infl[name] = {str(k): rel(evaluate(scaled(k, sel))) for k in (1.028, 1.05, 1.10, 1.15, 1.20)}
    for label, thr in (("union_threshold_23.998", THRESHOLD), ("empirical_99pct_20.458", EMP)):
        fn = lambda k: evaluate(scaled(k, sel))["stat_local_max"] - thr
        try:
            k0 = brentq(fn, 1.0, 3.0, xtol=1e-4); r = rel(evaluate(scaled(k0, sel)))
            dof_ok = float(chi2dist.cdf(r["null_chi2"], 676))
            infl[name]["needed_for_" + label] = {"scale": k0, **r, "lower_tail_of_null_chi2": dof_ok}
        except ValueError:
            infl[name]["needed_for_" + label] = "not reached for scale <= 3"
    ks = np.linspace(0.9, 1.3, 81); ll = [evaluate(scaled(k, sel))["lnL"] for k in ks]
    i = int(np.argmax(ll)); inside = ks[np.array(ll) > ll[i] - 0.5]
    infl[name]["max_likelihood_scale"] = {"scale": float(ks[i]), "dlnL_vs_released": ll[i] - base["lnL"], "interval_dlnL_0.5": [float(inside.min()), float(inside.max())]}
out["error_inflation"] = infl

# (3) extra white terms on time rows: EQUAD in quadrature; epoch-common achromatic term (jitter/ECORR-like per DMX epoch)
U = np.zeros((rows, ep.max() + 1)); U[np.arange(n), ep] = 1
def equad(q): Cm = C.copy(); Cm[np.arange(n), np.arange(n)] += (q * 1e-9)**2; return Cm
def ecorr(q): return C + (q * 1e-9)**2 * (U @ U.T)
for name, fn in (("extra_equad_ns", equad), ("epoch_common_achromatic_ns", ecorr)):
    r = {str(q): rel(evaluate(fn(q))) for q in (20, 40, 60, 80, 100, 150)}
    for label, thr in (("union_threshold_23.998", THRESHOLD), ("empirical_99pct_20.458", EMP)):
        try:
            q0 = brentq(lambda q: evaluate(fn(q))["stat_local_max"] - thr, 0.0, 2000.0, xtol=0.1); r["needed_for_" + label] = {"ns": q0, **rel(evaluate(fn(q0)))}
        except ValueError:
            r["needed_for_" + label] = "not reached below 2000 ns"
    qs = np.arange(0, 201, 5.0); ll = [evaluate(fn(q))["lnL"] for q in qs]; i = int(np.argmax(ll)); inside = qs[np.array(ll) > ll[i] - 0.5]
    r["max_likelihood"] = {"ns": float(qs[i]), "dlnL_vs_released": ll[i] - base["lnL"], "interval_dlnL_0.5": [float(inside.min()), float(inside.max())],
                           "dlnL_upper_2(~95%)": float(qs[np.array(ll) > ll[i] - 2].max())}
    out[name] = r

# (4) power-law red noise on time rows, Fourier modes k/T up to 1/30 d
T = np.ptp(t); modes = int(np.ceil(T / 30.0)); fk = np.arange(1, modes + 1) / T
F = np.zeros((rows, 2 * modes)); ph = 2 * np.pi * np.outer(t - t.min(), fk); F[:n, 0::2], F[:n, 1::2] = np.sin(ph), np.cos(ph)
fyr = 1 / 365.25
def red(log10A, gamma):
    # one-sided PSD convention of enterprise/PINT: phi_k = A^2/(12 pi^2) f_yr^(gamma-3) f^-gamma / T, in s^2 with f in Hz
    fhz = fk / 86400; fyrhz = 1 / (365.25 * 86400)
    phi = (10**log10A)**2 / (12 * np.pi**2) * fyrhz**(gamma - 3) * fhz**(-gamma) / (T * 86400)
    return C + (F * np.repeat(phi, 2)) @ F.T, phi
rn = {"modes": modes, "shortest_period_d": float(1 / fk[-1])}
for gamma in (0.5, 1.5, 2.5, 3.5, 13 / 3, 5.0):
    row = {}
    for la in (-15.0, -14.6, -14.0, -13.5, -13.0, -12.5):
        Cm, phi = red(la, gamma); r = rel(evaluate(Cm)); k37 = int(np.argmin(np.abs(1 / fk - 37.48)))
        r["rms_ns_per_mode_at_37.5d"] = float(np.sqrt(2 * phi[k37]) * 1e9); row[str(la)] = r
    for label, thr in (("union_threshold_23.998", THRESHOLD), ("empirical_99pct_20.458", EMP)):
        try:
            la0 = brentq(lambda la: evaluate(red(la, gamma)[0])["stat_local_max"] - thr, -16.0, -10.0, xtol=0.005)
            row["needed_for_" + label] = {"log10A": la0, **rel(evaluate(red(la0, gamma)[0]))}
        except ValueError:
            row["needed_for_" + label] = "not reached for log10A in [-16, -10]"
    las = np.arange(-16, -11.49, 0.1); ll = np.array([evaluate(red(la, gamma)[0])["lnL"] for la in las]); i = int(ll.argmax())
    row["max_likelihood"] = {"log10A": float(las[i]), "dlnL_vs_released": float(ll[i] - base["lnL"]),
                             "largest_log10A_with_dlnL>-2_vs_best": float(las[ll > ll[i] - 2].max())}
    rn["gamma_%.3f" % gamma] = row
out["red_noise"] = rn

# (5) single-TOA outlier and empirical null tail
z = y[:n] / np.sqrt(np.diag(C)[:n]); i = int(np.argmax(np.abs(z)))
Cm = C.copy(); Cm[i, i] *= 1e8; r = rel(evaluate(Cm))
out["largest_outlier_removed"] = {"toa_index": i, "mjd": float(t[i]), "z_prefit": float(z[i]), "flag": str(m["flag_f"][i]), **r}
with np.load(ROOT / "calibration/arrays.npz") as zz:
    nm = np.sort(zz["null_maxima"]); lm = np.sort(zz["linearised_null_maxima"])
top = nm[-205:]; scale = float(np.mean(top - top[0]))  # exponential tail above the 95% point
out["empirical_null_tail"] = {"count": len(nm), "max": float(nm[-1]), "quantiles_50_90_99_99.9": [float(np.quantile(nm, q)) for q in (0.5, 0.9, 0.99, 0.999)],
                              "exceeding_26.87": int((nm >= 26.87).sum()), "exceeding_24": int((nm >= 24).sum()), "exceeding_22": int((nm >= 22).sum()),
                              "exp_tail_scale_above_95pct": scale,
                              "extrapolated_p_single_search_26.87": float(0.05 * np.exp(-(26.871 - top[0]) / scale)),
                              "chi2_2dof_Neff_estimate_p_26.87": float(0.01 * np.exp(EMP / 2) * np.exp(-26.871 / 2)),
                              "note": "extrapolation beyond 4096 nulls under fixed Gaussian released noise; multiply by 3 for the three-target allowance"}
dump("05_noise.json", out); print(json.dumps(out, indent=1, default=float))
