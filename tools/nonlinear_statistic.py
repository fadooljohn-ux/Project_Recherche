"""Reusable periodic-signal statistic with a nonlinear orbit profiled at every period.

For a data vector y with covariance C, linear nuisance design N, a nonlinear
orbital delay d(x) and a two-column periodic template T_f, the statistic is

    delta_chi2(f) = min_x chi2(y - d(x) | N) - min_x chi2(y - d(x) | N, T_f)

so the orbit is re-fitted under both hypotheses and the linear terms stay
profiled in each. d(x) is a polynomial surrogate of the native delay; the
surrogate must be validated against the native delay before use. This module
is numerical machinery only: it reads no data and sets no threshold.
"""

from __future__ import annotations

from itertools import combinations_with_replacement

import numpy as np
from recherche_common import require
from scipy.linalg import cholesky, solve_triangular


def monomial_exponents(dimension, degree):
    """Exponent rows of every monomial of total degree 1..degree."""
    rows = []
    for order in range(1, degree + 1):
        for combo in combinations_with_replacement(range(dimension), order):
            row = np.zeros(dimension, dtype=int)
            for index in combo:
                row[index] += 1
            rows.append(row)
    return np.asarray(rows)


def extended_exponents(dimension, degree, pair, pair_degree):
    """All monomials to `degree`, plus every monomial in the `pair` parameters alone to `pair_degree`."""
    inner = monomial_exponents(len(pair), pair_degree)
    full = np.zeros((len(inner), dimension), dtype=int)
    full[:, list(pair)] = inner
    rows = np.unique(np.vstack([monomial_exponents(dimension, degree), full]), axis=0)
    # Linear terms first, in parameter order, so the leading columns are the Jacobian at the centre.
    order = np.lexsort((*(-rows.T[::-1]), rows.sum(axis=1)))
    return rows[order]


def monomials(x, exponents):
    """Monomial values, shape (..., M), for points x of shape (..., d)."""
    x = np.asarray(x, float)
    return np.prod(x[..., None, :] ** exponents, axis=-1)


def monomial_gradients(x, exponents):
    """Derivatives of each monomial, shape (..., M, d)."""
    x = np.asarray(x, float)
    out = np.empty(x.shape[:-1] + exponents.shape)
    for k in range(exponents.shape[1]):
        lowered = exponents.copy()
        lowered[:, k] = np.maximum(lowered[:, k] - 1, 0)
        out[..., k] = exponents[:, k] * np.prod(x[..., None, :] ** lowered, axis=-1)
    return out


class PolynomialDelay:
    """Least-squares polynomial surrogate d(x) = coefficients @ monomials(x), with d(0) = 0."""

    def __init__(self, coefficients, exponents, lower, upper):
        self.coefficients = np.asarray(coefficients, float)
        self.exponents = np.asarray(exponents, int)
        self.lower, self.upper = np.asarray(lower, float), np.asarray(upper, float)
        require(self.coefficients.shape[1] == len(self.exponents), "Coefficient and monomial counts differ")

    @classmethod
    def fit(cls, delay, lower, upper, degree, points, exponents=None):
        """Fit to delay(x) at the supplied points; delay(0) must be zero."""
        lower, upper = np.asarray(lower, float), np.asarray(upper, float)
        points = np.asarray(points, float)
        require(np.all(points >= lower) and np.all(points <= upper), "Training point outside the domain")
        if exponents is None:
            exponents = monomial_exponents(len(lower), degree)
        basis = monomials(points, exponents)
        require(len(points) >= 2 * basis.shape[1], "Too few training points for this degree")
        require(np.linalg.matrix_rank(basis) == basis.shape[1], "Training points do not determine the polynomial")
        values = np.stack([delay(p) for p in points])
        coefficients = np.linalg.lstsq(basis, values, rcond=None)[0].T
        return cls(coefficients, exponents, lower, upper)

    def __call__(self, x):
        return self.coefficients @ monomials(x, self.exponents)


