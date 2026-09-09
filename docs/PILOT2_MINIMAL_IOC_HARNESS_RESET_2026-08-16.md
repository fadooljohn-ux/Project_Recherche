# Pilot 2 minimal IOC harness reset

- **Date:** 2026-08-16, Asia/Taipei
- **Status:** authorized zero-science harness replacement stage
- **Recovery commit:** `b8190d3b2d4dee2b7dc38fb8c2cff66fc7f131bb`

## Current reset instruction

Retire and remove both qualification-harness implementation stacks:

- the v0.2.9 harness, observer, and test files; and
- the v0.2.10 harness, observer, and test files.

Preserve the v0.2.9 historical design, erratum, closeout, and recorded failure
result. Preserve the external v0.2.10 terminal acceptance evidence; do not copy
its receipt into the repository. Preserve all Pilot 2 science/runtime code,
configuration, snapshots, and other historical evidence.

The five v0.2.10 candidate paths and the three v0.2.9 executable paths are
recoverable from Git. The reset does not authorize deletion of any preserved
historical evidence or modification of the controlling governance policy.
This replacement stage binds no science adapter, data root, network, or science
execution, and does not authorize a commit.

## Failure log

The retired designs are not to be revived because the observed failure pattern
was architectural:

1. The meta-harness became larger and more operationally complex than the
   product under qualification.
2. Recursive sandbox/process topology failed at nested child creation.
3. Observer, counter, and receipt-schema drift created repeated alignment work.
4. Fixtures and APIs became stale or fabricated relative to the live verifier.
5. One-shot attempt identity enforcement was nonpersistent across invocations.
6. The work consumed effort without advancing the science roadmap.

## Do-not-repeat boundary

Do not add a custom pytest observer, run the full suite inside the operational
harness, create nested sandboxes, perform snapshot gymnastics in the operational
conductor, or introduce a daemon, broker, background service, or retry path.
Use direct lifecycle tests and one authoritative science entry point.

## Minimal foreground architecture

Any successor is limited to the plan's existing five finite foreground
commands:

1. `verify-gate` — verify the active authority and stop boundary;
2. `preflight` — verify source, environment, and repository identity;
3. `prepare` — construct only the bounded zero-science execution context;
4. `run` — invoke the separately bound science module once in the foreground;
   and
5. `status` — report the fixed outcome-free lifecycle and process metadata.

Under this reset, the implemented commands have explicit zero science, zero
data-root, and zero network authority. The `run` command therefore fails closed
until a later stage separately binds and authorizes the single authoritative
science-module entry point.

## Stop and recovery

The retired blobs remain recoverable from commit
`b8190d3b2d4dee2b7dc38fb8c2cff66fc7f131bb`; no destructive Git reset is part of
this document. The replacement implementation stopped before commit. The
owner's subsequent `Proceed` authorized only the clean reset commit; science
adapter binding, data-root access, network access, and science execution remain
locked.
