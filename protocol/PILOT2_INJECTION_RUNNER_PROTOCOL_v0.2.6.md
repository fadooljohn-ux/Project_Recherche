# Pilot 2 B1937+21 injection runner protocol v0.2.6

## Authority and scope

This protocol defines an isolated zero-science remediation of the preserved
v0.2.5 HOLD. It closes SOL-V025-001 and SOL-V025-002 without modifying v0.2.5
or authorizing injection execution, random draws, timing-model fits, periodic
scans, observed-residual access, promotion, or discovery claims.

The exact never-executed v0.2.3 inventory remains applicable. v0.2.6 reuses
its 344 cases and SHA-256
`811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`.
No v0.2.3 through v0.2.6 science case has consumed a member of this inventory.
The previously consumed v0.2.2 namespace remains retired.

## Exact trusted input binding

The runner constructs the input binding from the context actually prepared for
the invocation before it evaluates a new or interrupted case. The binding must
match the exact schema and concrete JSON types: booleans cannot stand in for
integers, integers cannot stand in for floating-point context values, and every
shape, count, search-grid value, reference epoch, and boundary flag is checked.

Every new, resumed, or interrupted record must be recursively identical in
both value and type to that trusted context binding. A canonical JSON SHA-256
of the binding is stored in the active-attempt journal and incorporated into
the execution binding together with the implementation, execution freeze,
threshold lock, and inventory hashes. Recovery rejects an attempt or artifact
whose trusted-context hash or complete typed binding differs.

## Durable first-use directory creation

Every newly created directory entry is committed by calling `fsync` on its
immediate parent before the next child is created. Before any case executor can
run, the runner durably precreates the version-local case root and the `main`,
`phase_reference`, `annual`, and `boundary` family directories.

The v0.2.5 durable file protocol remains in force: flush, file `fsync`, macOS
`F_FULLFSYNC`, atomic replace, then containing-directory `fsync`. A failure in
directory creation, parent synchronization, attempt journaling, or artifact
commit fails closed. Once a seed is durably journaled, it is either reconciled
to a complete verified artifact without recomputation or preserved as consumed
with a terminal hard stop.

## Recovered artifacts and authorization hashes

The complete v0.2.5 schema, solver payload, family rules, observed-data flags,
and repository-confined exact freeze-hash allowlists remain required. v0.2.6
also binds the preserved v0.2.5 Sol audit record and disposition as predecessor
evidence. Repository authorization is checked before predecessor or external
data access.

## Health and scientific boundaries

The 30-second health record remains outcome-free. It may expose only operational
state and never a case identity, seed, fit result, trigger, candidate, or grade.
Observed residuals, observed periodic search, threshold retuning, promotion,
and discovery claims remain unauthorized. No v0.2.6 execution freeze exists.

## Validation and next gate

Zero-science tests use temporary initialized roots, synthetic JSON records,
exact-type mutations, directory and synchronization spies, forced failures,
and executor replacement before any random draw or fit. One applicable
repository-suite run is allowed and its three historical v0.2.2 deselections
must be recorded exactly.

After implementation and readiness freezes, one fresh read-only Sol subagent
may audit the milestone. A HOLD preserves the package and stops. A PASS
establishes readiness only; science remains locked pending a later, separate
explicit instruction and a fully verified v0.2.6 execution freeze.
