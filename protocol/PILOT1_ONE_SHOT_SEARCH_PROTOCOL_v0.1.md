# Pilot 1 one-shot observed-residual search protocol v0.1

## Authority

This document prepares one and only one observed-residual circular-signal
search for PSR J1744-1134. Preparation, code review, synthetic testing, hash
freezing, and final independent review do not authorize observed residual
access. Execution requires both a passing hash-bound Fable sign-off and a
separate explicit user-authorization record matching the same package.

## One-shot boundary

Before any observed residual is calculated, the runner must verify every
frozen repository and external-input hash, verify both authorization records,
and confirm that no prior one-shot intent or result record exists. It then
writes an immutable execution-intent sentinel before calculating the residual
vector. A prior sentinel blocks automatic retry even if the earlier run did
not complete; recovery requires independent disposition, not a rerun.

Exactly one full 30–2,000-day grid is scanned at one-fifth-independent-bin
spacing. Threshold 23.33426855482562 and the strict-greater-than comparison are
unchanged. No alternate grid, threshold, pulsar, model, or second look is
permitted.

## Annual mask and candidate selection

The full grid is evaluated once. The grid cells nearest 350, 365.25, and 380
days are masked using the frozen tie rule. The strongest unmasked cell is the
candidate statistic and is compared with the locked threshold. A masked cell
is reported as an annual sensitivity gap and cannot suppress a distinct
unmasked candidate. The full-grid maximum may be reported as a diagnostic but
has no candidate authority if masked.

## Candidate grading

If the strongest unmasked cell exceeds threshold, run the already validated
ordinary and joint timing refits at that selected frequency, plus the explicit
full-covariance audit. Integrity, convergence, warning hygiene, and solver
agreement remain hard aborts. The frozen four-hour wall-time, 16 GiB peak-memory,
and 5 GiB complete-data-root ceilings are also hard integrity gates in the
published result. No robust estimator or alternate-frequency candidate branch
is included in v0.1.

## Advisory deletion diagnostics

For a threshold candidate, execute the exact 433 paired-row and 316 UTC-day
deletion units bound by inventory SHA-256
`617809921a1598b120514273bbab9ce0374b322601fcdb96c346d75933164eb4`.
Each unit rebuilds the reduced covariance, timing projection, and full frozen
grid. Stability requires a statistic strictly above the locked threshold and a
peak within one independent Fourier bin of the undeleted candidate frequency.

For each mode report the minimum statistic and its unit ID, number of failed
units, maximum frequency error in independent-bin units, and the mechanical
label `DELETION_FRAGILE` or `DELETION_STABLE`. The label changes reporting
language only. It cannot create, rescue, demote, veto, or trigger further
analysis of a candidate.

## Mandatory context

Every outcome report, including a null result, must carry the complete frozen
tail history: original 7/500 failure, disjoint R1 7/1,000 pass, clustered-day
16/1,000 with Wilson interval 0.9872%–2.5832%, paired-row deletion false-veto
5/125 with 9.02% Wilson upper bound, and UTC-day 6/125 with 10.08% upper bound.
The pooled 14/1,500 count remains contextual only. No set may be rerolled,
pooled into a gate, or re-measured on new recovery draws.

## Publication and stop rule

The runner writes the frozen candidate-report schema regardless of whether a
candidate triggers. Once an execution-intent sentinel exists, no second run is
authorized. After publication, scientific interpretation requires independent
review; this runner makes no discovery claim and cannot expand to another
target.
