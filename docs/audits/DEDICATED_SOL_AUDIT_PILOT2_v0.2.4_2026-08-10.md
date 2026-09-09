# Dedicated Sol audit — B1937+21 v0.2.4

## Executive disposition: HOLD

Target commit verified: `96cc62470002b1328407f24c98c3e4d2a7e34eca`.
The worktree was clean before and after the audit.

v0.2.4 closes several v0.2.3 defects, but does not yet justify its overall
implementation/readiness PASS claim.

## Finding register

### SOL-V024-001 — P1: attempt journal is atomic but not power-loss durable

`begin_attempt()` saves before the executor call, but `_atomic_json()` only
writes, closes, and calls `os.replace()`. It does not `fsync` the file or the
containing directory. The prior audit explicitly included power loss and
process termination. A power failure can therefore lose the journal after the
code proceeds to computation, preserving the original rerun ambiguity.

Evidence: `src/pulsar_pilot/pilot2_calibration_runtime.py:34-38` and
`src/pulsar_pilot/pilot2_injection_runner_v024.py:431-434,699-707` at the target
commit.

### SOL-V024-002 — P1: recovery does not fully verify an adoptable artifact

`_verified_attempt_artifact()` validates only case equality and execution
binding. It does not validate schema version, run ID, required scientific-record
keys and types, family fields, boundary flags, or executor-record completeness.
The recovery test deliberately supplies only `case` and
`execution_binding_sha256` and confirms that it is adopted and ledgered. This
contradicts the claim of a fully verified artifact.

Evidence: `src/pulsar_pilot/pilot2_injection_runner_v024.py:548-566` and
`tests/test_pilot2_injection_runner_v024.py:251-274` at the target commit.

### SOL-V024-003 — P1: execution-freeze hash paths are neither confined nor exact

The verifier joins each supplied key with the repository root and hashes it
without rejecting absolute paths or `..` escapes. A crafted present freeze can
therefore make repository-local authorization read an external file before
authorization completes. The verifier also accepts any nonempty hash map; the
full-contract test passes with only the runner configuration hashed. This does
not enforce an exact frozen-file contract.

Evidence: `src/pulsar_pilot/pilot2_injection_runner_v024.py:318-325` and
`tests/test_pilot2_injection_runner_v024.py:156-194` at the target commit.

No P0, P2, or P3 findings were recorded.

## Scorecard

| Audit item | Result | Assessment |
|---|---|---|
| Durable journal, recovery, and annual commits | HOLD | Journal precedes executor; missing artifacts hard-stop; ledger reconciliation and annual per-case ordering are correct. Storage durability and full artifact validation fail. |
| Authorization before predecessor access and full contract | HOLD | Absent, malformed, and ordinary missing fields fail before predecessor loading. Arbitrary hash paths can still cause external reads, and no exact hash-key set is required. |
| Explicit readiness PASS, boundaries, and hashes | PASS | `execution_readiness == "pass"` is mandatory; current boundaries and listed hashes verify. |
| Terminalization boundary and KeyboardInterrupt | PASS | Ordinary post-stage operations are terminalized; KeyboardInterrupt preserves the active attempt. |
| Tests and manifest | HOLD | Targeted 13/13 passed and exact commands/deselections are preserved, but the material durability, artifact-schema, path-containment, exact-set, and annual-interruption boundaries are not covered. |
| Freeze verification and current lock | PASS | Both freezes verify; execution is locked; predecessors were not loaded. |
| Exact v0.2.3 inventory reuse | PASS, repository-local | 344 cases and inventory SHA-256 reproduced; no v0.2.3 or v0.2.4 execution freeze exists. |
| Outcome-free health and science boundaries | PASS | Health excludes case identity and scientific outcomes; observed-data, retuning, promotion, and discovery boundaries remain false. |

Prior-finding disposition:

- SOL-V023-001: not closed — SOL-V024-001 and SOL-V024-002.
- SOL-V023-002: not closed — SOL-V024-003.
- SOL-V023-003: closed.
- SOL-V023-004: closed.
- SOL-V023-005: not closed — evidence improved, but remaining material
  boundaries are untested.

## Verified hashes

- Commit: `96cc62470002b1328407f24c98c3e4d2a7e34eca`
- Aggregate implementation: `e36f958626b46f57db23aae537dd320473f642333fae3b3e1fdf8e2edc5a11e0`
- Inventory: `811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`
- Implementation freeze: `3c7ba5cc1f99cada848c158766a97d47fda19f6a2a75295429bf0e34433e2845`
- Readiness freeze: `27af873355a6892ea5fb390a3c37b4bee8d24a736c7052a08562fd459a88fb68`
- Runner source: `825195d9aa8769fde920996db64186e477bc61fc06c83986f7588e3560ab8960`
- Tests: `dde290f1c70592d743a3ff820695f49e6a331245fe02f7d4996391fe4674935b`
- Validation manifest: `f583a74a353e773179d0f9f8a166f49b4bfd803c32f8d26b91a862956b158408`
- Zero-science validation: `7b2ec6502c949f5d6df05b0f385ee655c9600e8fee3992be90f261d93f691963`
- Readiness result: `efe480af331d62ce57c749cd2f5a6af3124fb7077f63c9d4f9f99e64e5490255`
- Closure record: `ac1592724e03519e4e41cfca1eb208a9e7d459766a502e37dc082e31f3b4e1e6`

## Exact permitted validation run

```text
PYTHONPATH=src pixi run python -m pytest -q tests/test_pilot2_injection_runner_v024.py
```

Result: `13 passed in 1.55s`.

```text
PYTHONPATH=src pixi run python -m pulsar_pilot.pilot2_injection_runner_v024 verify-implementation
```

Result: PASS.

```text
PYTHONPATH=src pixi run python -c 'import json; from pulsar_pilot.pilot2_injection_runner_v024 import verify_readiness_freeze; print(json.dumps(verify_readiness_freeze(), indent=2, sort_keys=True))'
PYTHONPATH=src pixi run python -m pulsar_pilot.pilot2_injection_runner_v024 verify-gate
```

Results: readiness PASS; execution locked; execution freeze absent;
`predecessors_loaded: false`.

## Attestation and next gate

The auditor executed zero science cases, random draws, timing-model fits, or
periodic scans; inspected no scientific outcomes; accessed no `/Volumes` path
or external science root; created no execution freeze; and made no repository
changes.

The exact next gate is to keep execution locked and create a new zero-science
remediation version that adds true file-and-directory durability, validates the
complete recovered-artifact schema, confines frozen hash paths to an exact
repository-relative allowlist, and adds the corresponding boundary tests. Only
a later independent PASS may precede separate explicit execution authorization.
