"""Nonlinear treatment of free Shapiro-delay parameters: a verified basis instead of derivative columns.

The search removes the inner orbit by projecting one derivative column per free
parameter, which is only valid where the arrival times are linear in that
parameter. Shapiro-delay shape parameters (M2/SINI, H3/STIGMA, H3/H4) are often
too uncertain or too curved for that, and the target is held.

Here the Shapiro parameters are frozen at the released values and the set of
values the data could still allow is treated as a whole:

neighbourhood  every physical combination of the Shapiro parameters whose
               change in arrival times, after the projection the search
               applies, is within 3 sigma of the released model under the
               search covariance (expected chi-square change <= 9), together
               with the box of three released uncertainties. For a linear
               parameter this is exactly +-3 times its uncertainty under the
               search covariance; unlike a per-parameter box it follows the
               correlation between the parameters.
basis          the leading principal directions of the arrival-time changes
               over a grid of the neighbourhood are added to the design as
               nuisance columns.
acceptance     at independent random points of the neighbourhood, what the
               basis leaves unremoved must be below the 0.1 TOA-sigma bound the
               local-linearity check uses; and the values the data prefer
               (chi-square minimum over the whole grid) must lie inside the
               neighbourhood.

Reads no periodogram.
"""
from __future__ import annotations

import itertools

import numpy as np
from scipy.linalg import cholesky, solve_triangular

PARAMETERS = ("M2", "SINI", "H3", "H4", "STIGMA")
# Physical limits. The upper limits on SINI and STIGMA both correspond to cos(i) of about 1e-3. STIGMA = 0
# (face-on) is singular in the H3/STIGMA form (the companion mass is H3 / STIGMA^3), so it stops at 0.02.
BOUNDS = {"M2": (0.0, np.inf), "SINI": (0.0, 1 - 5e-7), "STIGMA": (0.02, 0.999), "H3": (-np.inf, np.inf),
          "H4": (-np.inf, np.inf)}
LIMIT = 0.1              # TOA sigma left unremoved at any test point
GRID = 41                # points per parameter across the sampled range
REGION = 9.0             # expected chi-square change bounding the neighbourhood (3 sigma for one parameter)
MINIMUM_GRID_POINTS = 12
MAX_TRIES = 20000
TESTS = 64               # independent random points
MAX_COMPONENTS = 12
DERIVATIVE_STEP = 0.03   # of the released uncertainty, for the width estimate only


def whitened_projector(design, lower):
    whitened = solve_triangular(lower, design, lower=True)
    q, _ = np.linalg.qr(whitened / np.linalg.norm(whitened, axis=0))
    return q


def own_uncertainty(design, extra, lower):
    """Uncertainty of each extra column when fitted together with the design under the covariance."""
    whitened = solve_triangular(lower, np.column_stack([design, extra]), lower=True)
    norm = np.linalg.norm(whitened, axis=0)
    normalized = whitened / norm
    if np.linalg.matrix_rank(normalized) != normalized.shape[1]:
        raise ValueError("Shapiro parameters are not separable from the rest of the timing model")
    own = np.sqrt(np.diag(np.linalg.inv(normalized.T @ normalized))) / norm
    return own[design.shape[1]:]


