"""Check 1 (addendum): statistic with the orbit held fixed, and correlation of the 37.48 d template with orbital derivatives."""
import numpy as np
from common import *
a = arrays(); C, N, J, y, t = a["covariance"], a["nuisance"], a["jac"], a["residuals"], a["times"]; rows = len(C); Tm = tmpl(t, 37.48056, rows)
g1 = GLS(C, N); g2 = GLS(C, np.column_stack([N, J]))
T1 = g1.proj(Tm); T2 = g2.proj(Tm)
out = {"stat_orbit_fixed": g1.fit(y, Tm)[0], "stat_orbit_linearised": g2.fit(y, Tm)[0],
       "template_power_retained_after_orbit_projection": float((T2**2).sum() / (T1**2).sum()),
       "null_chi2_orbit_fixed": g1.chi2(y), "null_chi2_orbit_free": g2.chi2(y)}
dump("01b_orbit_fixed.json", out); print(json.dumps(out, indent=1))
