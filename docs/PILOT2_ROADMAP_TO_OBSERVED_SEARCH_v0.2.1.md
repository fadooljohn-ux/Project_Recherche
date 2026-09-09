# Pilot 2 Roadmap to Observed Search v0.2.1

## Current boundary

Pilot 2 has completed the frozen Gaussian calibration, independent sealed-Gaussian
evaluation, and three structured-tail stress families for B1937+21. The cumulative
v0.2.1 ledger contains 10,000 verified synthetic cases. The real observing cadence,
timing model, design matrix, and covariance have been used, but the observed residual
vector remains sealed and no observed periodic search has been executed.

## Gate 1 — Injection implementation and zero-case readiness

Prepare and freeze an additive runner for the remaining 284 synthetic injection
cases:

- 240 main recovery injections across five period-specific amplitude ladders;
- 28 annual-identifiability cases at seven periods;
- 16 search-boundary cases at 30 and 2,000 days;
- 568 primary ordinary/joint recovery fits; and
- 29 deterministic full-covariance solver audits.

The implementation package must preserve the completed 10,000-case ledger, locked
threshold, and observed-data boundary. Validation executes zero injections and ends
with a readiness scorecard. Injection execution requires separate user authorization.

## Gate 2 — Injection, annual-map, and solver-audit execution

Execute only the frozen 284-case inventory. Grade the preregistered gates:

- strong-control recovery rate at least 90 percent;
- injected-frequency recovery rate at least 95 percent within one independent
  Fourier bin;
- median amplitude bias no greater than 10 percent;
- 90th-percentile phase error no greater than 0.10 radians;
- monotonic detection behavior at at least three main periods;
- bracketed 50 and 90 percent recovery at at least three main periods;
- zero annual-eligibility violations; and
- all 29 solver audits within the frozen amplitude, phase, and chi-square tolerances.

Any integrity, convergence, numerical, or hard-gate failure stops the program without
reroll, threshold retuning, promotion, or observed-data access. The projected runtime
is approximately two to three hours and remains subject to the six-hour MacBook cap.

## Gate 3 — Promotion grade

Combine the Gaussian, sealed-null, structured-tail, injection, annual-map, and solver
results. Promotion requires every frozen hard gate to pass. A promotion pass authorizes
only preparation of an observed-search design; it never authorizes observed-residual
access or an observed periodic search.

## Gate 4 — Observed-search design and execution freeze

Freeze the exact observed-data and analysis boundary before access:

- observed residual-vector identity and cryptographic hash;
- target, controlled inputs, detector implementation, and environment;
- immutable threshold and empirical annual-period eligibility mask;
- candidate eligibility and strongest-unmasked-cell semantics;
- one-shot, no-rerun, no-retuning, and failure-stop rules;
- outcome sealing and closeout requirements; and
- explicit prohibitions on scope expansion and discovery claims.

This is the appropriate milestone for an optional passive independent audit. An audit
may provide findings and recommendations but cannot authorize execution.

## Gate 5 — Explicit observed-search authorization

Only a new explicit user authorization bound to the frozen observed-search package
may open the observed residual vector and execute the one-shot search. This is the
point at which the detector begins testing against the actual observed scientific
residual data.

## Execution and supervision policy

Each long-running stage uses a local 30-second health heartbeat, a 90-second stale
tripwire, 25-case durable checkpoints, a 15-minute passive review interval, and no
Codex polling while the heartbeat is fresh. Health displays process state and counts
without revealing scientific outcomes before stage completion.