def build(change, start, design, covariance, residuals, seed, limit=LIMIT, max_components=MAX_COMPONENTS):
    """Return (basis columns in seconds, report).

    change(values) gives the change in model delay (seconds) when the named parameters take the given
    values; start maps each free Shapiro parameter to (released value, released uncertainty).
    """
    names = list(start)
    for name, (value, uncertainty) in start.items():
        if uncertainty is None or not uncertainty > 0:
            raise ValueError("Released Shapiro uncertainty missing: " + name)
        if name in ("SINI", "STIGMA") and not 0 <= value <= 1:
            raise ValueError("Released Shapiro value outside its physical range: " + name)
    sigma = np.sqrt(np.diag(covariance))
    lower = cholesky(covariance, lower=True)
    q = whitened_projector(design, lower)

    def projected(delta):
        y = solve_triangular(lower, np.asarray(delta, float), lower=True)
        if not np.all(np.isfinite(y)):
            raise ValueError("Shapiro delay is not finite inside the sampled range")
        return y - q @ (q.T @ y)

    derivatives = []
    for name in names:
        value, uncertainty = start[name]
        step = DERIVATIVE_STEP * uncertainty
        high, low = min(value + step, BOUNDS[name][1]), max(value - step, BOUNDS[name][0])
        derivatives.append(np.asarray(change({name: high}) - change({name: low}), float) / (high - low))
    own = own_uncertainty(design, np.column_stack(derivatives), lower)
    width = {n: max(float(start[n][1]), float(o)) for n, o in zip(names, own)}
    edges = {n: (max(BOUNDS[n][0], start[n][0] - 3 * width[n]), min(BOUNDS[n][1], start[n][0] + 3 * width[n]))
             for n in names}

    def inside(point, change_norm2):
        released_box = all(abs(v - start[n][0]) <= 3 * start[n][1] for n, v in zip(names, point))
        return released_box or change_norm2 <= REGION

    axes = [np.linspace(*edges[n], GRID) for n in names]
    grid = list(itertools.product(*axes))
    raw_worst, columns, norm2, whitened = 0.0, [], [], []
    for point in grid:
        delta = np.asarray(change(dict(zip(names, point))), float)
        columns.append(projected(delta))
        whitened.append(solve_triangular(lower, delta, lower=True))
        norm2.append(float(columns[-1] @ columns[-1]))
        if inside(point, norm2[-1]):
            raw_worst = max(raw_worst, float(np.max(abs(delta - delta.mean()) / sigma)))
    kept = [j for j, point in enumerate(grid) if inside(point, norm2[j])]
    if len(kept) < MINIMUM_GRID_POINTS:
        raise ValueError(f"Shapiro neighbourhood too thin to sample: {len(kept)} grid points")
    u, singular, vt = np.linalg.svd(np.column_stack([columns[j] for j in kept]), full_matrices=False)
    usable = int(np.sum(singular > 1e-9 * singular[0])) if singular[0] > 0 else 0
    generator = np.random.default_rng(seed)
    tests, tries = [], 0
    while len(tests) < TESTS:
        tries += 1
        if tries > MAX_TRIES:
            raise ValueError(f"Shapiro neighbourhood too thin to test: {len(tests)} points in {MAX_TRIES} tries")
        point = tuple(generator.uniform(*edges[n]) for n in names)
        t = projected(change(dict(zip(names, point))))
        if inside(point, float(t @ t)):
            tests.append(t)
    for count in range(0, min(max_components, usable) + 1):
        basis = u[:, :count]
        worst = max(float(np.max(abs(lower @ (t - basis @ (basis.T @ t))) / sigma)) for t in tests)
        if worst <= limit:
            break
    else:
        raise ValueError(f"Shapiro basis leaves {worst:.3g} TOA sigma unremoved with {count} components")
    # Where the data put the Shapiro parameters: chi-square over the whole grid (no periodogram).
    y = projected(residuals)
    chi2 = np.array([float((y - c) @ (y - c)) for c in columns])
    best = int(np.argmin(chi2))
    shifts = {n: float((v - start[n][0]) / width[n]) for n, v in zip(names, grid[best])}
    if best not in kept:
        raise ValueError("Data prefer Shapiro parameters outside the checked neighbourhood: " + ", ".join(
            f"{n} {v:+.2f} widths" for n, v in shifts.items()) + f"; expected chi-square change {norm2[best]:.1f}")
    report = {
        "parameters": names, "released": {n: [float(start[n][0]), float(start[n][1])] for n in names},
        "uncertainty_under_search_covariance": {n: float(o) for n, o in zip(names, own)},
        "sampled_range": {n: [float(edges[n][0]), float(edges[n][1])] for n in names},
        "neighbourhood_range": {n: [float(min(grid[j][a] for j in kept)), float(max(grid[j][a] for j in kept))]
                                for a, n in enumerate(names)},
        "neighbourhood": "Expected chi-square change <= %g under the search covariance, or within three released "
                         "uncertainties; physical values only" % REGION,
        "grid_points": len(grid), "grid_points_in_neighbourhood": len(kept), "test_points": TESTS,
        "test_point_tries": tries, "components": int(count), "singular_values": [float(v) for v in singular[:count + 3]],
        "largest_change_before_projection_in_TOA_sigma": raw_worst,
        "largest_unremoved_at_test_points_in_TOA_sigma": worst, "limit_in_TOA_sigma": limit,
        "data_preferred_shift_in_widths": shifts, "data_preferred_expected_chi2_change": norm2[best],
        "chi2_released_minus_preferred": float(y @ y - chi2[best]),
        "rule": "Shapiro parameters frozen at the released values; principal directions of the arrival-time change "
                "over the neighbourhood projected as nuisance columns; accepted on independent test points"}
    # The columns handed to the search are the same combinations of the unprojected changes. With the design
    # they span exactly what was tested, and they keep the correlation between the Shapiro freedom and the
    # other orbital parameters, so those parameters' uncertainties under the search covariance stay marginal.
    combined = np.column_stack([whitened[j] for j in kept]) @ (vt[:count].T / singular[:count])
    return lower @ combined, report
