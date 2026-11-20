"""Check 3 (continued): short-period false-alarm rate of the frozen white-noise statistic under red noise, conditional on
the long-period part of the periodogram looking like the observed one. Linearised statistic. Review diagnostic only."""
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
g = GLS(C, D); L = g.L
Tm = np.zeros((rows, 2 * len(f))); p = 2 * np.pi * np.outer(t - EPOCH, f); Tm[:n, 0::2], Tm[:n, 1::2] = np.sin(p), np.cos(p)
Tw = g.proj(Tm); Gi = np.linalg.inv(np.einsum("nfi,nfj->fij", Tw.reshape(rows, len(f), 2), Tw.reshape(rows, len(f), 2)))
Fw = g.proj(F[:, :6]); G1 = np.linalg.inv(Fw[:, :2].T @ Fw[:, :2]); G3 = np.linalg.inv(Fw.T @ Fw)
short = elig & (1 / f < 100); long_ = elig & (1 / f >= 100)
def summary(d):
    w = g.proj(d); b = (Tw.T @ w).reshape(-1, 2); s = np.einsum("fi,fij,fj->f", b, Gi, b)
    b3 = Fw.T @ w
    return s[short].max(), s[long_].max(), b3[:2] @ G1 @ b3[:2], b3 @ G3 @ b3
o = summary(y); out["observed"] = {"short_max(P<100d)": o[0], "long_max(P>=100d)": o[1], "lowest_mode_dchi2": o[2], "lowest_3_modes_dchi2": o[3],
                                   "cells_short": int(short.sum()), "cells_long": int(long_.sum())}
rng = np.random.default_rng(2026111802)
base = HERE / "ng15-extract/NANOGrav15yr_PulsarTiming_v2.1.0/wideband/noise"
names = (base / "J2043+1711.wb.pars.txt").read_text().split(); ch = np.loadtxt(base / "J2043+1711.wb.chain_1.txt"); ch = ch[len(ch) // 4:]
la, ga = ch[:, names.index("J2043+1711_red_noise_log10_A")], ch[:, names.index("J2043+1711_red_noise_gamma")]
def run(count, draw):
    S = np.empty((count, 4)); pars = np.empty((count, 2))
    for i in range(count):
        A, g_ = draw(); pars[i] = A, g_
        S[i] = summary(L @ rng.standard_normal(rows) + F @ (np.sqrt(phi(A, g_)) * rng.standard_normal(2 * modes)))
    def rate(sel):
        k = int(sel.sum())
        return {"n": k, "short_max_ge_23.998": float((S[sel, 0] >= THRESHOLD).mean()) if k else None,
                "short_max_ge_26.87": float((S[sel, 0] >= 26.866).mean()) if k else None,
                "short_max_99pct": float(np.quantile(S[sel, 0], 0.99)) if k else None,
                "median_log10A": float(np.median(pars[sel, 0])) if k else None}
    return {"all": rate(np.ones(count, bool)),
            "long_max_le_15": rate(S[:, 1] <= 15),
            "long_max_le_15_and_low3_in_15_32": rate((S[:, 1] <= 15) & (S[:, 3] >= 15) & (S[:, 3] <= 32)),
            "low3_in_15_32": rate((S[:, 3] >= 15) & (S[:, 3] <= 32))}
out["white(logA=-25)"] = run(20000, lambda: (-25.0, 3.0))
def post():
    i = rng.integers(len(la)); return la[i], ga[i]
out["chain_drawn"] = run(40000, post)
for A, g_ in ((-15.3, 13 / 3), (-15.0, 13 / 3), (-14.8, 13 / 3), (-14.6, 13 / 3), (-14.5, 3.5), (-14.2, 2.5), (-14.0, 1.5), (-14.1, 0.5)):
    out["fixed_logA%.1f_g%.2f" % (A, g_)] = run(10000, lambda: (A, g_))
dump("05d_conditional.json", out); print(json.dumps(out, indent=1, default=float))
