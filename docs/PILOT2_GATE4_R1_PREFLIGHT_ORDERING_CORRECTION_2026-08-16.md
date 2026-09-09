# Pilot 2 Gate 4-R1 preflight-ordering correction

Date: 2026-08-16

Status: **DESIGN COMPLETE — implementation and real-root access remain unauthorized**

## 1. Why this correction exists

Gate 4 requires the existing IOC harness to inspect the designated science root,
construct the exact scientific context twice without running science, create the
resource and environment manifests, and then pass preflight. Gate 5 follows and
creates the execution freeze.

The current harness enforces those steps in the opposite order: its `preflight`
command first requires the Gate 5 execution freeze. Therefore Gate 4 cannot pass
without taking authority that belongs to Gate 5.

In plain English, the safety inspection currently demands the final launch
permit before it will perform the inspection needed to issue that permit.

This is an ordering defect. It is not a scientific failure, a data-root failure,
or a reason to create another harness.

## 2. Controlling baseline

- repository commit: `d623677908c433ec94cc61bf7d394d8f0167178b`
- repository tree: `9cbac6f191f6965844fd5bd86ce9a51a8d57d587`
- operational IOC plan SHA-256:
  `e1a1d97cfeb3482bb413feee53ce7d2426ff7f9542b2f51cb271ad0b8bd19ec9`
- Gate 2 closeout SHA-256:
  `018e3b52b003328041a1c45d181865d26c459331ed5024604dbc7f2a8ac3c8de`
- Gate 3 closeout SHA-256:
  `2bf935ec454bba40cda70e7545e510525baaba1d310e866bb5ca67ac838159c5`
- IOC harness SHA-256:
  `efa024cb5d6665e3969dbdb33475a0522b8a895a44b7195fd57cfff7dd315ca0`
- science adapter SHA-256:
  `e97b1f87cfbf633ea70721d9dba73fb2ae95fa72e32a5f1901bbd8860cf37d1f`
- release contract SHA-256:
  `3821a73c0cc30a9ce4600e567796086817505a7467b6b35d70ca56b9123dcdc6`

At this baseline the worktree was clean, no Pilot 2 process was active, and the
IOC execution freeze and both runtime manifests were absent. No external volume
was accessed while diagnosing the ordering defect.

## 3. Decision

Keep the existing `preflight` command and give it one narrow, fail-closed Gate 4
qualification route. Do not add another command, harness, runner, observer,
daemon, broker, or retry path.

The existing command will distinguish two exact authority schemas:

1. **Gate 4 preflight authority** permits only zero-science inspection,
   two context constructions, manifest creation, and preflight evidence.
   It contains no execution permission and requires no execution freeze.
2. **Operational execution authority** retains the current behavior and remains
   invalid until the Gate 5 execution freeze exists and passes.

The Gate 4 authority can never be accepted by `prepare` or `run`. The operational
authority can never be inferred from a Gate 4 PASS.

## 4. Exact Gate 4 behavior

Under a separately approved Gate 4 execution attempt, the operator will invoke
the existing `preflight` command once through a hash-recorded macOS process-level
network-denial wrapper. The wrapper is the system `/usr/bin/sandbox-exec` with
the fixed profile `(version 1)(allow default)(deny network*)`; its executable
hash must be recorded and verified immediately before launch. That invocation
must:

1. verify the clean repository commit/tree and fixed science-module identity;
2. before any external-root access, verify the hash-bound Gate 2 and Gate 3
   receipts and run the existing v0.2.8 zero-case dry run in two fresh disposable
   roots, requiring all 13 criteria to pass in each root with zero science;
3. verify an exact Gate 4 authority binding the canonical science-root path,
   data-root ID, marker SHA-256, evidence destination, and manifest destinations;
4. verify the designated host and storage before scientific-context loading;
5. construct candidate resource and environment manifests in memory from the
   fixed local inventory and live environment, without publishing them;
6. construct the exact B1937+21 context twice using that same candidate resource
   manifest and the same `pilot2_runtime_core.prepare_context` function used by
   execution;
7. require both resource-open traces to equal the candidate manifest exactly,
   then validate and write the final resource and environment manifests;
8. deny and count network activity in both the outer process policy and the
   existing in-process resource boundary;
9. record the two context bindings independently and require exact agreement;
10. perform the backup/restore-boundary verification already required by Gate 4,
   treating the recorded v0.2.1 verified-copy history as provenance only and
   not as proof that the current restore check passed; and
11. write one create-once Gate 4 receipt and exit.

The invocation must record zero:

- connection attempts and downloaded bytes;
- qualification cases and random draws;
- primary fits and solver audits;
- periodic scans and observed-residual reads;
- science-entry calls;
- science run-root creation; and
- scientific result, ledger, mask, case, or scorecard artifacts.

Context setup logs, manifest files, and Gate 4 evidence are qualification
evidence, not scientific artifacts. Every permitted output path must be named by
the Gate 4 authority before the first external-root read.

## 5. Fail-closed separation

The Gate 4 route must fail before external-root access if the authority,
repository, module identity, host, canonical path, data-root ID, marker,
network-denial identity, evidence paths, or zero-science policy differs.

It must fail after inspection if either context construction differs, any
network or science counter is nonzero, a manifested resource is missing or
unexpected, the live environment differs, an unauthorized output appears, or
the restore-lineage evidence is incomplete.

Failure is terminal evidence for that Gate 4 attempt. There is no automatic
repair, retry, fallback, resume, or conversion into execution authority.

The execution freeze remains mandatory for `verify-gate`, `prepare`, and `run`.
This correction does not weaken or bypass the existing operational launch gate.

## 6. Prospective implementation limit

A later implementation stage may modify only the existing minimal path needed
to realize this decision:

- `src/pulsar_pilot/pilot2_ioc_harness.py`;
- `src/pulsar_pilot/pilot2_science_module.py`;
- `src/pulsar_pilot/pilot2_release_contract.py`, only if the exact Gate 4
  authority validator cannot remain in the harness;
- `src/pulsar_pilot/pilot2_offline_resources.py`, only for deterministic
  manifest construction;
- `src/pulsar_pilot/pilot2_runtime_core.py`, only if a zero-science evidence-log
  destination cannot be supplied without changing scientific construction;
- `tests/test_pilot2_ioc_harness.py`; and
- `tests/test_pilot2_science_module.py`.

Defaults and the operational execution path must remain unchanged. If a new
operator command, alternative context constructor, copied science path, service,
observer, broker, general scheduler, eighth implementation/test path, or
execution-freeze workaround is required, stop as a design spiral.

## 7. Acceptance for the later implementation

Finite disposable tests must prove:

- Gate 4 authority is accepted only by `preflight`;
- `prepare` and `run` reject it before run-root creation;
- operational authority still requires the execution freeze;
- the exact context function is called twice and no executor is called;
- manifests and both context receipts are exact and create-once;
- every named non-science counter remains zero;
- nonzero counters, changed bindings, changed manifests, or unauthorized paths
  fail closed; and
- the operator surface remains exactly `verify-gate`, `preflight`, `prepare`,
  `run`, and `status`.

Disposable acceptance may not access `/Volumes`, create production manifests or
freezes, run the real context, or execute science.

## 8. Authority and stop boundary

The owner's current approval authorizes this design document only.

It authorizes no source or test edit, validation command, external-root access,
manifest creation, backup or restore operation, freeze, audit, commit, push,
Gate 4 attempt, Gate 5 work, or science.

Stop after reporting this document's exact SHA-256. A later implementation
requires separate owner approval of this exact document. A later real-root
Gate 4 attempt requires another separate approval after implementation and
disposable acceptance pass.
