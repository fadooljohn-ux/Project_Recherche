"""Check 3 (continued): red-noise mechanism, generic sensitivity loss, released noise chain. Review diagnostics only."""
import numpy as np
from common import *
a = arrays()
C, N, J, y, t = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"]
rows, n = len(C), len(t); out = {}
D = np.column_stack([N, J]); D = D / np.linalg.norm(D, axis=0)
P = 37.48056; Tm = tmpl(t, P, rows)
T = np.ptp(t); modes = int(np.ceil(T / 30.0)); fk = np.arange(1, modes + 1) / T
F = np.zeros((rows, 2 * modes)); ph = 2 * np.pi * np.outer(t - t.min(), fk); F[:n, 0::2], F[:n, 1::2] = np.sin(ph), np.cos(ph)
def red(log10A, gamma, kmax=modes, kmin=1):
    fhz = fk / 86400; fyrhz = 1 / (365.25 * 86400)
    phi = (10**log10A)**2 / (12 * np.pi**2) * fyrhz**(gamma - 3) * fhz**(-gamma) / (T * 86400)
    phi[kmax:] = 0; phi[:kmin - 1] = 0
    return C + (F * np.repeat(phi, 2)) @ F.T
g0 = GLS(C, D); d0, c0, cov0 = g0.fit(y, Tm); model = Tm @ c0
fine = np.linspace(1 / 37.75, 1 / 37.2, 45)
def stat(Cm, Dm=D):
    g = GLS(Cm, Dm); d, c, cov = g.fit(y, Tm); A, phs, sA, sp = amp_phase(c, cov)
    lam = g.fit(model, Tm)[0]            # noncentrality the released-noise best-fit signal would have under this model
    dl, _ = scan(g, y, t, fine, rows)
    return {"stat": d, "stat_local_max": float(dl.max()), "amp_us": A * 1e6, "amp_err_us": sA * 1e6, "phase": phs,
            "noiseless_model_noncentrality": lam, "generic_sensitivity_ratio": lam / d0, "observed_ratio": d / d0}
out["released"] = stat(C)
# (a) free low-frequency sinusoids as deterministic nuisance (the infinite-amplitude limit of red noise in those modes)
out["free_low_modes"] = {str(k): {**stat(C, np.column_stack([D, F[:, :2 * k] / np.linalg.norm(F[:, :2 * k], axis=0)])),
                                  "shortest_freed_period_d": float(1 / fk[k - 1]),
                                  "delta_chi2_of_modes": GLS(C, D).fit(y, F[:, :2 * k])[0], "dof": 2 * k} for k in (1, 2, 3, 5, 8, 10, 15, 20, 30)}
# (b) which modes matter: red noise restricted to bands
out["red_gamma4.33_logA-14.6_by_band"] = {"modes_%d_to_%d" % (lo, hi): stat(red(-14.6, 13 / 3, kmax=hi, kmin=lo)) for lo, hi in ((1, 111), (1, 3), (1, 10), (4, 10), (11, 111), (4, 111))}
out["red_examples"] = {"logA%.1f_g%.2f" % (la, ga): stat(red(la, ga)) for la, ga in ((-15, 13 / 3), (-14.6, 13 / 3), (-14, 13 / 3), (-14.5, 3.5), (-14, 2.5), (-14, 1.5), (-13.5, 1.5), (-14.1, 0.5))}
# (c) released NANOGrav noise chains (wideband and narrowband): red-noise posterior and the statistic over it
base = HERE / "ng15-extract/NANOGrav15yr_PulsarTiming_v2.1.0"
for kind in ("wideband", "narrowband"):
    tag = "wb" if kind == "wideband" else "nb"
    names = (base / kind / "noise" / f"J2043+1711.{tag}.pars.txt").read_text().split()
    ch = np.loadtxt(base / kind / "noise" / f"J2043+1711.{tag}.chain_1.txt")
    burn = len(ch) // 4; ch = ch[burn:]
    ig, ia = names.index("J2043+1711_red_noise_gamma"), names.index("J2043+1711_red_noise_log10_A")
    la, ga = ch[:, ia], ch[:, ig]
    r = {"columns": ch.shape[1], "named_parameters": len(names), "samples_after_burn": len(ch),
         "log10A_quantiles_5_50_95_99": [float(np.quantile(la, q)) for q in (0.05, 0.5, 0.95, 0.99)],
         "gamma_quantiles_5_50_95": [float(np.quantile(ga, q)) for q in (0.05, 0.5, 0.95)],
         "fraction_log10A_gt_-15": float((la > -15).mean()), "fraction_log10A_gt_-14": float((la > -14).mean()),
         "white_medians": {nm.replace("J2043+1711_", ""): float(np.median(ch[:, i])) for i, nm in enumerate(names) if "red" not in nm},
         "white_std": {nm.replace("J2043+1711_", ""): float(np.std(ch[:, i])) for i, nm in enumerate(names) if "efac" in nm and "PUPPI" in nm}}
    if kind == "wideband":
        idx = np.random.default_rng(20261118).choice(len(ch), 400, replace=False)
        s = np.array([stat(red(la[i], ga[i]))["stat_local_max"] for i in idx])
        r["statistic_over_400_posterior_red_samples"] = {"quantiles_5_25_50_75_95": [float(np.quantile(s, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)],
                                                           "fraction_below_union_threshold": float((s < THRESHOLD).mean()),
                                                           "fraction_below_empirical_99pct_20.458": float((s < 20.457684779563266).mean()), "min": float(s.min())}
        np.savez(HERE / "05b_chain_stat.npz", log10A=la[idx], gamma=ga[idx], stat=s)
    out["released_chain_" + kind] = r
dump("05b_red.json", out); print(json.dumps(out, indent=1, default=float))
