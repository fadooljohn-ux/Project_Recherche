# B1937+21 injection remediation v0.2.6 — execution-readiness report

## Disposition

**Primary readiness: PASS. Independent Sol audit: PENDING. Science execution:
LOCKED.**

v0.2.6 is an isolated zero-science remediation of the preserved v0.2.5 HOLD.
It does not modify v0.2.5 and does not create an execution freeze.

## Scorecard

| Gate | Outcome | Evidence |
|---|---|---|
| Exact trusted-context values | PASS | Every record must equal the context loaded for the invocation |
| Concrete JSON types | PASS | Boolean/integer and integer/float substitutions are rejected |
| Epoch, span, grid, and count binding | PASS | Dynamic context values are compared exactly, not merely schema-checked |
| Attempt context commitment | PASS | Canonical input-binding SHA-256 is stored before the executor |
| Execution context commitment | PASS | Input-binding SHA-256 is incorporated in the execution binding |
| Nested directory durability | PASS | Each new directory entry is followed by immediate-parent `fsync` |
| Case-directory precreation | PASS | Root and four family directories are durable before the executor |
| Failed directory synchronization | PASS | Forced failure stops and terminalizes before the executor |
| Durable artifact file boundary | PASS | File `fsync`, macOS `F_FULLFSYNC`, replace, and final-directory `fsync` retained |
| Interrupted recovery | PASS | Attempt hash and complete typed artifact must verify; no recomputation |
| Applicable repository suite | PASS | 269 passed, 0 failed, 3 documented historical deselections |
| v0.2.6 boundary tests | PASS | 33/33 |
| Temporary-root dry run | PASS | Zero cases, draws, fits, scans, predecessor loads, or observed residuals |
| Current execution lock | PASS | No v0.2.6 execution freeze exists |

## Validation boundary

All records were synthetic JSON in temporary initialized roots. Exact-binding
tests mutated booleans, integers, floating-point values, shapes, epoch, search
span, and frequency count. Directory tests observed actual synchronization
order or forced failure. Every execution-path test replaced the science
executor before a random draw or fit. No external science root was accessed.

The exact repository command and three historical v0.2.2 deselections are
preserved in
`results/pilot2/injection_validation_manifest_v0.2.6.json`.

## Residual limitations

Software tests cannot force a real electrical power loss. They validate the
operating-system durability sequence and fail closed if any required call
fails. Filesystems that reject macOS `F_FULLFSYNC` or directory `fsync` will
stop before science instead of silently weakening the contract.

## Conservative final audit

One fresh Sol subagent will inspect this frozen package under a read-only,
zero-science charter. It may run only targeted v0.2.6 tests and repository-local
freeze verifiers. It may not access `/Volumes`, inspect scientific outcomes,
modify the repository, or rerun the full repository suite.

A HOLD preserves the package and stops. A PASS establishes readiness only. A
later separate explicit instruction would still be required before a v0.2.6
execution freeze could be created and verified.
