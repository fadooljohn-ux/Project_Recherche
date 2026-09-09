# Fable pre-execution disposition acceptance v0.1

## Decision

The independent Fable disposition is verified and accepted:

`ONE_SHOT_FREEZE_PREPARATION_MAY_RESUME_WITH_DELETION_CHECKS_ADVISORY`

This acceptance authorizes preparation and validation of a hash-bound one-shot
observed-residual search freeze. It does not authorize observed-residual access
or execution.

The Fable disposition SHA-256 is
`bfbdc9f6b42fbc5af766e68801fd7f7b1c37283b8fef8087b5b76f1d0c371c02`.
The prior seven-file result manifest verified without mismatch. Independent
recalculation reproduced the reported exact binomial tail probabilities and
all 88 repository tests pass.

## Accepted findings

- The clustered-day result remains a formal but borderline pass: 16/1,000,
  Wilson 0.9872%–2.5832%. It requires permanent disclosure, not a post-hoc
  rebaseline or another sample.
- The paired-row and UTC-day cost failures reject those checks as hard vetoes;
  they do not invalidate the locked detection statistic.
- The deletion checks may be executed and reported only as mechanical advisory
  diagnostics. They cannot create, rescue, demote, veto, or trigger further
  analysis of a candidate.
- The one-shot freeze remains subject to a separate final Fable hash-bound
  sign-off and the user's explicit execution authorization.

## Binding implementation choices

The one-shot freeze must satisfy Fable conditions C1–C7 exactly:

1. Set `deletion_checks_as_hard_vetoes: false` and classify both deletion
   checks as advisory.
2. Bind all 433 paired-row and 316 UTC-day deletion units to inventory SHA-256
   `617809921a1598b120514273bbab9ce0374b322601fcdb96c346d75933164eb4`.
3. Carry forward the no-reroll, no-new-recovery-randomness rules and all final
   historical counts.
4. Require every candidate report to quote the clustered-day and deletion-cost
   results and intervals.
5. Omit the optional ordinary-versus-robust refit from v0.1. This avoids adding
   an unvalidated estimator or a second detection branch.
6. Retain threshold 23.33426855482562, the 30–2,000-day grid, one-fifth-bin
   spacing, strongest-unmasked-cell semantics, and no threshold retuning.
7. Keep observed access false during preparation and require both final Fable
   sign-off and explicit user authorization before execution.

## Required advisory deletion fields

For each deletion mode, the candidate report schema must contain:

- minimum trigger statistic and the unit attaining it;
- number of units failing the frozen stability definition;
- maximum frequency error in independent-bin units; and
- a mechanical `DELETION_FRAGILE` or `DELETION_STABLE` label.

The label changes reporting language only. It has no candidate-disposition
authority and cannot trigger an additional analysis branch.

## Next gate

Prepare the one-shot freeze, implementation, tests, output schema, and candidate
disposition contract without reading observed residuals. Then provide the
complete hash-bound packet to Fable for the separate final pre-execution
sign-off. A final Fable pass still requires the user's explicit authorization
before the one-shot search can run.
