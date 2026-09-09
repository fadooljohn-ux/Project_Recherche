# Dedicated Sol audit — B1937+21 v0.2.3

## Executive disposition: HOLD

The frozen v0.2.3 package is currently execution-locked and its hashes,
inventory isolation, PINT correction, predecessor hashes, and health-only
records check out. However, four open P1 fail-closed defects make the
“execution ready” claim unsupported.

No P0 breach was observed. No execution freeze exists, so none of these defects
has yet caused an unauthorized science run.

## Finding register

### SOL-V023-001 — P1: interruption can silently rerun a consumed case

Affected code:

- `src/pulsar_pilot/pilot2_injection_runner_v023.py:408`
- `src/pulsar_pilot/pilot2_injection_runner_v023.py:417`
- `src/pulsar_pilot/pilot2_injection_runner_v023.py:438`
- `src/pulsar_pilot/pilot2_injection_runner_v023.py:533`

Evidence: `current_case_id` exists only in memory. A case is computed before
its artifact and ledger entry are committed. `KeyboardInterrupt` is not caught
by `except Exception`. If interruption occurs during computation, or after
artifact writing but before `ledger.record_case`, the ledger contains no
completed entry. Resume therefore executes the same case and seed again.

Impact: orderly interruption is not safely resumable under one-shot
seed-consumption rules. Power loss or process termination has the same
ambiguity.

Recommendation: in a new version, durably journal the active case ID, seed, and
execution binding before computation. On restart, an interrupted attempt must
either be adopted from a verified artifact without recomputation or be consumed
and terminally stopped. Test interruptions at every commit boundary.

### SOL-V023-002 — P1: execution authorization verification is incomplete and not staged

Affected code:

- `src/pulsar_pilot/pilot2_injection_runner_v023.py:193`
- `src/pulsar_pilot/pilot2_injection_runner_v023.py:213`
- `protocol/PILOT2_INJECTION_EXECUTION_READINESS_FREEZE_v0.2.3.json:27`
- `protocol/PILOT2_INJECTION_RUNNER_PROTOCOL_v0.2.3.md:63`

Evidence:

- Once an execution-freeze file is present, predecessor records are loaded even
  when its status, authorization, boundaries, inventory, implementation, or
  readiness binding has already failed.
- Unlike v0.2.2, v0.2.3 never verifies the execution freeze’s `frozen_sha256`
  entries.
- It does not require authorization-contract fields such as exact case counts,
  no-reroll, threshold-retuning prohibition, or predecessor hashes.

Impact: a present-but-invalid or under-specified execution freeze crosses the
required “verify authorization before predecessor loading” boundary and can be
accepted without validating its full frozen contract.

Recommendation: complete all repository-local execution-freeze validation and
return immediately on any failure before receiving or inspecting a data root.
Require and verify the entire execution-freeze schema and every frozen hash.

### SOL-V023-003 — P1: readiness verifier does not require readiness to have passed

Affected code:

- `src/pulsar_pilot/pilot2_injection_runner_v023.py:88`
- `src/pulsar_pilot/pilot2_injection_runner_v023.py:128`
- `protocol/PILOT2_INJECTION_EXECUTION_READINESS_FREEZE_v0.2.3.json:6`

Evidence: the generic freeze verifier checks status, authorization,
zero-science count, inventory, implementation, and hashes, but never requires
`execution_readiness == "pass"`.

Impact: a future execution freeze could bind a readiness freeze whose readiness
result is `fail` or missing, and the runner would still accept it.

Recommendation: add a dedicated semantic readiness check requiring
`execution_readiness: pass`, plus tests for fail and missing values.

### SOL-V023-004 — P1: post-begin exceptions can bypass terminal hard stop

Affected code:

- `src/pulsar_pilot/pilot2_injection_runner_v023.py:381`
- `src/pulsar_pilot/pilot2_injection_runner_v023.py:387`
- `src/pulsar_pilot/pilot2_injection_runner_v023.py:390`
- `src/pulsar_pilot/pilot2_injection_runner_v023.py:445`

Evidence: the ledger stage begins before the protected `try` block.
Threshold-lock rehashing and execution-binding setup occur after `begin_stage`
but before `try`. An exception in that interval leaves the ledger running
without the promised terminal result or hard stop.

Impact: the core v0.2.2 secondary failure mode remains reachable through a
smaller pre-case window.

Recommendation: place every operation after stage activation inside the
terminalization boundary and add an integration test that induces failure
immediately after `begin_stage`.

### SOL-V023-005 — P2: validation does not exercise the claimed recovery boundaries

