# B1937+21 injection remediation v0.2.4 — execution-readiness report

## Disposition

**Primary readiness: PASS. Independent Sol audit: PENDING. Science execution:
LOCKED.**

The v0.2.4 remediation closes all five findings from the v0.2.3 dedicated Sol
audit under zero-science validation. This report does not authorize execution.
A separate v0.2.4 execution freeze remains absent.

## Scorecard

| Gate | Outcome | Evidence |
|---|---|---|
| Durable attempt journal before seed use | PASS | Active case, seed, sequence, artifact path, and execution binding are atomically saved before the executor |
| Verified artifact recovery | PASS | Interrupted complete artifact is adopted and ledgered without recomputation |
| Consumed attempt without artifact | PASS | Terminal failure and hard stop; no reroll |
| Ledger/attempt reconciliation | PASS | Path, byte count, and SHA-256 must match before clearing the attempt |
| Annual-case commit boundary | PASS | Each annual case commits before group eligibility calculation |
| Repository authorization before external access | PASS | Malformed or incomplete execution freeze returns before predecessor loading |
| Full execution-freeze contract | PASS | Exact counts, 688 fits, boundaries, predecessor hashes, supervision, stop rule, and frozen hashes required |
| Readiness semantic | PASS | `execution_readiness` must explicitly equal `pass` |
| Post-stage terminalization | PASS | Immediate post-begin exception produces terminal result and hard stop |
| Health-only record | PASS | Attempt presence is visible; case ID, seed, fits, triggers, candidates, and grades are absent |
| Inventory integrity | PASS | Never-executed v0.2.3 inventory reused exactly; SHA-256 `811c46d4...eac7b` |
| v0.2.4 boundary tests | PASS | 13/13 |
| Applicable repository suite | PASS | 212 passed, 0 failed, 3 documented historical deselections |
| Temporary-root dry run | PASS | Zero cases, draws, fits, scans, predecessor loads, or observed residuals |
| Current science lock | PASS | No v0.2.4 execution freeze exists |

## Validation boundary

All v0.2.4 recovery tests use temporary initialized roots and synthetic JSON
artifacts. The executor is replaced before any draw or fit in the interrupt
test. The dry run uses no project data root and loads no predecessor record.
The exact repository command and all deselected test IDs are preserved in
`results/pilot2/injection_validation_manifest_v0.2.4.json`.

The three deselections are historical v0.2.2 tests whose preauthorization-only
assumptions became false after v0.2.2 received its one-time execution freeze.
They are preserved unchanged and are not v0.2.4 failures.

## Conservative audit policy

The implementation was developed and validated without repeated subagent
reviews. After the readiness package is frozen, one fresh Sol subagent will
perform a read-only milestone audit. It may inspect the repository package,
temporary test behavior, and preserved predecessor hashes, but it must not read
scientific outcomes or execute science.

If that audit returns HOLD, the package remains locked. If it returns PASS, the
result establishes readiness only; a later separate explicit user instruction
would still be required before creating and verifying a v0.2.4 execution
freeze.
