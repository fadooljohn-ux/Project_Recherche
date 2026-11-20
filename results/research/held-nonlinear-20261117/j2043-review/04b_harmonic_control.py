"""Check 2 (control): is the drop of the 37.48 d statistic when 8 orbital harmonics are freed specific to the real orbital period?
Repeat with fake 'orbital' periods. Review diagnostic only."""
import numpy as np
from common import *
a = arrays(); C, N, J, y, t = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"]
rows, n = len(C), len(t); D = np.column_stack([N, J]); Tm = tmpl(t, 37.48056, rows)
g0 = GLS(C, D); d0, c0, _ = g0.fit(y, Tm); model = Tm @ c0
def run(pb, ms=range(1, 9)):
    Z = np.zeros((rows, 2 * len(ms)))
    for i, k in enumerate(ms):
        ph = 2 * np.pi * k * (t - 57413.5013381163) / pb; Z[:n, 2 * i], Z[:n, 2 * i + 1] = np.sin(ph), np.cos(ph)
    g = GLS(C, np.column_stack([D, Z / np.linalg.norm(Z, axis=0)]))
    return g.fit(y, Tm)[0], g.fit(model, Tm)[0] / d0, g0.fit(y, Z)[0]
real = run(1.4822907863872236)
rng = np.random.default_rng(2026111805); fakes = rng.uniform(1.15, 1.95, 60)
res = np.array([run(p) for p in fakes])
out = {"real_PB_harmonics_1_to_8": {"stat_after": real[0], "generic_sensitivity_ratio": real[1], "harmonics_dchi2_16dof": real[2]},
       "fake_periods": {"count": len(fakes), "stat_after_quantiles_5_50_95": [float(np.quantile(res[:, 0], q)) for q in (0.05, 0.5, 0.95)],
                        "generic_ratio_quantiles_5_50_95": [float(np.quantile(res[:, 1], q)) for q in (0.05, 0.5, 0.95)],
                        "harmonics_dchi2_quantiles_5_50_95": [float(np.quantile(res[:, 2], q)) for q in (0.05, 0.5, 0.95)],
                        "fraction_fakes_with_stat_after_le_real": float((res[:, 0] <= real[0]).mean())}}
dump("04b_harmonic_control.json", out); print(json.dumps(out, indent=1, default=float))
