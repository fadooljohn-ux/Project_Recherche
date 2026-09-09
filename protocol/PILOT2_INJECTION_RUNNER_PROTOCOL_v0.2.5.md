# Pilot 2 B1937+21 injection runner protocol v0.2.5

## Authority and scope

This protocol defines a zero-science remediation of the preserved v0.2.4 HOLD.
It addresses SOL-V024-001 through SOL-V024-003 without modifying v0.2.4 or
authorizing injection execution, random draws, timing-model fits, periodic
scans, observed-residual access, promotion, or discovery claims.

The exact never-executed v0.2.3 inventory remains applicable. v0.2.5 reuses its
344 cases and SHA-256
`811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`.
No v0.2.3, v0.2.4, or v0.2.5 science case has consumed a member of this
inventory. The previously consumed v0.2.2 namespace remains retired.

## Power-loss-durable attempt boundary

The v0.2.5 ledger uses a version-local durable JSON commit:

1. write the complete JSON payload to a temporary file;
2. flush the language-level buffer;
3. call `fsync` on the temporary file;
4. on macOS, call `F_FULLFSYNC` on that file;
5. atomically replace the destination;
6. call `fsync` on the containing directory; and
7. return only after all synchronization calls succeed.

The active-attempt record is committed through this boundary before the science
executor can be invoked. Case artifacts and terminal results use the same
durable commit. If any synchronization step is unsupported or fails, execution
fails closed before the executor and writes a terminal hard stop when the stage
is active.

An interrupted attempted seed still has only two dispositions: adopt a complete
verified artifact without recomputation, or preserve the seed as consumed and
terminally stop. Annual artifacts commit individually before group-level
eligibility is calculated.

## Complete recovered-artifact contract

Every new, resumed, or interrupted case artifact must match an exact record
schema. Validation requires:

- schema version and v0.2.5 run identity;
- the exact frozen case and execution binding;
- exact family-specific top-level keys;
- finite numeric fields and actual booleans;
- locked-threshold equality;
- expected candidate-eligibility behavior;
- exact input-binding and frequency-grid structure;
- observed-data boundary flags fixed false; and
- solver-audit requirement, comparison, and full-covariance nested schema
  consistent with the frozen audit inventory.

Nonannual stored records require `candidate_eligible: true`. Annual stored
records must omit that group-derived value; it is deterministically recomputed
only after every artifact in the period group verifies. A partial JSON object
cannot be adopted or ledgered.

The scientific computation remains the corrected v0.2.3 executor. A thin
v0.2.5 wrapper changes only the record identity before complete validation and
durable commit.

## Repository-confined exact authorization hashes

Implementation, readiness, and future execution freezes each have a distinct
compiled allowlist of required repository-relative files. A hash map must match
the applicable path set exactly before any target is hashed. Missing, extra,
absolute, parent-traversal, symlinked, absent, or repository-escaping paths fail
closed.

The expected execution-freeze path itself must be a nonsymlinked file resolving
inside the repository. Repository-local implementation and readiness checks
complete before predecessor or external-data access. A future execution freeze
must also bind the final dedicated Sol audit records; otherwise its exact path
set cannot pass.

## Health and scientific boundaries

The 30-second health record remains outcome-free. It may reveal whether an
attempt is active, but never the case ID, seed, fit result, trigger, candidate,
or scientific grade. The stale threshold remains 90 seconds and the passive
review interval remains 30 minutes.

Observed residuals, observed periodic search, threshold retuning, promotion,
and discovery claims remain unauthorized. No execution freeze exists.

## Validation and next gate

Zero-science tests use temporary initialized roots, synthetic complete and
incomplete artifacts, synchronization spies, forced synchronization failure,
and path-containment probes. The forced interrupt replaces the executor before
any random draw or fit. Exact commands and intentional historical deselections
must be preserved in a machine-readable manifest.

After one local validation cycle and readiness freeze, one fresh read-only Sol
audit may assess the final milestone. A HOLD preserves the package and stops. A
PASS establishes readiness only; science remains locked pending a later,
separate explicit user authorization and a fully verified v0.2.5 execution
freeze.
