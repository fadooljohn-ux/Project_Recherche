# Pilot 1 tail-robustness protocol v0.1

## Decision

Determine whether the excess-kurtosis advisory carried into initial v0.1 can
be bounded without inspecting any observed periodic-search result. Passing
this gate permits preparation of a separate one-shot search freeze; it does
not authorize that search.

## Boundary

The only authorized use of the observed J1744-1134 residual vector is
non-periodic time-domain tail localization. The execution must not construct
an observed-data frequency grid, compute a periodogram, evaluate a sinusoidal
candidate statistic, inspect a peak, or change the annual-identifiability
mask. Synthetic contaminated nulls and injections may use the already frozen
30–2,000-day detector grid.

## Load-bearing concern

The original non-periodic diagnostic found absolute excess kurtosis 1.26214,
outside its frozen central 99% interval, while energy, variance, skewness,
median spread, maximum absolute residual, and short-lag correlation passed.
The gate therefore tests whether a sparse heavy-tailed innovation process can
materially change false-positive calibration or recovery sensitivity.

## Frozen contamination model

Each independent standard-normal innovation has a one-percent probability of
being multiplied by 2.8237419549367053. The complete innovation vector is
divided by the analytic mixture standard deviation before multiplication by
the released covariance factor. The resulting zero-mean unit-variance scale
mixture has theoretical excess kurtosis 1.262140834554768, matching the
observed advisory magnitude without using any periodic information.

This is a stress model, not a claim that the observed residuals were generated
by that exact process. It deliberately preserves the released covariance while
introducing tails of the measured magnitude.

## Observed non-periodic localization

The frozen diagnostic must reproduce the prior projected kurtosis and report:

1. projected and raw-standardized results separately for the timing and DM
   blocks;
2. the twelve largest absolute projected coordinates with their corresponding
   TOA row metadata;
3. leave-one-coordinate influence on kurtosis;
4. leave-one-group influence for UTC observing day, backend, frontend, and
   observing system; and
5. top-one and top-five squared-energy concentration.

Because whitening and timing projection mix coordinates, metadata attached to
a projected coordinate is an influence locator, not proof that a named TOA is
the physical cause.

## Contaminated null calibration and evaluation

- Generate exactly 1,000 calibration nulls and 500 disjoint evaluation nulls.
- Use the existing synthetic detector grid only.
- Estimate the contamination threshold with the conservative nearest-rank
  99th percentile.
- Lock the robust threshold to the larger of the initial-v0.1 threshold and
  the contamination threshold.
- Do not retune after evaluating the 500 disjoint cases.
- Require evaluation false-positive rate at most 1% and Wilson 95% upper bound
  at most 2.5%.
- Also report, without making it a gate, how the initial-v0.1 threshold would
  have performed on the contaminated evaluation set.

## Recovery stress

Run exactly 160 contaminated-noise injections: five periods, four amplitudes,
four phases, and two noise realizations. Recovery requires both exceeding the
robust threshold and placing the global synthetic peak within one independent
Fourier bin of the injection. Require monotonic response and bracketed 50% and
90% crossings at three or more periods, plus at least 95% frequency recovery
among robust-threshold triggers.

Sixteen deterministically selected cases receive complete ordinary and joint
timing refits. Four of those receive the independent explicit-covariance audit.
All selected fits must converge and every audit comparison must remain within
the frozen amplitude, phase, and chi-squared tolerances.

## Resource and integrity controls

Execution is resumable and writes case artifacts and ledgers only beneath
`RECHERCHE_DATA_ROOT`. The incremental wall-time cap is two hours, peak memory
is 16 GiB, and the complete external data-root cap remains 5 GiB. Code,
configuration, protocol, seeds, inventories, environment lock, parent release
record, and the prior advisory result must be hashed before execution.

## Decision rule

All hard benchmarks must pass. A failure pauses the observed search and
requires a detector or threshold rebaseline. A pass retains the tail finding
as a documented limitation and authorizes only the preparation and review of a
separate one-shot observed-residual search freeze.
