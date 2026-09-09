# Pilot 1 first-50 benchmark result v0.1

## Outcome

The frozen 50-case benchmark completed in 676.7 seconds and failed one of 17
hard gates. Progression is stopped. The sealed evaluation set remains untouched
and no observed-residual global search occurred.

Sixteen gates passed. All 40 ordinary and compatible joint fits converged; the
four explicit-full-covariance audits agreed well inside their frozen
tolerances; the covariance realizations whitened correctly; there were no
unexpected warnings; and projected complete runtime, memory, storage, and
artifact-integrity gates passed.

## Failed gate

The recorded maximum TOA application error was 1.462 microseconds against the
0.001-microsecond limit. Inspection of the frozen implementation and PINT 1.1.5
residual behavior showed that the metric compared an uncentered requested
wideband residual vector with a TOA residual object that subtracts a weighted
mean by default. The removable constant offset was therefore counted as
waveform error.

This does not turn the failed row into a pass. The trigger explicitly projected
the offset and the timing fits fitted it, so their covariance and convergence
results remain interpretable, but the application metric did not measure what
the protocol intended.

## Corrective disposition

The replacement measurement will record the actual high-precision TOA
adjustment error directly, matching the established Pilot 0 injection method.
It will also retain an uncentered residual-target difference as a separate
diagnostic rather than conflating the two quantities.

The same 50 case IDs, seeds, order, and scientific thresholds will be replayed
only after a new corrective execution freeze is merged. The sealed evaluation
set remains unauthorized. The original failed summary and all 50 case
artifacts remain immutable under `RECHERCHE_DATA_ROOT`.