def sample_domain(lower, upper, count, seed):
    """Uniform points in the box, with the centre and the 2d face centres included first."""
    lower, upper = np.asarray(lower, float), np.asarray(upper, float)
    generator = np.random.default_rng(seed)
    points = generator.uniform(lower, upper, size=(count, len(lower)))
    faces = []
    for k in range(len(lower)):
        for bound in (lower[k], upper[k]):
            face = np.zeros(len(lower))
            face[k] = bound
            faces.append(face)
    fixed = np.asarray(faces)[: max(0, count)]
    points[: len(fixed)] = fixed
    return points


class NonlinearScan:
    """Profile a polynomial orbit and linear nuisance terms under null and periodic hypotheses."""

    def __init__(self, covariance, nuisance, delay, templates, *, rank_tolerance=1e-9,
                 maximum_iterations=200, step_tolerance=1e-7):
        """templates has shape (n, F, 2): the two periodic columns at each trial frequency."""
        self.delay = delay
        self.L = cholesky(covariance, lower=True)
        scaled = nuisance / np.linalg.norm(nuisance, axis=0)
        self.Q, triangular = np.linalg.qr(self.white(scaled), mode="reduced")
        diagonal = np.abs(np.diag(triangular))
        require(diagonal.min() > 1e-12 * diagonal.max(), "Linear nuisance design lost rank")
        # Orthonormal basis B of the projected, whitened surrogate columns: P d(x) = B (A @ monomials).
        projected = self.project(delay.coefficients)
        reach = np.max(np.abs(monomials(np.stack([delay.lower, delay.upper]), delay.exponents)), axis=0)
        left, singular, right = np.linalg.svd(projected * reach, full_matrices=False)
        keep = singular > rank_tolerance * singular[0]
        self.B = left[:, keep]
        self.A = (singular[keep, None] * right[keep]) / reach
        self.discarded_surrogate_norm = float(np.sqrt(np.sum(singular[~keep] ** 2)))
        # Orthonormal template pairs U_f after nuisance projection, and their overlap with B.
        n, count, pair = templates.shape
        require(pair == 2 and n == len(self.L), "Templates must have shape (n, F, 2)")
        projected = self.project(templates.reshape(n, -1)).reshape(n, count, 2)
        gram = np.einsum("nfi,nfj->fij", projected, projected)
        values, vectors = np.linalg.eigh(gram)
        require(values[:, 0].min() > 1e-10 * values[:, 1].max(), "A periodic template is degenerate with the nuisance design")
        self.template_transform = vectors / np.sqrt(values)[:, None, :]
        self.U = np.einsum("nfi,fij->nfj", projected, self.template_transform)
        self.M = np.einsum("nfi,nr->fir", self.U, self.B)
        self.S = np.eye(self.B.shape[1]) - np.einsum("fir,fis->frs", self.M, self.M)
        self.maximum_iterations, self.step_tolerance = maximum_iterations, step_tolerance

    def white(self, values):
        return solve_triangular(self.L, values, lower=True)

    def project(self, values):
        whitened = self.white(values)
        return whitened - self.Q @ (self.Q.T @ whitened)

    def _minimise(self, start, target, metric=None, linear=None):
        """Minimise e'Se - 2 linear'e with e = target - A phi(x), for K box-bounded problems at once.

        target (r,), metric (K, r, r) or None for the identity, linear (K, r) or None for zero.
        """
        x = np.array(start, float)
        lower, upper = self.delay.lower, self.delay.upper

        def evaluate(points, rows):
            error = target - monomials(points, self.delay.exponents) @ self.A.T
            weighted = error if metric is None else np.einsum("krs,ks->kr", metric[rows], error)
            value = np.einsum("kr,kr->k", error, weighted)
            if linear is not None:
                value = value - 2 * np.einsum("kr,kr->k", linear[rows], error)
            return error, weighted, value

        error, weighted, value = evaluate(x, slice(None))
        damping = np.full(len(x), 1e-3)
        active = np.ones(len(x), bool)
        iterations = np.zeros(len(x), int)
        for _ in range(self.maximum_iterations):
            if not active.any():
                break
            rows = np.flatnonzero(active)
            jacobian = np.einsum("rm,kmj->krj", self.A, monomial_gradients(x[rows], self.delay.exponents))
            pull = weighted[rows] if linear is None else weighted[rows] - linear[rows]
            gradient = np.einsum("krj,kr->kj", jacobian, pull)
            scaled = jacobian if metric is None else np.einsum("krs,ksj->krj", metric[rows], jacobian)
            hessian = np.einsum("krj,kri->kji", jacobian, scaled)
            diagonal = np.einsum("kjj->kj", hessian)
            hessian = hessian + damping[rows, None, None] * (np.eye(x.shape[1]) * np.maximum(diagonal, 1e-12)[:, None, :])
            # Active set: a parameter on a bound whose descent direction points outward stays fixed.
            fixed = ((x[rows] <= lower) & (gradient < 0)) | ((x[rows] >= upper) & (gradient > 0))
            gradient = np.where(fixed, 0.0, gradient)
            free = ~fixed
            hessian = hessian * (free[:, :, None] & free[:, None, :]) + np.eye(x.shape[1]) * fixed[:, None, :]
            step = np.linalg.solve(hessian, gradient[..., None])[..., 0]
            trial = np.clip(x[rows] + step, lower, upper)
            moved = np.max(np.abs(trial - x[rows]), axis=1)
            trial_error, trial_weighted, trial_value = evaluate(trial, rows)
            better = trial_value <= value[rows]
            accept = rows[better]
            x[accept], error[accept] = trial[better], trial_error[better]
            weighted[accept], value[accept] = trial_weighted[better], trial_value[better]
            damping[rows] = np.where(better, damping[rows] / 10, damping[rows] * 10)
            iterations[rows] += 1
            # Converged when an accepted step is negligible; abandoned when damping can no longer help.
            active[rows[better & (moved < self.step_tolerance)]] = False
            active[rows[~better & (damping[rows] > 1e12)]] = False
        return x, value, iterations, active

    def scan(self, data):
        """Return the statistic for one data vector at every template frequency."""
        whitened = self.project(np.asarray(data, float))
        c = self.B.T @ whitened
        outside = float(whitened @ whitened - c @ c)
        u = np.einsum("nfi,n->fi", self.U, whitened) - self.M @ c
        null_x, null_value, null_iterations, null_active = self._minimise(np.zeros((1, len(self.delay.lower))), c)
        count = len(self.U[0])
        start = np.repeat(null_x, count, axis=0)
        linear = np.einsum("fir,fi->fr", self.M, u)
        x, value, iterations, active = self._minimise(start, c, metric=self.S, linear=linear)
        # chi2_alt = outside + e'Se - 2 (M'u)'e - u'u ; chi2_null = outside + e0'e0.
        alternative = value - np.einsum("fi,fi->f", u, u)
        error = c - monomials(x, self.delay.exponents) @ self.A.T
        orthonormal = u + np.einsum("fir,fr->fi", self.M, error)
        edge = np.minimum(x - self.delay.lower, self.delay.upper - x).min(axis=1) < 1e-6
        return {
            "delta_chi2": float(null_value[0]) - alternative,
            "null_chi2": outside + float(null_value[0]),
            "null_orbit": null_x[0],
            "orbit": x,
            "template_coefficients": np.einsum("fij,fj->fi", self.template_transform, orthonormal),
            "iterations": iterations,
            "unconverged": active | bool(null_active[0]),
            "on_boundary": edge,
            "null_on_boundary": bool(np.minimum(null_x[0] - self.delay.lower, self.delay.upper - null_x[0]).min() < 1e-6),
        }


def periodic_templates(times, frequencies, epoch, rows):
    """Sine and cosine columns in the first len(times) rows of an (rows, F, 2) array."""
    phase = 2 * np.pi * np.outer(np.asarray(times, float) - epoch, frequencies)
    out = np.zeros((rows, len(frequencies), 2))
    out[: len(times), :, 0], out[: len(times), :, 1] = np.sin(phase), np.cos(phase)
    return out
