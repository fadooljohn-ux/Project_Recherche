# Pilot 2 Structured-Tail Implementation v0.2.1

## Scope

This additive implementation prepares the three frozen 1,000-case structured-tail
variants. It does not modify the completed Gaussian implementation, its 7,000 case
artifacts, the locked threshold, or the sealed Gaussian result.

The stage remains execution-locked until a separate authorization and execution
freeze bind the structured implementation hash, inventory hash, Gaussian closeout,
and external threshold-lock hash.

## Execution controls

- Exactly 3,000 frozen case IDs and seeds; no reroll.
- The locked Gaussian threshold is read and hash-verified before and after execution.
- A threshold change, prerequisite mismatch, artifact mismatch, or tripwire failure
  produces a hard stop.
- Resume uses the existing hash-bound v0.2.1 artifact ledger.
- Checkpoints are recorded every 25 cases.
- A health-only heartbeat is written every 30 seconds.
- Observed residuals, observed periodic scans, injections, promotion, threshold
  retuning, and discovery claims remain prohibited.

## Low-usage supervision policy

The local runner owns heartbeat and checkpoint writes. A fresh heartbeat suppresses
Codex polling. Attention is requested only for a terminal state, an interrupted
runner, or a heartbeat older than 90 seconds. For a healthy long run, the optional
review interval is 15 minutes. Health output contains counts and process state but no
scientific outcomes.

## Readiness boundary

Implementation verification and the zero-case dry run may inspect hashes, the
existing ledger, and health metadata. They may not draw a structured null, fit a
model, execute a periodic scan, or create a structured case artifact.
