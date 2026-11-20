"""Refine a re-expressed orbit so that it reproduces the released model's delays.

The small-eccentricity re-expression uses the first-order relation between
the Keplerian and Laplace-Lagrange parameters. For wide, slightly eccentric
orbits the re-expressed model then starts a little away from the released
one (J1640+2224: 0.8 microseconds rms, removed to 0.002 by a small change of
parameters). This step adjusts the re-expressed orbital parameters by least
squares so that the re-expressed model's delay matches the released model's
at the observing times. It compares model with model: no residual and no
measured arrival-time information enters beyond the sampling.
"""
from __future__ import annotations

import numpy as np

PARAMETERS = ("TASC", "PB", "A1", "EPS1", "EPS2")
ITERATIONS = 6
CONVERGED = 1e-3          # stop when the rms difference changes by less than this fraction


def refine(delay, derivatives, target, start, iterations=ITERATIONS):
    """Gauss-Newton fit of `delay(values)` to `target` (both in seconds), with a free constant.

    delay(values) -> array; derivatives(values) -> (n, k) array of d delay / d value. Returns (values, record).
    """
    values = np.array(start, dtype=np.longdouble)
    difference = np.asarray(delay(values) - target, float)
    history = [float(np.std(difference))]
    for _ in range(iterations):
        columns = np.column_stack([np.ones(len(difference)), np.asarray(derivatives(values), float)])
        scale = np.linalg.norm(columns, axis=0)
        step = np.linalg.lstsq(columns / scale, difference, rcond=1e-14)[0] / scale
        trial = values - step[1:].astype(np.longdouble)
        new = np.asarray(delay(trial) - target, float)
        if not np.std(new) < history[-1]:
            break
        values, difference = trial, new
        history.append(float(np.std(difference)))
        if history[-2] - history[-1] < CONVERGED * history[-2]:
            break
    return values, {"rms_seconds_before": history[0], "rms_seconds_after": history[-1], "iterations": len(history) - 1}


def apply(model, released, toas, parameters=PARAMETERS):
    """Refine `model` (re-expressed) against `released` on the sampling of `toas`; returns the record."""
    import astropy.units as u

    names = [p for p in parameters if p in model.free_params]
    target = np.asarray(released.delay(toas).to_value(u.s), np.longdouble)
    units = [getattr(model, n).units for n in names]
    start = [getattr(model, n).value for n in names]

    def put(values):
        for name, value in zip(names, values):
            getattr(model, name).value = value

    def delay(values):
        put(values)
        return np.asarray(model.delay(toas).to_value(u.s), np.longdouble)

    def derivatives(values):
        put(values)
        return np.column_stack([np.asarray(model.d_delay_d_param(toas, n).to_value(u.s / unit), float)
                                for n, unit in zip(names, units)])

    values, record = refine(delay, derivatives, target, start)
    put(values)
    model.delay(toas)
    record["parameters"] = names
    record["change"] = {n: float(v - s) for n, v, s in zip(names, values, start)}
    record["rule"] = "Least-squares match of the re-expressed model's delay to the released model's, with a free constant"
    return record
