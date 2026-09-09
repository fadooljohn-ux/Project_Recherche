# Pilot 2 Gate 2A-R1 science-binding compatibility decision

- **Date:** 2026-08-16, Asia/Taipei
- **Status:** design complete; implementation HOLD pending separate owner approval
- **Gate:** 2A-R1, design only
- **Repository HEAD:** `05142087ee2e9c8f661e27b83d0b9ee9159b4f7f`
- **Repository tree:** `7f227bcbc2bcba8a577a9728f2ac47a869474cf2`

## 1. Authority and stop boundary

The owner's `Proceed` authorized one short compatibility decision after Gate 2A
stopped fail-closed. This document is the only authorized write.

This gate does **not** authorize source, test, configuration, protocol,
evidence, or controlling-plan changes; imports or test execution; process
launch; a data-root read; network access; adapter binding; manifest or freeze
creation; a commit; or science. Stop after reporting this document's SHA-256.

This decision is prospective. It does not alter the v0.2.8 HOLD, revive either
retired qualification stack, regrade any terminal attempt, or satisfy Gate 2.

## 2. Bound baseline

| Artifact | SHA-256 | Disposition |
|---|---|---|
| `docs/PROJECT_RECHERCHE_OPERATIONAL_IOC_PLAN_2026-08-15.md` | `8e82c469ff49a44de64a662dbdb73685a0e1e6cf79f95a0d97e455883b7eb341` | controlling |
| `docs/PILOT2_MINIMAL_IOC_HARNESS_RESET_2026-08-16.md` | `a1aaf726160f22aea62bcb1a4ede9f4ff4f8fa4c6781f26b9a42d45d6745d35f` | controlling reset |
| `src/pulsar_pilot/pilot2_ioc_harness.py` | `f16c053e6a48785208a2e619fef48a48b0f1ad7ddb7cf3e0b255d10522a3e9a8` | fresh outer harness |
| `src/pulsar_pilot/pilot2_runtime_core.py` | `5d69608eacc5fa3014e19ff23526aea3d4f0fb020dd9172a4d1b28bb42f81efe` | preserved inner engine |
| `src/pulsar_pilot/pilot2_release_contract.py` | `019e3c6bfe681b92c50fb34c86bc938cd5822db44dfd13634f86e8121984d0c5` | preserved v0.2.8 contract |
| `src/pulsar_pilot/pilot2_durable_ledger.py` | `94a82393bfd659932b00a40e8a9eca4fe47a118d42a0de967c4e9ce0b6483bde` | immutable inner artifact identity |
| `src/pulsar_pilot/pilot2_injection_runner_v028.py` | `592b02a58bae31c54d7998a4dc445b225232b73cdd5eceb3be208a48976f2e0b` | preserved legacy route; successor-locked |

Gate 2A established that the scientific computation has one real internal
entry, `pilot2_runtime_core.execute(data_root)`, but the fresh IOC authority and
manifest do not bind its required science data root. The old release contract
also names the legacy runner and permits resume or `already_complete`, while the
new IOC contract consumes interruption or failure terminally. An adapter alone
cannot reconcile those facts.

## 3. Compatibility decision

Retain the fixed v0.2.8 runtime, ledger paths, science run ID, constructors,
inventory, thresholds, numerical work, and artifacts as the **inner scientific
engine** of a new outer science-module release. The inner identity is provenance
and evidence, not current authority or a v0.2.8 PASS.

The accepted operational chain is exactly:

```text
operator
  -> pulsar_pilot.pilot2_ioc_harness run
  -> pulsar_pilot.pilot2_science_module:SCIENCE_MODULE.run
  -> pilot2_runtime_core.execute in successor-bound, fresh-only mode
```

There is no second runner, observer, poller, supervisor, daemon, broker,
dashboard, retry path, copied release stack, or alternative science engine.
The five foreground harness commands remain unchanged.

The outer module identities for the prospective implementation are:

- `module_id = "pilot2-b1937-injection-science"`; and
- `release_id = "pilot2-b1937-injection-science-ioc-v1"`.

The fixed inner science identity remains
`pilot2-b1937-injection-remediation-v0.2.8`. Generalizing its approximately
version-coupled ledger and artifact surface is explicitly rejected.

## 4. Exact science-execution binding

The external operator authority gains one exact `science_execution` object.
The write-once IOC manifest copies it unchanged:

```json
{
  "schema": "pilot2-science-execution-binding-v1",
  "ioc_run_id": "<exact outer run ID>",
  "module_release_id": "pilot2-b1937-injection-science-ioc-v1",
  "science_run_id": "pilot2-b1937-injection-remediation-v0.2.8",
  "execution_freeze_sha256": "<64 lowercase hex>",
  "inventory_sha256": "811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b",
  "expected_accounting": {
    "cases": 344,
    "primary_fits": 688,
    "solver_audits": 35
  },
  "science_data_root": {
    "canonical_path": "<absolute operator-authorized path>",
    "data_root_id": "<exact stable ID>",
    "marker_sha256": "<64 lowercase hex>"
  },
  "fresh_only": true,
  "resume_authorized": false
}
```

Rules:

1. `authority.run_id == science_execution.ioc_run_id == manifest.run_id`.
2. The module release and fixed inner run ID must match the loaded adapter and
   durable ledger constants exactly.
3. The committed execution freeze binds the data-root ID and marker hash, not
   an absolute machine path. The external operator authority supplies the path.
4. The adapter uses only the manifest path. `RECHERCHE_DATA_ROOT`, cwd,
   ancestry, discovery, and fallback selection are forbidden.
5. `verify-gate` may validate schema and repository authority without resolving
   or opening the root. Canonical-path and marker verification remain locked
   until the separately authorized real-root preflight gate.
