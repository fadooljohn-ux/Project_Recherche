"""Shared read-only loaders for the J2043+1711 review diagnostics (post-hoc, not a search)."""
import json
from pathlib import Path
import numpy as np
from scipy.linalg import cholesky, solve_triangular

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "nonlinear-held-20261117" / "j2043"
EPOCH = 57413.0
P0 = 37.48230065939762
THRESHOLD = 23.998096952191695


def arrays():
    with np.load(ROOT / "profile/arrays.npz", allow_pickle=False) as z:
        a = {k: z[k] for k in z.files}
    with np.load(ROOT / "prepared/observed.npz") as z:
        a["residuals"] = z["residuals"]
    with np.load(ROOT / "run01/periodogram.npz") as z:
        a["run_delta"] = z["delta_chi2"]; a["eligible"] = z["eligible"]; a["run_coeff"] = z["template_coefficients"]
    a["jac"] = a["surrogate_coefficients"][:, :len(a["orbit_lower"])]
    return a


def tmpl(times, period, rows):
    t = np.zeros((rows, 2))
    ph = 2 * np.pi * (times - EPOCH) / period
    t[:len(times), 0], t[:len(times), 1] = np.sin(ph), np.cos(ph)
    return t


class GLS:
    """Plain linearised GLS: delta chi2 for adding columns T to design D under covariance C."""
    def __init__(self, C, D):
        self.L = cholesky(C, lower=True)
        Dw = solve_triangular(self.L, D / np.linalg.norm(D, axis=0), lower=True)
        self.Q, r = np.linalg.qr(Dw)
        d = np.abs(np.diag(r)); assert d.min() > 1e-12 * d.max(), "rank"

    def proj(self, v):
        w = solve_triangular(self.L, v, lower=True)
        return w - self.Q @ (self.Q.T @ w)

    def chi2(self, y):
        w = self.proj(y); return float(w @ w)

    def fit(self, y, T):
        """Return delta chi2, coefficients, coefficient covariance for template columns T."""
        w, Tw = self.proj(y), self.proj(T)
        G = Tw.T @ Tw; b = Tw.T @ w
        cov = np.linalg.inv(G); c = cov @ b
        return float(b @ c), c, cov


def amp_phase(c, cov=None):
    a = float(np.hypot(*c)); ph = float(np.arctan2(c[1], c[0]))
    if cov is None:
        return a, ph
    g = np.array([c[0], c[1]]) / a
    sa = float(np.sqrt(g @ cov @ g))
    h = np.array([-c[1], c[0]]) / a**2
    sp = float(np.sqrt(h @ cov @ h))
    return a, ph, sa, sp


def dump(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=1, default=float))


def scan(g, y, times, freqs, rows, chunk=400, weight=None):
    """Vectorised linearised periodogram: delta chi2 and (sin, cos) coefficients at each frequency.
    weight: optional per-TOA multiplier of the template (e.g. a mask or chromatic scaling)."""
    w = g.proj(y); n = len(times)
    out = np.empty(len(freqs)); co = np.empty((len(freqs), 2))
    for s in range(0, len(freqs), chunk):
        f = freqs[s:s + chunk]
        ph = 2 * np.pi * np.outer(times - EPOCH, f)
        T = np.zeros((rows, 2 * len(f)))
        sc = 1.0 if weight is None else weight[:, None]
        T[:n, 0::2], T[:n, 1::2] = np.sin(ph) * sc, np.cos(ph) * sc
        Tw = g.proj(T)
        b = (Tw.T @ w).reshape(-1, 2)
        Tw = Tw.T.reshape(len(f), 2, rows)
        G = np.einsum("fin,fjn->fij", Tw, Tw)
        c = np.linalg.solve(G, b[..., None])[..., 0]
        out[s:s + chunk] = np.einsum("fi,fi->f", b, c); co[s:s + chunk] = c
    return out, co
