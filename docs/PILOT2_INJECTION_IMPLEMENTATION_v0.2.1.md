# Pilot 2 Injection Implementation v0.2.1

## Scope

This additive implementation prepares the frozen 284-case injection, recovery,
annual-identifiability, search-boundary, and solver-audit stage for B1937+21. It does
not modify or rerun the completed 10,000 Gaussian and structured-tail cases.

## Frozen workload

- 240 main recovery cases across five period-specific amplitude ladders.
- 28 annual-identifiability cases across seven periods and four phases.
- 16 boundary cases at 30 and 2,000 days.
- One ordinary timing-model fit and one joint circular-signal fit per case.
- 29 deterministic explicit full-covariance solver audits.

The exact case IDs, seeds, ordering, audit selection, threshold, detector, recovery
limits, annual-eligibility limits, and numerical tolerances come from the frozen
v0.2.1 design. There is no reroll, threshold retuning, interpolation outside a
bracket, or substitution of a prior-generation case.

## Integrity and resume controls

The runner verifies the cumulative artifact ledger, Gaussian and structured-tail
results, threshold lock, inventory, implementation, and execution authorization
before setup. Each completed case is written atomically and hash-bound to the
cumulative v0.2.1 ledger. Resume accepts only matching case artifacts and the same
inventory, implementation, threshold, and execution freeze.

Annual eligibility is computed periodwise from all four frozen phase cases before
new annual artifacts are committed. Solver audits require convergence, preservation
of released red noise, absence of WaveX, and agreement within all three frozen
numerical tolerances.

## Supervision and resource controls

The stage uses 25-case durable checkpoints, a local 30-second heartbeat, a 90-second
stale tripwire, and a 15-minute passive review interval. A fresh heartbeat suppresses
Codex polling. Health output reports only process state and counts. The runner enforces
the six-hour wall-time, 16 GiB peak-memory, and 1.5 GiB complete-data-root caps.

## Authority boundary

Implementation verification and the zero-case dry run may inspect hashes, ledger
metadata, and health state. They may not generate an injection, fit a synthetic case,
execute a periodic scan, open the observed residual vector, grade promotion, or
prepare a discovery claim. Execution requires a separate explicit user authorization
and execution freeze.
