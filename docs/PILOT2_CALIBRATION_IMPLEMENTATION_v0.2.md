# Pilot 2 Calibration Runner Implementation v0.2

## Purpose

This package implements the frozen B1937+21 calibration orchestration and grading
controls. It does not authorize or execute calibration cases, access observed
residuals, or run an observed periodic search.

## Implemented controls

- Frozen six-stage sequence with fail-closed predecessor checks.
- Separate execution-freeze gate checked before a case executor can be called.
- Resumable ledger bound to both the 4,784-case inventory and implementation hash.
- Atomic artifact records with byte length and SHA-256 verification.
- Durable checkpoints every 25 completed cases.
- A 30-second heartbeat, process state, active-stage elapsed time, last checkpoint,
  hard-stop state, and manual-refresh command.
- A desktop-visible HTML health page that reveals operational state but no interim
  trigger values, thresholds, candidates, or other scientific outcomes.
- Threshold proposal followed by a distinct immutable threshold-lock artifact.
- Sealed Gaussian evaluation blocked until the threshold lock verifies.
- Fail-closed graders for Gaussian calibration, sealed evaluation, three structured
  tails, injection recovery, the empirical annual mask, deterministic solver audits,
  and final promotion.
- Promotion explicitly leaves observed-search authorization false.

## Recovery semantics

On restart, the runner verifies the inventory hash, implementation hash, and every
recorded artifact. Already-recorded cases are skipped. A missing, changed, or corrupt
artifact blocks continuation. An interrupted stage is shown as
`paused_or_interrupted` until an authorized runner resumes it.

## Implementation boundary

The orchestration accepts a science-case executor only after the separate execution
freeze passes. This implementation phase supplies and tests the runner and graders;
the first invocation of a science-case executor remains a separately authorized act.
The execution freeze must bind the final executor adapter, environment, inventory,
and implementation hashes before calibration begins.

## Validation boundary

Validation uses temporary synthetic JSON artifacts and deterministic grader fixtures.
It performs zero covariance draws, zero timing-model fits, zero periodic scans, and
zero calibration science cases. Temporary test artifacts are not retained as program
results.
