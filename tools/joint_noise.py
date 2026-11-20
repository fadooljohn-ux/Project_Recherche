"""Bounded grid-profile likelihood with timing nuisance parameters marginalized.

The variable stochastic processes and circular signals affect TOA rows only.
Auxiliary measurements retain their fixed covariance and timing correlations.
No fitted noise waveform is subtracted from the observations.
"""
import numpy as np
from scipy.linalg import null_space, solve_triangular


class Contrast:
    """Remove timing columns and fixed-noise-only directions exactly once."""
    def __init__(self, base_covariance, design, toa_count):
        self.L = np.linalg.cholesky(base_covariance)
        norms = np.linalg.norm(design, axis=0)
        if np.any(norms == 0):
            raise ValueError('Zero timing column')
        x = solve_triangular(self.L, design / norms, lower=True)
        x /= np.linalg.norm(x, axis=0)
        q = null_space(x.T, rcond=1e-12)
        self.timing_rank = len(x) - q.shape[1]
        if self.timing_rank != x.shape[1]:
            raise ValueError('Joint noise comparison requires full-rank timing design')
        b = solve_triangular(self.L.T, q, lower=False).T
        u, s, _ = np.linalg.svd(b[:, :toa_count], full_matrices=False)
        rank = int(np.sum(s > s[0] * 1e-10))
        self.B = u[:, :rank].T @ b
        self.toa = self.B[:, :toa_count]
        self.dimension = rank
        np.testing.assert_allclose(self.B @ base_covariance @ self.B.T,
                                   np.eye(rank), rtol=1e-8, atol=1e-8)
        self.discarded_dimension = q.shape[1] - rank

    def covariance(self, red_covariance):
        return np.eye(self.dimension) + self.toa @ red_covariance @ self.toa.T

    def data(self, y):
        return self.B @ y


def evaluate(covariance, templates, samples):
    """One grid member, all periods and samples; includes covariance determinant.

Return null objective, each sample's best alternative, period index and fit.
The same timing integration measure is shared by every member. Common constants
and fixed-noise-only directions cancel from all objective differences.
"""
    l = np.linalg.cholesky(covariance)
    d, f, _ = templates.shape
    z = solve_triangular(l, templates.reshape(d, -1), lower=True).reshape(d, f, 2)
    gram = np.einsum('nfi,nfj->fij', z, z)
    eig = np.linalg.eigvalsh(gram)
    if np.any(eig[:, 0] <= eig[:, 1] * 1e-10):
        raise ValueError('An eligible signal cell lost rank under this noise member')
    inv = np.linalg.inv(gram)
    w = solve_triangular(l, samples, lower=True)
    null = np.sum(w*w, axis=0) + 2*np.log(np.diag(l)).sum()
    rhs = (z.reshape(d, -1).T @ w).reshape(f, 2, -1)
    beta = np.einsum('fij,fjb->fib', inv, rhs, optimize=True)
    score = np.einsum('fib,fib->fb', rhs, beta, optimize=True)
    peak = np.argmax(score, axis=0)
    columns = np.arange(samples.shape[1])
    return {'null': null, 'signal': null-score[peak, columns], 'peak': peak,
            'beta': beta[peak, :, columns], 'score': score,
            'observed_beta_grid': beta[:, :, 0], 'inverse_gram': inv}


def order_threshold(values, alpha):
    """Finite-sample upper order statistic; no extrapolation of a tiny tail."""
    v = np.sort(values)
    index = int(np.ceil((len(v)+1)*(1-alpha))) - 1
    if index >= len(v):
        raise ValueError('Too few nulls for the requested conditional allowance')
    return float(v[index])
