# Pilot 1 injection calibration freeze v0.1

This gate authorizes the complete 284-case injection matrix and the frozen 29
explicit-full-covariance audits. It re-executes every injection case with the
locked detector so that application, ordinary-refit absorption, trigger,
compatible joint grading, amplitude/phase recovery, and annual astrometric
correlation are recorded consistently.

Frequency recovery means the global peak lies within one independent Fourier
bin, `1 / observation span`, of the injected frequency. Annual absorption is
one minus the exact-frequency covariance-GLS amplitude remaining after the
ordinary timing refit, divided by the injected amplitude and clipped to 0–1.
The annual mask uses the maximum across phases at each frozen period.

Detection fractions are evaluated only at sampled amplitudes. A 50% or 90%
crossing is interpolated only when the sampled fractions bracket it. The
100-day 90%-recovery timing amplitude is converted to projected mass using a
1.4-solar-mass pulsar and compared with the frozen 0.56-lunar-mass reference.

Any failed execution or promotion row stops progression. No observed-residual
search, candidate claim, or discovery claim is authorized.
