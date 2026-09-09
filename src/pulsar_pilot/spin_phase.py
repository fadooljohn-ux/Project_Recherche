"""Preserve fractional spin phase before PINT combines phase components.

Long-double evaluation of a many-billion-turn polynomial rounds away small
changes before Phase can separate integer and fractional turns. Evaluate that
same polynomial with Decimal, then pass its two parts separately to PINT.
This binding is local to a model; the installed PINT package is unchanged.
"""

from decimal import Decimal, localcontext
from types import MethodType
from typing import Any

import astropy.units as u
import numpy as np

PHASE_DECIMAL_PRECISION = 50


def _decimal(value: Any) -> Decimal:
    numerator, denominator = np.longdouble(value).as_integer_ratio()
    return Decimal(numerator) / Decimal(denominator)


def spin_phase_parts(spin: Any, toas: Any, delay: u.Quantity) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate the existing spin Taylor polynomial without merging its parts.

    Use exact binary input ratios rather than decimal string conversions. Keep
    the day-to-second conversion and delay subtraction at extended precision
    too: rounding dt first would lose the same small timing changes.
    """
    with localcontext() as context:
        context.prec = PHASE_DECIMAL_PRECISION
        epoch = _decimal(spin.PEPOCH.quantity.tdb.mjd_long)
        coefficients = [
            _decimal(term.to_value(u.Hz / u.s**order))
            for order, term in enumerate(spin.get_spin_terms())
        ]
        integer = np.empty(len(toas.table["tdbld"]), dtype=np.longdouble)
        fractional = np.empty_like(integer)
        for index, (tdb, lag) in enumerate(zip(toas.table["tdbld"], delay.to_value(u.s), strict=True)):
            dt = (_decimal(tdb) - epoch) * 86400 - _decimal(lag)
            phase = Decimal(0)
            for order in range(len(coefficients), 0, -1):
                phase = (phase + coefficients[order - 1]) * dt / order
            whole = int(phase)
            integer[index] = whole
            fractional[index] = np.longdouble(str(phase - whole))
    return integer, fractional


def _integer_phase(spin: Any, toas: Any, delay: u.Quantity) -> u.Quantity:
    return spin_phase_parts(spin, toas, delay)[0] * u.dimensionless_unscaled


def _fractional_phase(spin: Any, toas: Any, delay: u.Quantity) -> u.Quantity:
    return spin_phase_parts(spin, toas, delay)[1] * u.dimensionless_unscaled


def bind_precise_spin_phase(model: Any) -> None:
    """Bind split phase evaluation to this model, including subsequent deep copies."""
    spin = model.components["Spindown"]
    if spin.PEPOCH.value is None:
        raise ValueError("Precise spin phase requires the input model's PEPOCH")
    functions = spin.phase_funcs_component
    names = [function.__name__ for function in functions]
    if names not in (["spindown_phase"], ["_integer_phase", "_fractional_phase"]):
        raise ValueError("Spindown has an unsupported phase-function composition")
    spin.phase_funcs_component = [
        MethodType(_integer_phase, spin),
        MethodType(_fractional_phase, spin),
    ]
