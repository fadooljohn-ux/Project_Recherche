"""Check 5: consistency across subsets and jackknife influence. Review diagnostics only."""
import numpy as np
from scipy.stats import chi2 as chi2dist
from common import *
a = arrays(); m = np.load(HERE / "meta.npz"); ep = np.load(HERE / "epochs.npz")["ep"]
C, N, J, y, t = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"]
rows, n = len(C), len(t); out = {}
D = np.column_stack([N, J]); P = 37.48056; Tm = tmpl(t, P, rows)
g = GLS(C, D); d0, c0, cov0 = g.fit(y, Tm); w = g.proj(y); Tw = g.proj(Tm)
out["baseline"] = {"stat": d0, "amp_us": float(np.hypot(*c0) * 1e6)}

# (a) split fits: separate sinusoid coefficients per subset inside the full nuisance model
def split(label, groups):
    cols = np.column_stack([Tm * np.concatenate([s, np.zeros(n, bool)])[:, None] for s in groups.values()])
    d, c, cov = g.fit(y, cols); k = len(groups); r = {"stat_%ddof" % (2 * k): d, "improvement_over_common": d - d0}
    # consistency: chi2 of the hypothesis that all subsets share one coefficient pair
    r["consistency_chi2"] = d - d0; r["consistency_dof"] = 2 * (k - 1); r["consistency_p"] = float(chi2dist.sf(d - d0, 2 * (k - 1)))
    for i, (name, s) in enumerate(groups.items()):
        A, ph, sA, sp = amp_phase(c[2 * i:2 * i + 2], cov[2 * i:2 * i + 2, 2 * i:2 * i + 2])
        info = float(np.einsum("ij,ij->", g.proj(cols[:, 2 * i:2 * i + 2]), g.proj(cols[:, 2 * i:2 * i + 2])) / np.einsum("ij,ij->", Tw, Tw))
        r[name] = {"toas": int(s.sum()), "amp_us": A * 1e6, "amp_err_us": sA * 1e6, "phase": ph, "phase_err": sp, "own_stat": g.fit(y, cols[:, 2 * i:2 * i + 2])[0], "information_share": info}
    return r
tmid = np.median(t); q = np.quantile(t, [1 / 3, 2 / 3]); q4 = np.quantile(t, [0.25, 0.5, 0.75])
snr = m["flag_snr"].astype(float); orb = m["orbphase"] % 1; doy = (t - 51544.5) % 365.25; sid = (t * 1.0027379093) % 1
fe = m["flag_fe"]; Lw = fe == "L-wide"
S = {}
S["receiver"] = split("receiver", {"430": fe == "430", "L-wide": Lw})
S["backend"] = split("backend", {"ASP": m["flag_be"] == "ASP", "PUPPI": m["flag_be"] == "PUPPI"})
S["time_halves"] = split("halves", {"first": t < tmid, "second": t >= tmid})
S["time_thirds"] = split("thirds", {"t1": t < q[0], "t2": (t >= q[0]) & (t < q[1]), "t3": t >= q[1]})
S["time_quarters"] = split("quarters", {"q1": t < q4[0], "q2": (t >= q4[0]) & (t < q4[1]), "q3": (t >= q4[1]) & (t < q4[2]), "q4": t >= q4[2]})
S["orbital_phase_halves"] = split("orb", {"phase_0_0.5": orb < 0.5, "phase_0.5_1": orb >= 0.5})
S["near_superior_conjunction(0.15-0.35)"] = split("conj", {"near": (orb > 0.15) & (orb < 0.35), "far": ~((orb > 0.15) & (orb < 0.35))})
S["season_halves"] = split("season", {"doy_lt_182": doy < 182.6, "doy_ge_182": doy >= 182.6})
S["hour_angle_halves"] = split("ha", {"early": sid < np.median(sid), "late": sid >= np.median(sid)})
medL = np.median(snr[Lw]); med4 = np.median(snr[~Lw])
hi = np.where(Lw, snr >= medL, snr >= med4)
S["snr_halves(per receiver)"] = split("snr", {"high_snr": hi, "low_snr": ~hi})
S["odd_even_epochs"] = split("oddeven", {"even": ep % 2 == 0, "odd": ep % 2 == 1})
out["splits"] = S
out["observatory_split"] = "not possible: all 459 TOAs are from Arecibo"

# (b) leave-one-epoch-out via indicator columns (deleting rows == giving each its own free parameter)
def without(row_idx):
    E = np.zeros((rows, len(row_idx))); E[row_idx, np.arange(len(row_idx))] = 1
    Ew = g.proj(E); u, s, _ = np.linalg.svd(Ew, full_matrices=False); u = u[:, s > 1e-9]
    w2 = w - u @ (u.T @ w); T2 = Tw - u @ (u.T @ Tw); b = T2.T @ w2; c = np.linalg.solve(T2.T @ T2, b)
    return float(b @ c), c
