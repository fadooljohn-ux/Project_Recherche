# Pilot 2 Calibration Revision Implementation v0.2.1

## Scope

This package implements the revised Gaussian calibration and sealed-evaluation
stages. It preserves the v0.2 hard stop and uses a fresh external data-root generation,
new ledger, new case identities, and new seeds. Structured-tail and injection execution
are not part of this package.

## Controls

- Aggregate implementation hash binding the revision runner, executor, graders, and
  shared atomic-ledger/heartbeat implementation.
- Fresh `Pulsar-Timing-Pilot-v0.2.1` data root with verified controlled and cache
  manifests copied from the completed preflight generation.
- Offline setup with exact B1937+21 covariance, design-matrix, rank, and TOA checks.
- Atomic case artifacts, SHA-256 ledger, checkpoints every 25 cases, 30-second health
  heartbeat, interruption recovery, and a health-only dashboard.
- Rank-4,962 threshold grading over exactly 5,000 calibration cases.
- Immutable threshold lock before any of the 2,000 sealed cases.
- A sealed primary gate based only on Wilson upper 95% no greater than 2.5%; the raw
  false-positive fraction is reported but is not a second hard gate.
- Hard stop on any failed integrity, calibration, or sealed gate.
- No observed-residual vector and no observed periodic search.

## Execution boundary

Implementation validation is zero-case. Execution requires a separate freeze binding
the implementation, inventory, authorization, controlled-data manifest, environment,
and design freeze. Conditional user authorization was supplied in advance but becomes
effective only after every implementation and zero-case verification passes.
