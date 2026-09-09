# Dedicated Sol audit — B1937+21 v0.2.7

## Executive disposition: PASS

The independent read-only audit verified clean frozen commit
`63aaa9ede52caff09a6680fb32e11dfa51ba24c2`. The commit tree is
`dd9654ce40ea4be36106a531a9d4b9fccfc76b3a`, with parent
`60dc29f4a400647c17c7b99bf37fb0c1f7938e65`. The worktree remained clean
throughout the audit.

SOL-V026-001 is closed. SOL-V025-001 and SOL-V025-002 remain closed. No new
P0, P1, P2, or P3 finding was recorded.

## Finding disposition

### SOL-V026-001 — P1 — CLOSED

v0.2.7 uses one nested-object-aware JSON parser that rejects repeated member
names before dictionary construction. The entrypoint covers implementation and
readiness freezes, future execution authorization, predecessor controls, the
data-root marker, the version ledger, interrupted artifacts, and resumed
completed artifacts.

Exploit-shaped negative tests place the apparently valid value last after a
contradictory duplicate. Authorization, readiness, nested input binding, ledger
state, and marker identity all fail closed. A source guard permits only the
single object-pairs-aware `json.loads` call in the v0.2.7 runner.

### SOL-V025-001 — P1 — CLOSED AND RETAINED

Recursive exact value-and-concrete-type comparison remains intact. The
canonical live input-binding SHA-256 remains committed to both the active
attempt and execution binding. Interrupted and resumed artifacts must match the
current invocation context exactly.

### SOL-V025-002 — P2 — CLOSED AND RETAINED

File synchronization, macOS `F_FULLFSYNC`, atomic replace, and final-directory
sync remain intact. Every newly created nested case-directory entry is synced
through its immediate parent, and all four family directories are durably
precreated before the executor.

## Scorecard

| Control | Outcome |
|---|---|
| SOL-V026-001 duplicate rejection | PASS |
| SOL-V025-001 typed context and hash binding | PASS |
| SOL-V025-002 nested-directory durability | PASS |
| Interrupted artifact no-recomputation rule | PASS |
| Resumed completed-artifact strict validation | PASS |
| Exact repository-confined freeze hashes | PASS |
| Preserved 344-case inventory and seeds | PASS |
| Science, observed-data, promotion, and discovery locks | PASS |
| New P0-P3 findings | None |

## Verified identities

- Inventory SHA-256: `811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`
- Aggregate implementation SHA-256: `ff2241b6f354db7bd35c81ee715a61f2e41069d10ca5551dcc4bbe57dfb09374`
- Implementation-freeze SHA-256: `b8bf2f33ffc3334e9b03cced8cdd389f04c536cec2f6249d33ea726e801cb533`
- Readiness-freeze SHA-256: `dbf770f28f9e7105880c0a7822925613295db7197731afba7bb0d23c75d11694`

All eight implementation-freeze and ten readiness-freeze allowlist entries
matched independently. The preserved v0.2.6 audit report, primary verification,
disposition, and audit-record hashes also matched their bound values.

## Commands and results

The auditor ran only the authorized focused module:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
pixi run python -m pytest -q \
-p no:cacheprovider tests/test_pilot2_injection_runner_v027.py
```

Result: `40 passed in 2.46s`.

Repository-local verifiers reported implementation PASS and readiness PASS.
Repository authorization was LOCKED solely because the separate v0.2.7
execution freeze was absent, with `predecessors_loaded: false`. The auditor did
not rerun the full repository suite; its frozen 309-pass result remained package
evidence.

## Boundary attestation

The auditor made no repository, Git, external-state, or data-root write. It
accessed no `/Volumes` path, external science root, predecessor payload, run
payload, scientific outcome, observed residual, random draw, timing-model fit,
periodic scan, promotion grade, or science case.

## Next gate

Preserve frozen commit `63aaa9e` unchanged and record this PASS. Construct and
verify the separate v0.2.7 execution freeze binding the exact implementation,
readiness, audit, inventory, threshold, predecessors, supervision policy, and
authorized data root. Science remains locked until that freeze and the real-root
preflight both pass.
