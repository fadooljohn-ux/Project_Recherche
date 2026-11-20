"""Check 3 (continued): statistic at the peak over joint white+red samples of the released NANOGrav wideband noise chain.
Review diagnostic only: the frozen search fixed the noise at the par-file values."""
import numpy as np
from common import *
a = arrays(); m = np.load(HERE / "meta.npz")
C, N, J, y, t = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"]
rows, n = len(C), len(t); out = {}
D = np.column_stack([N, J]); D = D / np.linalg.norm(D, axis=0)
T = np.ptp(t); modes = int(np.ceil(T / 30.0)); fk = np.arange(1, modes + 1) / T
F = np.zeros((rows, 2 * modes)); ph = 2 * np.pi * np.outer(t - t.min(), fk); F[:n, 0::2], F[:n, 1::2] = np.sin(ph), np.cos(ph)
def phi(log10A, gamma):
    fhz = fk / 86400; fyrhz = 1 / (365.25 * 86400)
    return np.repeat((10**log10A)**2 / (12 * np.pi**2) * fyrhz**(gamma - 3) * fhz**(-gamma) / (T * 86400), 2)
err = m["err_us"] * 1e-6; dme = m["flag_pp_dme"].astype(float); fl = m["flag_f"]
par = {"430_ASP": (0.9223454941439383, 0.13342801797293716, 1.1794475188302422, 6.266835272873465e-06),
       "430_PUPPI": (0.9632672567572883, 0.09856240216758863, 0.9433678912082092, 0.0001149232081701689),
       "L-wide_ASP": (0.987815021217935, 0.004481595974380615, 1.0023526248283214, 6.030718736243266e-07),
       "L-wide_PUPPI": (1.1795344190511778, 0.011615523574721025, 1.1332816074867993, 1.2676889214310924e-05)}
def white(p):
    d = np.empty(rows)
    for k, (ef, eq, def_, deq) in p.items():
        s = fl == k
        d[:n][s] = ef**2 * (err[s]**2 + (eq * 1e-6)**2); d[n:][s] = def_**2 * (dme[s]**2 + deq**2)
    return d
d0 = white(par); out["par_white_reproduces_saved_covariance_max_rel_diff"] = float(np.max(np.abs(d0 / np.diag(C) - 1)))
base = HERE / "ng15-extract/NANOGrav15yr_PulsarTiming_v2.1.0/wideband/noise"
names = [x.replace("J2043+1711_", "") for x in (base / "J2043+1711.wb.pars.txt").read_text().split()]
ch = np.loadtxt(base / "J2043+1711.wb.chain_1.txt"); ch = ch[len(ch) // 4:]
lnpost = ch[:, len(names)]; imap = int(np.argmax(lnpost))
def sample(i):
    v = dict(zip(names, ch[i]))
    return {k: (v[k + "_efac"], 10**v[k + "_log10_t2equad"] * 1e6, v[k + "_dmefac"], 10**v[k + "_log10_dmequad"]) for k in par}, v["red_noise_log10_A"], v["red_noise_gamma"]
out["chain_max_posterior_sample"] = {k: list(map(float, v)) for k, v in sample(imap)[0].items()}
out["chain_max_posterior_red"] = [float(x) for x in sample(imap)[1:]]
Tm = tmpl(t, 37.48056, rows); fine = np.linspace(1 / 37.75, 1 / 37.2, 23)
def stat(Cm):
    g = GLS(Cm, D); d, _ = scan(g, y, t, fine, rows); return float(d.max()), g.chi2(y)
rng = np.random.default_rng(2026111803); idx = rng.choice(len(ch), 500, replace=False)
res = {"white_only_from_chain": [], "white_and_red_from_chain": [], "chi2_white_only": []}
for i in idx:
    p, la, ga = sample(i); dw = white(p)
    s, c2 = stat(np.diag(dw)); res["white_only_from_chain"].append(s); res["chi2_white_only"].append(c2)
    res["white_and_red_from_chain"].append(stat(np.diag(dw) + (F * phi(la, ga)) @ F.T)[0])
EMP = 20.457684779563266
for k in ("white_only_from_chain", "white_and_red_from_chain"):
    v = np.array(res[k])
    out[k] = {"samples": len(v), "quantiles_5_25_50_75_95": [float(np.quantile(v, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)],
              "fraction_below_union_threshold_23.998": float((v < THRESHOLD).mean()), "fraction_below_empirical_99pct_20.458": float((v < EMP).mean())}
out["null_chi2_white_only_chain_quantiles_5_50_95"] = [float(np.quantile(res["chi2_white_only"], q)) for q in (0.05, 0.5, 0.95)]
p, la, ga = sample(imap); out["stat_at_chain_max_posterior"] = {"white_only": stat(np.diag(white(p)))[0], "white_and_red": stat(np.diag(white(p)) + (F * phi(la, ga)) @ F.T)[0]}
np.savez(HERE / "05e_chain_full.npz", idx=idx, **{k: np.array(v) for k, v in res.items()})
dump("05e_chain_full.json", out); print(json.dumps(out, indent=1, default=float))
