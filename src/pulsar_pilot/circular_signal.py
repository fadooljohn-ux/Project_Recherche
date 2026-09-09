from __future__ import annotations

from typing import Any

import astropy.units as u
import numpy as np
from pint.models.parameter import MJDParameter, floatParameter
from pint.models.timing_model import DelayComponent


class ProjectCircularSignal(DelayComponent):
    """Fixed-frequency deterministic circular timing-delay signal.

    This component intentionally has a distinct physical-signal category. It
    does not replace or duplicate PINT's PLRedNoise covariance component.
    """

    register = False
    category = "project_circular_signal"

    def __init__(self) -> None:
        super().__init__()
        self.add_param(
            MJDParameter(
                name="CSEPOCH",
                description="Reference epoch for the deterministic circular signal",
                time_scale="tdb",
                tcb2tdb_scale_factor=u.Quantity(1),
            )
        )
        self.add_param(
            floatParameter(
                name="CSFREQ",
                description="Fixed deterministic circular-signal frequency",
                units="1/d",
                value=0.01,
                frozen=True,
                tcb2tdb_scale_factor=u.Quantity(1),
            )
        )
        self.add_param(
            floatParameter(
                name="CSSIN",
                description="Deterministic circular-signal sine amplitude",
                units="s",
                value=0.0,
                frozen=False,
                tcb2tdb_scale_factor=u.Quantity(1),
            )
        )
        self.add_param(
            floatParameter(
                name="CSCOS",
                description="Deterministic circular-signal cosine amplitude",
                units="s",
                value=0.0,
                frozen=False,
                tcb2tdb_scale_factor=u.Quantity(1),
            )
        )
        self.set_special_params(["CSFREQ", "CSSIN", "CSCOS"])
        self.delay_funcs_component += [self.circular_signal_delay]

    def setup(self) -> None:
        super().setup()
        self.register_deriv_funcs(self.d_delay_d_cssin, "CSSIN")
        self.register_deriv_funcs(self.d_delay_d_cscos, "CSCOS")

    def validate(self) -> None:
        super().validate()
        if self.CSEPOCH.value is None:
            raise ValueError("CSEPOCH is required")
        if self.CSFREQ.value is None or self.CSFREQ.value <= 0:
            raise ValueError("CSFREQ must be positive")

    def _base_phase(self, toas: Any, delays: u.Quantity | None = None) -> u.Quantity:
        base = toas.table["tdbld"].data * u.d - self.CSEPOCH.value * u.d
        if delays is not None:
            base -= delays.to(u.d)
        return 2.0 * np.pi * self.CSFREQ.quantity * base

    def circular_signal_delay(self, toas: Any, delays: u.Quantity) -> u.Quantity:
        phase = self._base_phase(toas, delays)
        return self.CSSIN.quantity * np.sin(phase.value) + self.CSCOS.quantity * np.cos(
            phase.value
        )

    def _derivative_phase(self, toas: Any, delays: u.Quantity | None) -> u.Quantity:
        # PINT's d_phase_d_param calls delay derivatives without passing the
        # accumulated delay. Reconstruct the delay entering this component,
        # excluding our own signal, so the Jacobian matches the forward model.
        if self._parent is not None:
            delays = self._parent.delay(
                toas, cutoff_component=self.__class__.__name__, include_last=False
            )
        return self._base_phase(toas, delays)

    def d_delay_d_cssin(
        self,
        toas: Any,
        param: str,
        delays: u.Quantity,
        acc_delay: u.Quantity | None = None,
    ) -> u.Quantity:
        del acc_delay
        phase = self._derivative_phase(toas, delays)
        return np.sin(phase.value) * u.s / getattr(self, param).units

    def d_delay_d_cscos(
        self,
        toas: Any,
        param: str,
        delays: u.Quantity,
        acc_delay: u.Quantity | None = None,
    ) -> u.Quantity:
        del acc_delay
        phase = self._derivative_phase(toas, delays)
        return np.cos(phase.value) * u.s / getattr(self, param).units