Affected evidence:

- `tests/test_pilot2_injection_runner_v023.py:115`
- `tests/test_pilot2_injection_runner_v023.py:137`
- `results/pilot2/injection_execution_readiness_v0.2.3.json:25`
- `docs/PILOT2_INJECTION_EXECUTION_READINESS_v0.2.3.md:30`

Evidence: exception testing calls the terminalization helper directly rather
than exercising `execute`. Authorization-boundary testing covers only an absent
execution freeze. There are no interrupt-boundary, malformed-present-freeze,
failed-readiness, or post-stage-begin exception tests. The recorded “199 passed
/ 3 deselected” claim does not preserve the exact command or deselected test
IDs.

Impact: the central fail-closed defects above were outside the asserted
readiness validation.

Recommendation: preserve a machine-readable validation manifest and add
zero-science integration tests for each boundary.

No P3 findings were necessary.

## Scorecard

| Gate | Result |
|---|---|
| Target commit `a3db08b` and version isolation | PASS |
| v0.2.2 ledger, health, setup-log and crash preservation | PASS |
| 344 unique cases and 35 audits | PASS |
| Family counts and ordering | PASS |
| Entire-inventory ID/seed disjointness from v0.2.1 and v0.2.2 | PASS |
| Current remediation, implementation and readiness hashes | PASS |
| Aggregate implementation hash | PASS |
| PINT object-property correction | PASS |
| Legacy text getter avoided | PASS |
| Threshold and predecessor hash immutability | PASS |
| Unexpected-exception terminalization coverage | FAIL |
| User-interrupt/resume integrity | FAIL |
| Preauthorization loading boundary | FAIL |
| Readiness semantic gate | FAIL |
| Execution-freeze contract verification | FAIL |
| Health-only outcome isolation | PASS |
| Observed-data, promotion, retuning and rerun prohibitions | PASS |
| Current execution lock | PASS — execution freeze absent |
| Safe audit tests | PASS — 7/7 |
| Claimed full 199-test run | N/A — not rerun under this audit’s no-science boundary |

## Verified hashes

- Commit: `a3db08b3776e4a6a4d144b0a5b0cd9f62b44baea`
- Inventory: `811c46d4d7e6137df8e50ac560449132f590e8abbbc6c851bf77e9e4214eac7b`
- Aggregate implementation: `23d093c816c1fd6e029ffa7ac83ef4175b8c60028013ac6bf51f004bcfa58a34`
- Remediation freeze: `bf243b80307c0ddc773c85f244ef59854ce06de800bd0a74ffe2d2c1f1a8cd23`
- Runner freeze: `fcb8ad7714b13283ce251d74ac28e07643ae98d1e4e027c42e0c7ec8e7acf46e`
- Readiness freeze: `96d38b5b495ef8322143f30d343a007f6181133c9f777dada9f58164e1ca6c16`
- v0.2.2 crash audit: `6d58ef1be4a03969be41ee3e0d916adaa252ee5bfa42d7c23244f203f878b473`
- External v0.2.2 ledger: `9d0c2c2d1bef17cd4197975b899fc46fa2866c2111eeeee9931234290afcde19`
- External v0.2.2 health: `292113f3663d47e74d12484aea19d054414d3e96b28c05972647a48a99c7ecf8`
- External v0.2.2 setup log: `f456bc3109931d9af286344687c54dc2f88d43bd079d9bbfb7b90323fa84a073`

All frozen-entry hash comparisons passed. All five v0.2.1 predecessor hashes
matched without inspecting their contents.

## Residual limitations

The audit did not run the complete repository suite because its safety boundary
was not independently classified test by test. Seven manifest, inventory,
PINT, freeze, source-boundary, and crash-audit tests were run without cache or
bytecode writes and passed. No fitted PINT model was executed.

No case artifacts, injection metrics, triggers, candidates, phase results,
observed residuals, or sealed scientific outcomes were inspected.

## Attestation and exact next gate

This was a dedicated Sol audit; Fable was not used. I made no repository or
external-data changes. Git status remains exactly the two pre-existing
untracked audit-framework files. I executed zero science cases, random draws,
timing-model fits, or periodic scans.

The exact next gate is:

1. Preserve this report verbatim.
2. Have the primary agent independently reproduce every P1 and P2 finding.
3. Do not create a v0.2.3 execution freeze or execute science.
4. If the findings are confirmed, obtain separate user authorization for a new
   zero-science remediation version and freeze.
5. Submit that new frozen version to a fresh dedicated Sol audit before any
   separate science-execution authorization.
