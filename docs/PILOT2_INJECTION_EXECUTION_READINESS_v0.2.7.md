# B1937+21 injection remediation v0.2.7 — execution-readiness report

## Disposition

**Primary readiness: PASS. Independent Sol audit: PENDING. Science execution:
LOCKED.**

v0.2.7 is an isolated zero-science remediation of the preserved v0.2.6 HOLD.
It does not modify v0.2.6 and does not create an execution freeze.

## Scorecard

| Gate | Outcome | Evidence |
|---|---|---|
| Duplicate-free trusted parser | PASS | The single `json.loads` entrypoint uses an object-pairs hook for every nested object |
| Implementation/readiness freezes | PASS | Duplicate members fail before freeze semantics or hashes are trusted |
| Future execution authorization | PASS | Contradictory duplicate authorization fails before predecessors load |
| Predecessor controls | PASS | Ledger, crash audit, and threshold lock route through strict parsing |
| Data-root identity | PASS | Duplicate marker fails before the root is trusted |
| Version ledger | PASS | Duplicate state member fails before stage state is used |
| Interrupted artifact | PASS | Nested duplicate input binding prevents adoption and preserves a terminal hard stop |
| Resumed completed artifact | PASS | Same strict parser precedes complete typed record validation |
| Exact typed live context | PASS | v0.2.6 recursive type-and-value comparison and context hashes retained |
| Nested directory durability | PASS | Immediate-parent synchronization and family-directory precreation retained |
| Durable file commit | PASS | File `fsync`, macOS `F_FULLFSYNC`, replace, and directory `fsync` retained |
| Applicable repository suite | PASS | 309 passed, 0 failed, 3 documented historical deselections |
| v0.2.7 boundary tests | PASS | 40/40 |
| Temporary-root dry run | PASS | Zero cases, draws, fits, scans, predecessor loads, or external-root access |
| Current execution lock | PASS | No v0.2.7 execution freeze exists |

## Validation boundary

The duplicate-member tests deliberately place an apparently valid value last,
which ordinary parsing would retain. Authorization, readiness, nested artifact
binding, ledger state, and the data-root marker all reject the raw document
instead. A source guard verifies that no ordinary `json.loads` call remains
outside the object-pairs-aware entrypoint in the v0.2.7 runner.

All execution-path tests replaced the science executor before any random draw
or fit. The dry run used an automatically removed temporary root. No external
science root, predecessor record, sealed result, or observed residual was read.

## North Star position

This package satisfies the remediation and zero-science validation stages of
`docs/PILOT2_SCIENCE_STAGE_NORTH_STAR.md`. The next stage is one conservative
read-only Sol audit of the exact frozen commit. An audit PASS would permit the
separate execution-freeze preparation stage; it would not itself execute
science.

## Residual limitation

This validation establishes fail-closed parsing and software durability
sequences. It does not simulate physical power loss and does not establish
scientific performance, which remains the purpose of the future frozen 344-case
run.
