# Dedicated Sol audit — B1937+21 v0.2.5

## Executive disposition: HOLD

Target verified at clean commit
`96bfd5919cd538915e3f4177112452c34f5e8c65`. The worktree remained clean
after the independent review.

Two material gaps remain. SOL-V024-003 is closed, but SOL-V024-001 is only
partially closed and SOL-V024-002 remains open.

## Finding register

### SOL-V025-001 — P1: recovered-artifact input binding is not exact

`_validate_input_binding()` compares several fields using Python equality, so
integer `0` satisfies required `False`, floating-point values satisfy required
integers, and shape elements are not type-checked. More importantly,
`reference_epoch_mjd_tdb` and `span_days` need only be finite;
`frequency_count` may be any integer at least two with only local step
consistency.

The trusted current context is not supplied to
`validate_complete_case_record()`. An artifact from a materially different
input context can therefore pass and be adopted without recomputation. This
contradicts the claimed complete, exact input-binding and type contract and
leaves SOL-V024-002 open.

### SOL-V025-002 — P2: first-use case-artifact directories are not fully durable

`_durable_atomic_json()` may create multiple parent directories but
synchronizes only the final containing directory. The first case write can
create the previously absent `derived/.../injections/<family>` chain. Directory
entries in newly created ancestors are not individually persisted.

Attempt-ledger and terminal paths already have established parents, but the
claimed power-loss durability of first-use case artifacts is incomplete.
SOL-V024-001 is therefore only partially closed.

No P0 or P3 findings were recorded.

## Scorecard

| Question | Result | Assessment |
|---|---|---|
| SOL-V024-001 durability | HOLD / partial | Active-attempt ordering is correct: flush, file `fsync`, macOS `F_FULLFSYNC`, replace, then directory `fsync`, all before executor. Sync failures stop before execution and terminalize. Newly created case-directory chains remain insufficiently synchronized. |
| SOL-V024-002 complete schema | HOLD | Exact top-level keys, case, binding, threshold, family candidate field, finite top-level values, boundaries, and solver schemas are checked. Input-binding identity and concrete types are not exact. |
| SOL-V024-003 confined hashes | PASS | Freeze maps must equal compiled path sets before hashing. Absolute, traversal, missing, extra, symlinked, and escaping paths fail closed. |
| Freeze verification and lock | PASS | Implementation and readiness pass. Execution freeze is absent; gate is locked; predecessors were not loaded. |
| Inventory reuse | PASS | Runner calls `build_v023_inventory()` directly; 344 cases and the inventory SHA-256 verify. |
| Executor wrapper | PASS | v0.2.5 delegates unchanged computation to v0.2.3 and changes only schema and run identity. |
| Health and science boundaries | PASS | Health excludes case identity and outcomes. Observed-data, retuning, promotion, and discovery boundaries remain false. |
| Targeted tests and manifest | PASS with historical limitation | 24/24 targeted tests passed. The 236-pass/3-deselection command and exact IDs are preserved but were not rerun by the auditor. |

SOL-V024 dispositions:

- SOL-V024-001: partial and remains open.
- SOL-V024-002: remains open.
- SOL-V024-003: closed.

## Verified hashes

- Commit: `96bfd5919cd538915e3f4177112452c34f5e8c65`
- Inventory: `811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`
- Aggregate implementation: `7f8760106c4c850e6d2eec6ef8dbc307784d6a01b7a21ba8d1254aab2ef5cc4d`
- Implementation freeze: `dcb3a961f2a1e8ef07811f5f50aeeb9dfdbec6a83a61fec95d445986de05ef2d`
- Readiness freeze: `15f894c927eefbc02598fb8b53d79cf65e1bf1c7c13c09bd52edf253f4238825`
- Validation manifest: `29eeca4ab788044726c529c6b480c2af53de45aaa88193c508e45bf4917694dc`
- Zero-science validation: `933b38f85ba19e04cfa9744f94c143fb1e23808610aa308fd36e6023431881c7`
- Readiness result: `d922376119d51f7156f629a18ae96e5d5d28a578e2b03769fcd397cfc7c16d4e`
- Finding closure: `7f175ff48645313e8e669fc3c5850790f211a547e1f98a09830b8d613f3003c5`
- Runner: `47e9ae30decf165c13da49dd21e579eac8cffaa44a206ed264ad370a7bfc2e49`
- Executor: `a69f9941951f33b183151a35a91d58ecba060634cb7e652baa7570bd6784a96b`
- Tests: `ae69b71a32802170dcdf2dc7a57527efb1563640c0e9efa921f290bea877177f`

## Commands and results

```text
GIT_OPTIONAL_LOCKS=0 git rev-parse HEAD
GIT_OPTIONAL_LOCKS=0 git status --short --untracked-files=all
```

Result: target commit verified; worktree clean before and after.

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pixi run \
  python -m pytest -q -p no:cacheprovider tests/test_pilot2_injection_runner_v025.py
```

Result: `24 passed in 2.33s`.

Repository-local implementation, readiness, authorization, and gate verifiers
reported implementation PASS, readiness PASS, authorization and gate LOCKED,
execution freeze absent, and `predecessors_loaded: false`.

## Attestation and next gate

The auditor executed zero science cases, random draws, timing-model fits, and
periodic scans. It accessed no `/Volumes` path, external science root,
predecessor, observed residual, scientific outcome, trigger, candidate, or
prior science metric. It made no repository or external-data write and created
no execution freeze.

The exact next gate is to preserve v0.2.5 and its HOLD. A new zero-science
remediation version must validate exact input-binding values and concrete types
against a trusted binding, with mutation tests, and durably create and
synchronize every new case-directory component, with a first-use nested-
directory test. Science execution remains unauthorized.
