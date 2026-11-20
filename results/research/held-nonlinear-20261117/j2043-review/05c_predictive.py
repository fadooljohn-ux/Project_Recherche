"""Check 3 (continued): simulated behaviour of the frozen white-noise statistic when red noise drawn from the
released NANOGrav wideband noise chain is present, and of a real 37.48 d signal when red noise is modelled.
Linearised statistic on the frozen grid and eligible cells. Review diagnostics only; not a recalibration."""
import numpy as np
from common import *
a = arrays()
C, N, J, y, t, f, elig = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"], a["frequencies"], a["eligible"]
rows, n = len(C), len(t); out = {}
D = np.column_stack([N, J]); D = D / np.linalg.norm(D, axis=0)
T = np.ptp(t); modes = int(np.ceil(T / 30.0)); fk = np.arange(1, modes + 1) / T
F = np.zeros((rows, 2 * modes)); ph = 2 * np.pi * np.outer(t - t.min(), fk); F[:n, 0::2], F[:n, 1::2] = np.sin(ph), np.cos(ph)
def phi(log10A, gamma):
    fhz = fk / 86400; fyrhz = 1 / (365.25 * 86400)
    return np.repeat((10**log10A)**2 / (12 * np.pi**2) * fyrhz**(gamma - 3) * fhz**(-gamma) / (T * 86400), 2)

class Fast:
    def __init__(self, Cm):
        self.g = GLS(Cm, D)
        Tm = np.zeros((rows, 2 * len(f))); p = 2 * np.pi * np.outer(t - EPOCH, f); Tm[:n, 0::2], Tm[:n, 1::2] = np.sin(p), np.cos(p)
        self.Tw = self.g.proj(Tm)
        G = np.einsum("nfi,nfj->fij", self.Tw.reshape(rows, len(f), 2), self.Tw.reshape(rows, len(f), 2)); self.Gi = np.linalg.inv(G)
    def stat(self, data):
        b = (self.Tw.T @ self.g.proj(data)).reshape(-1, 2)
        return np.einsum("fi,fij,fj->f", b, self.Gi, b)
white = Fast(C)
obs = white.stat(y); out["observed_linear_peak"] = [float(obs[elig].max()), float(1 / f[elig][obs[elig].argmax()])]
rng = np.random.default_rng(2026111801); L = white.g.L
base = HERE / "ng15-extract/NANOGrav15yr_PulsarTiming_v2.1.0/wideband/noise"
names = (base / "J2043+1711.wb.pars.txt").read_text().split(); ch = np.loadtxt(base / "J2043+1711.wb.chain_1.txt"); ch = ch[len(ch) // 4:]
la, ga = ch[:, names.index("J2043+1711_red_noise_log10_A")], ch[:, names.index("J2043+1711_red_noise_gamma")]

def nulls(count, draw):
    mx = np.empty(count); at37 = np.empty(count); k37 = int(np.argmin(np.abs(f - 1 / P0)))
    for i in range(count):
        A, g_ = draw()
        d = L @ rng.standard_normal(rows)
        if A is not None: d = d + F @ (np.sqrt(phi(A, g_)) * rng.standard_normal(2 * modes))
        s = white.stat(d); mx[i] = s[elig].max(); at37[i] = s[k37]
    return {"count": count, "max_quantiles_50_90_99": [float(np.quantile(mx, q)) for q in (0.5, 0.9, 0.99)],
            "fraction_max_ge_union_threshold_23.998": float((mx >= THRESHOLD).mean()), "fraction_max_ge_observed_26.87": float((mx >= 26.866).mean()),
            "mean_cell_stat_at_37.48": float(at37.mean())}
out["null_white_only(check against calibration: 99% = 20.46)"] = nulls(4000, lambda: (None, None))
def post():
    i = rng.integers(len(la)); return la[i], ga[i]
out["null_red_drawn_from_released_wb_chain"] = nulls(8000, post)
for A, g_ in ((-15.0, 13 / 3), (-14.6, 13 / 3), (-14.3, 13 / 3), (-14.0, 13 / 3), (-14.5, 3.5), (-14.1, 2.5), (-14.0, 1.5), (-14.0, 3.65)):
    out["null_red_fixed_logA%.1f_g%.2f" % (A, g_)] = nulls(3000, lambda: (A, g_))

# real-signal control: inject the best-fit 37.48 d sinusoid into white noise; how much does modelling red noise lower it?
Tm = tmpl(t, 37.48056, rows); d0, c0, _ = white.g.fit(y, Tm); model = Tm @ c0
alts = {"red_logA-14.6_g4.33": GLS(C + (F * phi(-14.6, 13 / 3)) @ F.T, D), "red_logA-15_g4.33": GLS(C + (F * phi(-15, 13 / 3)) @ F.T, D),
        "free_lowest_mode": GLS(C, np.column_stack([D, F[:, :2] / np.linalg.norm(F[:, :2], axis=0)])),
        "free_lowest_3_modes": GLS(C, np.column_stack([D, F[:, :6] / np.linalg.norm(F[:, :6], axis=0)]))}
obs_ratio = {k: g.fit(y, Tm)[0] / d0 for k, g in alts.items()}
obs_low = {"free_lowest_mode": white.g.fit(y, F[:, :2])[0], "free_lowest_3_modes": white.g.fit(y, F[:, :6])[0]}
sim = {k: [] for k in alts}; low = {k: [] for k in obs_low}; ws = []
for i in range(1500):
    d = model + L @ rng.standard_normal(rows)
    w0 = white.g.fit(d, Tm)[0]; ws.append(w0)
    for k, g in alts.items(): sim[k].append(g.fit(d, Tm)[0] / w0)
    low["free_lowest_mode"].append(white.g.fit(d, F[:, :2])[0]); low["free_lowest_3_modes"].append(white.g.fit(d, F[:, :6])[0])
out["real_signal_in_white_noise_control"] = {
    "sims": 1500, "white_stat_median": float(np.median(ws)),
    "ratio_stat_alt_over_white": {k: {"observed": float(obs_ratio[k]), "sim_quantiles_1_5_50_95": [float(np.quantile(v, q)) for q in (0.01, 0.05, 0.5, 0.95)],
                                      "fraction_sims_ratio_le_observed": float((np.array(v) <= obs_ratio[k]).mean())} for k, v in sim.items()},
    "low_mode_delta_chi2_with_signal_present_but_unmodelled": {k: {"observed": float(obs_low[k]), "sim_quantiles_50_95_99": [float(np.quantile(v, q)) for q in (0.5, 0.95, 0.99)],
                                                                    "fraction_sims_ge_observed": float((np.array(v) >= obs_low[k]).mean())} for k, v in low.items()}}
dump("05c_predictive.json", out); print(json.dumps(out, indent=1, default=float))
