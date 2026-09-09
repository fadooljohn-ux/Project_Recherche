# Pilot 2 B1937+21 injection runner protocol v0.2.4

## Authority and scope

This protocol defines a zero-science remediation of the v0.2.3 injection
runner. It closes the dedicated Sol audit findings SOL-V023-001 through
SOL-V023-005. It does not authorize an injection case, timing-model fit,
random draw, periodic scan, observed-residual access, promotion grade, or
discovery claim.

The v0.2.3 inventory was frozen but never executed. v0.2.4 therefore reuses
that exact 344-case inventory and its SHA-256
`811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`.
Generating another inventory would add seed churn without retiring a consumed
case. The previously consumed v0.2.2 case and the entire v0.2.2 namespace remain
excluded.

## Durable one-shot attempt journal

Before any case executor can generate a random draw or perform a fit, the
runner atomically records an active attempt containing its frozen case ID,
seed, sequence, family, intended artifact path, and execution binding. That
record marks the seed as consumed.

After an interruption, exactly two recovery outcomes are allowed:

1. If a complete artifact verifies against the frozen case and execution
   binding, it is adopted and ledgered without recomputation.
2. If no verified artifact exists, the stage writes a terminal failure and
   hard stop. The case and seed remain consumed and cannot be rerun.

If the ledger entry committed before interruption, its path, byte count, and
SHA-256 must also match before the active attempt is cleared. Annual-family
artifacts are committed individually before group eligibility is derived, so
no computed annual case can remain pending behind a group-level commit.

`KeyboardInterrupt` deliberately remains outside ordinary exception handling.
An interrupt before the durable attempt record is resumable. An interrupt after
that record invokes the recovery disposition above on the next authorized
start.

## Staged authorization verification

Repository-local authorization is validated before any predecessor artifact or
data root is accessed. The implementation and readiness freezes must both pass,
and readiness must explicitly state `execution_readiness: pass`. A present
execution freeze must verify its schema, identity, explicit user authorization,
exact case and fit counts, no-reroll rule, threshold and observed-data
boundaries, predecessor hashes, supervision policy, stop rule, and every frozen
file hash.

Only after all repository-local checks pass may the runner receive and verify
the external data root and preserved predecessor records. A malformed,
incomplete, mismatched, or absent execution freeze fails closed without loading
those records or preparing the timing-model context.

## Complete terminalization boundary

All ordinary operations from stage activation through terminal grading are
inside one exception boundary. Any unexpected `Exception`, including a failure
immediately after stage activation, writes a terminal result with the exception
class, message, active case ID if any, and completed-record count. It records no
partial scientific metrics, then marks the stage failed and writes a hard stop.

## Health-only supervision

The 30-second health record exposes process state, PID, elapsed time, completed
count out of 344, checkpoint count, stage status, whether an attempt is active,
and hard-stop state. It never exposes the active case ID, seed, injection
outcomes, fit results, trigger statistics, candidate metrics, or scientific
grade. Heartbeat staleness remains 90 seconds and passive review remains every
30 minutes.

## Validation and next gate

Validation must use temporary initialized data roots and mocks that stop before
random generation, fitting, or scanning. The exact test command, selected test
IDs, and intentional historical deselections must be preserved in a
machine-readable manifest.

After the implementation and readiness packages are frozen, one fresh
read-only Sol audit may assess the milestone. A Sol PASS would establish only
execution readiness. Science remains locked until a separate explicit user
authorization is captured in a v0.2.4 execution freeze and reverified before
external-data access.