def epoch_rows(es):
    sel = np.isin(ep, es); return np.concatenate([np.flatnonzero(sel), n + np.flatnonzero(sel)])
ne = ep.max() + 1
def jack(yv):
    wv = g.proj(yv)
    full = None
    drops = np.empty(ne)
    global w
    keep = w; w = wv
    b = Tw.T @ wv; full = float(b @ np.linalg.solve(Tw.T @ Tw, b))
    for e in range(ne): drops[e] = full - without(epoch_rows([e]))[0]
    order = np.argsort(drops)[::-1]
    cum = [full - without(epoch_rows(order[:k]))[0] for k in (1, 3, 5, 10, 20)]
    w = keep
    return full, drops, order, cum
full, drops, order, cum = jack(y)
tde = np.array([t[ep == e].mean() for e in range(ne)])
out["leave_one_epoch_out"] = {
    "epochs": int(ne), "stat_min": float(full - drops.max()), "stat_max": float(full - drops.min()),
    "epochs_whose_removal_alone_drops_below_23.998": int((full - drops < THRESHOLD).sum()),
    "top10": [{"epoch_mjd": float(tde[e]), "toas": int((ep == e).sum()), "stat_without": float(full - drops[e]), "drop": float(drops[e])} for e in order[:10]],
    "most_negative(removal raises stat)": [{"epoch_mjd": float(tde[e]), "stat_without": float(full - drops[e])} for e in order[-3:]],
    "stat_after_removing_top_k_(one-shot ranking)": dict(zip(["1", "3", "5", "10", "20"], [float(full - c) for c in cum])),
    "fraction_of_stat_removed_top_k": dict(zip(["1", "3", "5", "10", "20"], [float(c / full) for c in cum]))}
# greedy: how many epochs to bring below the union threshold and below 20.46
removed = []; cur = full; trace = []
while cur >= 20.457684779563266 and len(removed) < 40:
    best = None
    cand = order[:60]
    for e in cand:
        if e in removed: continue
        s = without(epoch_rows(removed + [int(e)]))[0]
        if best is None or s < best[0]: best = (s, int(e))
    removed.append(best[1]); cur = best[0]; trace.append([len(removed), float(tde[best[1]]), cur])
out["greedy_removal"] = {"epochs_to_fall_below_23.998": next(k for k, _, s in trace if s < THRESHOLD), "epochs_to_fall_below_20.458": len(removed), "trace": trace}
# control: same influence measures for a real 37.48 d signal of the fitted amplitude in white released noise
rng = np.random.default_rng(2026111804); model = Tm @ c0; ctl = {"top1": [], "top5": [], "top10": [], "full": []}
for i in range(300):
    f2, dr, od, cm = jack(model + g.L @ rng.standard_normal(rows))
    ctl["full"].append(f2); ctl["top1"].append(cm[0] / f2); ctl["top5"].append(cm[2] / f2); ctl["top10"].append(cm[3] / f2)
obs = {"top1": cum[0] / full, "top5": cum[2] / full, "top10": cum[3] / full}
out["influence_control_real_signal_white_noise"] = {"sims": 300, **{k: {"observed_fraction_removed": float(obs[k]),
    "sim_quantiles_5_50_95": [float(np.quantile(ctl[k], q)) for q in (0.05, 0.5, 0.95)], "fraction_sims_ge_observed": float((np.array(ctl[k]) >= obs[k]).mean())} for k in obs}}
# same for pure noise maxima? (a noise peak of the same height at this fixed period): condition on stat >= 20 is too rare to sample; not done.

# (c) leave-one-calendar-year-out and cumulative growth
yr = np.floor((tde - 55197.0) / 365.25).astype(int) + 2010
out["leave_one_year_out"] = {str(int(v)): {"epochs": int((yr == v).sum()), "stat_without": without(epoch_rows(np.flatnonzero(yr == v)))[0],
                                           "amp_us_without": float(np.hypot(*without(epoch_rows(np.flatnonzero(yr == v)))[1]) * 1e6)} for v in np.unique(yr)}
grow = {}
for frac in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
    k = int(round(frac * ne)); late = np.flatnonzero(np.argsort(np.argsort(tde)) >= k)
    s, c = (full, c0) if len(late) == 0 else without(epoch_rows(late))
    grow["first_%d%%_epochs" % (frac * 100)] = {"stat": s, "amp_us": float(np.hypot(*c) * 1e6), "phase": float(np.arctan2(c[1], c[0]))}
out["cumulative_growth"] = grow
# (d) the single largest outlier TOA and TOAs with |z|>2.5
z = y[:n] / np.sqrt(np.diag(C)[:n]); big = np.flatnonzero(np.abs(z) > 2.5)
out["without_toas_|z|>2.5"] = {"count": int(len(big)), "stat": without(np.concatenate([big, n + big]))[0]}
np.savez(HERE / "07_jackknife.npz", epoch_mjd=tde, drop=drops)
dump("07_subsets.json", out); print(json.dumps(out, indent=1, default=float))
