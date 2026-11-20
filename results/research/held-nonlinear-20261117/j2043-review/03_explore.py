import numpy as np
from common import *
m = np.load(HERE / "meta.npz"); a = arrays()
t = m["tdb"]; n = len(t)
print("names tail", m["names"][-4:], "orbphase range", m["orbphase"].min(), m["orbphase"].max())
for k in ("flag_f", "flag_fe", "flag_be", "obs"):
    u, c = np.unique(m[k], return_counts=True); print(k, dict(zip(u, c)))
for f in np.unique(m["flag_f"]):
    s = m["flag_f"] == f
    print(f, "n", s.sum(), "mjd", t[s].min().round(1), t[s].max().round(1), "median err us", np.median(m["err_us"][s]).round(3),
          "sigma_cov us", (np.sqrt(np.diag(a["covariance"])[:n][s]) * 1e6).round(3)[:3], "wrms us", (np.std(a["residuals"][:n][s]) * 1e6).round(3))
C = a["covariance"]; off = C - np.diag(np.diag(C)); print("max offdiag", np.abs(off).max(), "diag DM part", np.sqrt(np.diag(C)[n:])[:3])
day = np.floor(t + 0.5); ud, cnt = np.unique(day, return_counts=True)
print("distinct days", len(ud), "TOAs/day hist", np.bincount(cnt))
gaps = np.diff(ud); print("gap quantiles", np.quantile(gaps, [0, .1, .25, .5, .75, .9, 1]))
print("gap histogram (days: count)", {int(g): int(c) for g, c in zip(*np.unique(np.round(gaps), return_counts=True)) if c >= 3})
# DMX windows vs epochs
d = m["dmx"]; print("DMX n", len(d), "width quantiles", np.quantile(d[:, 2] - d[:, 1], [0, .5, 1]))
ep = np.array([np.argmax((d[:, 1] <= x) & (x <= d[:, 2])) for x in m["mjd"]]); u, c = np.unique(ep, return_counts=True)
print("TOAs per DMX bin hist", np.bincount(c)); 
fe_per = [len(set(m["flag_fe"][ep == e])) for e in u]; print("receivers per DMX bin hist", np.bincount(fe_per))
# local sidereal proxy: fraction of sidereal day
sid = (t * 1.0027379093) % 1; print("sidereal-day fraction: min/max/std(hours)", sid.min(), sid.max(), np.std(sid) * 24)
sol = t % 1; print("solar frac std hours", np.std(sol) * 24)
print("orbital phase hist (10 bins)", np.histogram(m["orbphase"] % 1, bins=10, range=(0, 1))[0])
print("freq MHz by fe", {f: (m["freq"][m["flag_fe"] == f].min().round(0), m["freq"][m["flag_fe"] == f].max().round(0)) for f in np.unique(m["flag_fe"])})
r = a["residuals"][:n] / np.sqrt(np.diag(C)[:n]); print("largest |z| time residuals", np.sort(np.abs(r))[-8:].round(2))
rd = a["residuals"][n:] / np.sqrt(np.diag(C)[n:]); print("largest |z| DM residuals", np.sort(np.abs(rd))[-8:].round(2), "DM resid unit sample", a["residuals"][n:n+3])
np.savez(HERE / "epochs.npz", ep=ep)
