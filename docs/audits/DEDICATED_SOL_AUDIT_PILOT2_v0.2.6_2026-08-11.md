# Dedicated Sol audit — B1937+21 v0.2.6

## Executive disposition: HOLD

The independent read-only audit verified clean commit
`8c1dd7062246c111a49e8fcbd6f9181a04dd844c`. The worktree remained clean
throughout the audit. The two v0.2.5 remediation mechanisms are substantively
present, but one new P1 trust-boundary gap prevents execution readiness.

## Finding register

### SOL-V026-001 — P1: duplicate JSON member names precede trust decisions

The runner uses ordinary `json.loads()` for implementation and readiness
freezes, a future execution freeze, predecessor controls, interrupted artifacts,
and resumed completed artifacts. Ordinary parsing silently keeps only the last
value when the serialized object repeats a member name.

A raw authorization or artifact record can therefore contain contradictory
duplicate controls or input-binding members, yet reach exact schema and typed
binding validation only after one value has been discarded. This affects the
serialized authorization boundary and the recovered-artifact boundary. No
negative test requires rejection before dictionary construction.

Primary verification reproduced the behavior with contradictory duplicate
`execution_authorized` and `active_toas` members. The retained final values
passed ordinary parsing without an error.

SOL-V025-001 is consequently only partially closed at the parsed unique-key
object layer. SOL-V025-002 is fully closed. No additional P0, P2, or P3
finding was recorded.

## Scorecard

| Question | Result | Assessment |
|---|---|---|
| SOL-V025-001 exact typed binding | HOLD / partial | Recursive type-and-value comparison and live-context hashing are correct after parsing, but duplicate raw members are not rejected before parsing collapses them. |
| SOL-V025-002 nested directory durability | PASS | Every new directory entry is followed by immediate-parent `fsync`; all four family directories are durably precreated before the executor. |
| Attempt and execution context commitment | PASS | Canonical input-binding SHA-256 is present in the attempt journal and execution binding. |
| Interrupted artifact recovery | PASS with finding limitation | Live context is recomputed and unique-key parsed artifacts must match it exactly; duplicate raw members remain ambiguous. |
| File durability | PASS | File `fsync`, macOS `F_FULLFSYNC`, atomic replace, and final-parent `fsync` remain ordered. |
| Freeze verification and lock | PASS | Implementation and readiness freezes verify; execution freeze is absent; repository authorization is locked; predecessors were not loaded. |
| Repository-confined exact hashes | PASS | Compiled allowlists and all frozen hashes match. |
| Inventory preservation | PASS | The exact never-executed 344-case inventory and SHA-256 remain bound. |
| Targeted tests | PASS with coverage gap | 33/33 passed; no duplicate-member rejection test exists. |
| Science and audit boundaries | PASS | No science, external root, payload, or outcome was accessed or executed. |

## Verified identities

- Commit: `8c1dd7062246c111a49e8fcbd6f9181a04dd844c`
- Tree: `8847cf0c4d1afb5386425c351768827df2dcd916`
- Parent: `a485619eb650d78e04e13ae30d4a975510aad91a`
- Inventory: `811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`
- Aggregate implementation: `3d56ab925e87f3938f4b85ded3c8c3683e5b2d80dc14b468a9bfa6fb6ba8183e`
- Implementation freeze: `37e5b462289a2f30b16f1984269c30c53f98e948665d2f13e6068bcf1578b7f5`
- Readiness freeze: `e245e2ebb4649f1a3a589fa3b6344cc33340f950e0ac463ac729e3d87ab6f820`

## Commands and results

The auditor ran only the targeted v0.2.6 module:

```text
PYTHONPATH=src pixi run pytest -q \
  tests/test_pilot2_injection_runner_v026.py
```

Result: `33 passed in 2.94s`.

Repository-local implementation and readiness verifiers reported PASS. The
authorization verifier reported LOCKED solely because the separate v0.2.6
execution freeze is absent, with `predecessors_loaded: false`. The full
repository suite was not rerun by the auditor.

Primary verification used inert in-memory JSON strings and confirmed:

```text
{"execution_authorized":true,"execution_authorized":false}
=> {"execution_authorized": false}

{"input_binding":{"active_toas":0,"active_toas":660}}
=> {"input_binding": {"active_toas": 660}}
```

## Attestation and next gate

The auditor made no repository, Git, external-state, or data-root write. It
accessed no `/Volumes` path, external science root, run payload, scientific
outcome, random draw, timing-model fit, periodic scan, promotion grade, or
science case.

Preserve v0.2.6 and this HOLD unchanged. The next allowed step is a new
zero-science remediation version that rejects duplicate JSON member names
before dictionary construction across implementation, readiness, execution
authorization, predecessor-control, and recovered-record reads, with negative
tests for both execution authorization and artifact recovery. Freeze that new
version and obtain a fresh independent read-only audit. Science execution
remains unauthorized.
