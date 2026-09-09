# Pilot 1 first-50 execution freeze

- **Freeze target:** `pilot1-first-50-v0.1`.
- **Authorization:** exactly the 50 ordered cases in
  `results/pilot1/benchmark50_plan.json`.
- **Sealed evaluation:** not authorized.
- **Observed-residual search:** not authorized.
- **Promotion:** not evaluated by this benchmark.

## Purpose

This is the first Pilot 1 phase allowed to generate synthetic realizations. It
is a resource and numerical-validity benchmark, not threshold calibration. It
tests the complete MacBook workflow before committing to the full 1,784-case
calibration workload.

The 50 cases comprise ten calibration nulls, 28 main-matrix injections, four
annual-identifiability injections at 365.25 days, four search-boundary
injections spanning both 30 and 2,000 days at both boundary amplitudes, and
four independently selected full-covariance audit cases. No sealed-evaluation
seed or case appears in the order.

## Execution controls

The runner refuses to start unless the execution-freeze record, benchmark
order, runner, Pilot 1 design, target configuration, implementation record,
and environment lock all match their frozen hashes. Every case has a fixed ID,
seed, and sequence. Results remain below `RECHERCHE_DATA_ROOT`; the resumable
ledger binds every completed case to the frozen inventory and implementation
and verifies every external artifact hash.

Synthetic wideband residuals are generated from the released covariance. For
fit cases, the observed release residual is removed before adding the frozen
noise and circular signal, so the synthetic realization replaces rather than
stacks on the observed residual. The trigger operates on the same requested
wideband residual vector.

## Hard benchmark scorecard

The benchmark stops progression unless every row passes:

1. Exactly 50 unique ordered cases complete and the ledger verifies.
2. The sealed evaluation and global observed-residual search remain untouched.
3. Pooled whitened lag correlations and variance satisfy the frozen null gates.
4. Every injected TOA waveform is applied within 0.001 microseconds.
5. Every ordinary and compatible joint fit converges.
6. Four explicit-full-covariance audits meet the frozen amplitude, phase, and
   chi-squared equivalence tolerances.
7. No unexpected material warning occurs.
8. Projected complete Pilot 1 runtime is at most four hours.
9. Peak memory is at most 16 GiB and the complete data root is at most 5 GiB.

## Stop rule and next gate

Any failed row stops execution after the benchmark and requires a disposition
before another synthetic case is authorized. A full pass permits preparation
of a separate calibration-null authorization for the remaining 990
calibration nulls. It does not unlock the 500 sealed evaluation nulls, the
complete injection matrix, or initial-v0.1 promotion.
