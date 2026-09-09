# Pilot 2 v0.2.9 qualification-harness formal attempt 1 closeout

- **Status:** terminal `FAIL`; preserved without repair or rerun
- **Gate:** Gate 1B
- **Candidate commit:** `8055f3c11be41cf539a46c1838323c9ca893ef3d`
- **Candidate tree:** `f2b703648b335c51c8b6ae11721d09ed41dbb9c9`
- **Formal command exit:** `2`
- **Formal failure:** `FAIL_ZERO_SCIENCE_BOUNDARY`
- **Evidence record:** `results/pilot2/qualification_harness_v029_formal_attempt_1_failure.json`

## Result

Disposable Gate 1B acceptance passed `86/86` before the candidate was
committed. The candidate was then clean, preserved every baseline tracked byte,
and passed the exact-six candidate verifier. The corrected governed command was
invoked once.

That formal attempt returned `FAIL`. Its aggregate recorded one audited network
event in the complete current lane. All operational-context, operational-case,
science-entry, controlled/observed-artifact, observed-residual, external-root,
and resource-acquisition counters remained zero. The macOS sandbox continued to
deny network access; the nonzero audited event is nevertheless disqualifying
under the approved zero-counter contract.

The complete current pytest lane also terminated with `417 passed, 15 failed`.
Five failures were the recorded historical witnesses. Ten were additional
current failures: the child environment set `TMPDIR` to a writable directory
that was not an ancestor of pytest `basetemp`, so an existing temporary-root
test and several v0.2.9 snapshot/nested-qualification acceptance cases rejected
their otherwise disposable paths. Because the boundary failed before current
classification, no historical lane ran and final accounting was not produced.

## Preservation

The raw evidence remains unmodified in the system-temporary evidence directory
recorded in the JSON closeout. The record binds all eight evidence files by
byte count and SHA-256, including:

- aggregate SHA-256
  `54cc8a908dea73e0981e801fffb32d0d33f62c6c074504a8a7195bf39e89fa74`;
- canonical semantic SHA-256
  `ae907598666f7eb089e70381b5170d371bc053717eb76d01de12b161ac5ae25d`;
- complete evidence-inventory SHA-256
  `483fd8eaa61fb5322c7cf356c83015b492e918a412ea568a8272587c791627ab`.

Repository start and end identity were identical and clean. No real data root,
manifest, freeze, audit, observed residual, operational qualification case, or
science execution was reached.

## Stop rule

Formal attempt 1 is terminal evidence. It may not be repaired, resumed,
regraded, or rerun under the same identity. Gate 1B did not pass, so Gate 2 and
all later operational or science work remain locked. Any remediation requires a
new prospective design/authority decision and a new formal attempt identity.
