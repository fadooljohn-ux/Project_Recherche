# B1937+21 injection remediation v0.2.5 — execution-readiness report

## Disposition

**Primary readiness: PASS. Independent Sol audit: PENDING. Science execution:
LOCKED.**

v0.2.5 is an isolated zero-science remediation of the preserved v0.2.4 HOLD.
It does not modify v0.2.4 and does not create an execution freeze.

## Scorecard

| Gate | Outcome | Evidence |
|---|---|---|
| File synchronization before executor | PASS | Ledger temp file is flushed, `fsync`ed, and macOS `F_FULLFSYNC`ed before replace |
| Directory synchronization | PASS | Parent directory is `fsync`ed after atomic replace and before return |
| Failed file synchronization | PASS | Forced failure stops before executor and terminalizes the active stage |
| Failed directory synchronization | PASS | Forced failure stops before executor and terminalizes the active stage |
| Partial recovery artifact | PASS | Rejected and consumed with terminal hard stop |
| Complete recovery artifact | PASS | Adopted without recomputation |
| Ledger reconciliation | PASS | Path, byte count, and SHA-256 must match |
| Annual interruption | PASS | Annual artifact commits and adopts without candidate eligibility; group value is recomputed later |
| Nonannual schema | PASS | Stored record requires `candidate_eligible: true` |
| Solver-audit schema | PASS | Exact comparison and full-covariance nested fields required |
| Hash path exact set | PASS | Missing and extra paths fail before hashing |
| Parent and absolute paths | PASS | Rejected before target access |
| Symlink escape | PASS | Rejected even when the target exists |
| Readiness and science boundaries | PASS | Explicit readiness, observed-data, retuning, promotion, and discovery controls retained |
| Applicable repository suite | PASS | 236 passed, 0 failed, 3 documented historical deselections |
| v0.2.5 boundary tests | PASS | 24/24 |
| Temporary-root dry run | PASS | Zero cases, draws, fits, scans, predecessor loads, or observed residuals |
| Current execution lock | PASS | No v0.2.5 execution freeze exists |

## Validation boundary

All recovery records were synthetic JSON created in temporary initialized data
roots. Interruption tests replaced the executor before any random generation or
fit. Synchronization tests observed actual local filesystem calls or forced a
failure before the executor. Path tests used temporary files and never accessed
an external science root.

The exact repository command, all 24 v0.2.5 test IDs, and the three historical
v0.2.2 deselections are preserved in
`results/pilot2/injection_validation_manifest_v0.2.5.json`.

## Residual limitations

No software test can force a real electrical power loss while this MacBook is
running. The implementation therefore validates the required operating-system
durability sequence and fails closed if any synchronization call fails. A
future filesystem that rejects macOS `F_FULLFSYNC` or directory `fsync` will
stop before science rather than silently weaken the guarantee.

## Conservative final audit

One fresh Sol subagent will inspect this frozen package under a read-only,
zero-science charter. It may run only the targeted v0.2.5 tests and repository-
local freeze verifiers. It may not access `/Volumes`, inspect scientific
outcomes, or run the full repository suite again.

A HOLD preserves the package and stops. A PASS establishes readiness only. A
later separate explicit instruction would still be required before a v0.2.5
execution freeze could be created and verified.