6. The successor verifier requires the legacy v0.2.8 execution freeze to remain
   absent. The historical runner therefore remains preserved but locked.

## 5. One outer identity to one fresh inner attempt

The execution freeze binds the exact pair `(ioc_run_id, science_run_id)`. The
IOC manifest SHA-256 becomes an input to the successor science execution-binding
hash already carried by the inner ledger and terminal result.

The outer identity is consumed when the harness durably records `run_started`.
The inner identity is eligible only if, under its existing single-writer lock,
all of the following are true:

- the ledger is absent or exactly pristine and pending;
- completed cases, attempts, checkpoints, stage results, and hard stop are
  empty;
- no terminal result, annual mask, or case artifact exists; and
- neither `already_complete` nor `resume_runtime` would be entered.

Any non-fresh state refuses execution before a case, draw, fit, or scan. No new
IOC identity may adopt or resume the fixed inner attempt. The existing
v0.2.8-default call behavior may remain for historical compatibility, but it is
not accepted by the successor verifier and receives no successor authority.

## 6. Stop and terminal semantics

- `KeyboardInterrupt` terminalizes the inner ledger as
  `operator_controlled_stop`, consumes any active attempt, and re-raises so the
  outer harness records `controlled_stop`.
- Any other `BaseException` terminalizes the inner ledger as
  `operational_failure` and re-raises so the outer harness records the same
  operational class.
- Process death, released OS locks, partial artifacts, or a missing closeout
  receipt never confer resume authority.
- There is no retry, recovery, artifact adoption, recomputation, top-up, or
  `already_complete` success on the successor path.
- Completion of all 344 cases is outer operational `complete` even if a sealed
  scientific gate fails. Scientific PASS/FAIL is reviewed only at the later
  terminal-science gate and is never relabeled as an operational failure.

## 7. One outcome-free status surface

`status.json` remains the only operator/AI health surface. Only the foreground
runtime call path may call `publish_status`, synchronously after initial
binding and each durable case/checkpoint transition, mapping only:

- stage;
- completed and total cases;
- last durable checkpoint; and
- the status update time supplied by the harness.

The adapter returns the existing exact
`{completed, total, checkpoint}` completion record. The inner health file may
remain an artifact, and its existing internal heartbeat writer may remain
unchanged, but it never calls the outer callback. The harness does not poll,
mirror, serve, or supervise it. No callback-bearing background thread or second
status writer is permitted. If foreground checkpoint updates prove
operationally insufficient, stop for owner direction rather than add a service.
No scientific score, gate result, threshold outcome, fitted value, diagnostic,
or discovery content enters status.

## 8. Inner/outer evidence chain

Before returning or re-raising, the adapter creates the sole additional
write-once adapter receipt, outcome-free `science-evidence-binding.json`, in the
IOC run root. This receipt is required because the current terminal inventory
cannot otherwise bind artifacts outside its run root. It contains:

- the paired run IDs and IOC manifest SHA-256;
- execution-freeze, inventory, data-root-ID, and marker hashes;
- the inner execution-binding hash, when created;
- completed/total/checkpoint and fixed fit/audit accounting;
- logical paths, byte counts, and SHA-256 values for each inner ledger,
  terminal result, annual mask, and health artifact that exists;
- a `hard_stop_present` boolean derived from the bound ledger; and
- `scientific_outcomes_visible: false`.

It does not contain scientific status or payload. The harness validates the
receipt's schema, paired IDs, manifest hash, and accounting before closeout.
The existing outer terminal inventory then hashes the receipt:

```text
outer manifest SHA
  -> inner execution-binding SHA
  -> inner artifact hashes
  -> outer science-evidence-binding SHA
  -> outer terminal inventory SHA
```

If abrupt process death prevents the receipt, its absence is terminal incident
evidence, not permission to recover or resume.

## 9. Smallest prospective implementation gate

A later Gate 2A-R2 may change exactly these six paths:

1. `src/pulsar_pilot/pilot2_ioc_harness.py`;
2. `src/pulsar_pilot/pilot2_science_module.py` (new);
3. `src/pulsar_pilot/pilot2_release_contract.py`;
4. `src/pulsar_pilot/pilot2_runtime_core.py`;
5. `tests/test_pilot2_ioc_harness.py`; and
6. `tests/test_pilot2_science_module.py` (new).

Release-contract and runtime changes must be narrow, additive successor seams;
their defaults preserve the historical v0.2.8 behavior. Do not edit the
durable ledger, legacy runner, executor, configuration, historical tests,
thresholds, inventory, constructors, scanners, fitters, graders, or evidence.

Finite zero-science acceptance must prove exact schema and cross-hash binding,
no environment root fallback, legacy-route lockout, fresh-state refusal,
no-resume behavior, interruption/failure mapping, outcome-free status, exact
receipt closure, and zero calls to cases/draws/fits/scans. These contract tests
do not satisfy the later real-entry scientific parity requirement.

Stop Gate 2A-R2 if a seventh path, copied science logic, configuration fork,
second route, observer, polling loop, subprocess control, retry, historical-test
edit, or numerical/scientific change is required. Also stop if retaining the
fixed v0.2.8 inner artifact identity is rejected; do not generalize it or create
another release stack.

## 10. Gate closeout

Gate 2A-R1 produces this document only. Gate 2 remains incomplete. Gate 2A-R2,
real-root preflight, implementation/freezes, process launch, 344-case science,
observed-data access, commit, push, backup, and publication are unauthorized.

The next possible action is owner review of this exact document and SHA-256.
Approval must expressly name Gate 2A-R2 and the six-path, zero-science
implementation boundary. Nothing begins automatically.
