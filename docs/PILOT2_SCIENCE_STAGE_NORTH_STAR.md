# Pilot 2 science-stage North Star

## Governing sequence

This roadmap controls Project Recherche / Neutron Star Program Pilot 2 through
completion of the science stage.

1. Preserve each frozen HOLD and remediate it only in a new zero-science
   version.
2. Complete focused and applicable repository validation, a temporary-root
   dry run, and exact implementation/readiness freezes.
3. Obtain one conservative read-only Sol audit of the frozen milestone.
4. If and only if that audit passes, build and verify a separate execution
   freeze binding the implementation, readiness, audit, inventory, threshold,
   predecessors, environment, and data root.
5. Execute the exact frozen 344-case B1937+21 injection run after authorization
   for that stated next stage.
6. Preserve a terminal failure without rerunning, rerolling, retuning,
   replacing, or regrading the same version.
7. If the injection run passes, freeze and audit the terminal result before
   preparing a separately authorized observed-data search package.
8. Audit, freeze, execute, and close out that observed-data science stage under
   the same explicit gates and immutable-failure rules.

## Authorization semantics

`Proceed` authorizes the next stage explicitly laid out in the current plan.
It is not intrinsically limited to design, audit, or non-science activity. The
next stage and its boundaries must be stated before authorization is consumed.

## Current position

v0.2.6 is preserved under HOLD for SOL-V026-001. The authorized stage is an
isolated v0.2.7 remediation that rejects duplicate JSON member names before
trusted dictionary construction, followed by zero-science validation and
implementation/readiness freezes. This stage does not include the final Sol
audit, execution-freeze construction, or science execution.
