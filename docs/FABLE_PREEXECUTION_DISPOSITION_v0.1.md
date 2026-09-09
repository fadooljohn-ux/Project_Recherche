# Fable independent disposition of the failed pre-unblinding validation v0.1

## 1. Reviewer identity and date

**Reviewer:** Claude Fable 5 (read-only independent disposition; no code,
protocol, configuration, result, or manifest file was modified).
**Date:** 2026-08-09.
**Scope:** Disposition of the failed frozen pre-unblinding validation
(`pilot1-preunblinding-validation-v0.1`, FAIL 14/15). This document is not an
observed-search authorization and not the final pre-execution sign-off.

## 2. Manifest verification statement

Every entry in `manifests/preunblinding_validation_result_v0.1.sha256` was
verified with `shasum -a 256 -c`: all 7 files OK. The manifest's own SHA-256
reproduces the packet value
`8d5e7cad0b7e42707f58394c7e3a9026108c6cde621695c4e29db3c3fd9074ca`. The five
execution-identity hashes in the review packet (preparation freeze, execution
freeze, implementation, complete synthetic result, compact result) match the
manifest entries and the values recorded inside the result files. Additional
independent checks, all of which reproduced exactly:

- `execution_binding_sha256` = SHA-256 of `<implementation hash>:<execution
  freeze hash>` = `84269312e0b7…872e8`, matching both result files.
- `config/pilot1_preunblinding_validation_v0.1.yaml` hashes to
  `caefe896…71be`, the value pinned in both freeze documents.
- Project test suite: 88/88 pass.
- All five Wilson 95% intervals (2/1000, 4/1000, 16/1000, 5/125, 6/125)
  recomputed independently; every bound matches the frozen results to full
  reported precision.
- The listed failed case IDs are exactly the cases whose minimum
  post-deletion trigger statistic is ≤ the locked threshold 23.33426855482562
  (5 paired-row, 6 UTC-day), and every one lies in the 0.2 μs amplitude cell,
  as claimed.

## 3. Blinding statement

No observed-residual periodic content was provided, inspected, or calculated.
The packet states none exists; the result files record
`observed_residual_access_executed: false` and
`observed_periodic_search_executed: false`; nothing in this review touched,
derived, or estimated any observed-residual periodic quantity. The answer
required by the packet is: **no**.

## 4. Independent evaluation of the borderline clustered-day result

Observed: 16/1,000 false positives (1.6%), Wilson 95% interval
0.9872%–2.5832%. The frozen rebaseline trip-wire is "Wilson lower bound
strictly greater than 1%"; 0.9872% < 1%, so the trip-wire did not fire. This
is a formal pass by the exact predeclared rule, confirmed independently.

Independent assessment of strength of evidence: under a true 1% false-positive
rate, the exact one-sided binomial probability of observing ≥ 16 in 1,000 is
**4.79%**. That is marginal evidence of inflation — roughly the significance
the trip-wire was designed to interrogate — and the interval remains
consistent with the 1% design target. Two considerations govern the
disposition:

1. **The rule must be honored in both directions.** The trip-wire was frozen
   before execution with full knowledge that borderline outcomes were
   possible (the rule says *strictly* greater). Rebaselining in response to a
   formally passing gate would be exactly the post-hoc rule change this
   project's process discipline exists to prevent, and (under the one-sided
   max rule) could only raise the threshold and burn sensitivity in response
   to no failed criterion.
2. **The result must not be laundered into "1%."** The clustered-day variant
   is the stress scenario closest to the realistic failure mode
   (whole-bad-observing-day contamination), and its point estimate is 1.6×
   the design target. The honest statement is: under clustered-day
   heavy-tail contamination, the false-positive rate of the locked detector
   is consistent with 1% but bounded above only by ≈ 2.58%. That bound must
   travel with any future candidate report.

Conclusion: no rebaseline is required by this result; mandatory reporting
conditions in §8 prevent the borderline character from disappearing.

## 5. Independent evaluation of the failed hard-veto cost gates

Observed: paired-row 5/125 false vetoes (4.0%, Wilson upper 9.02%); UTC-day
6/125 (4.8%, Wilson upper 10.08%). The frozen adoption gate was rate ≤ 1% AND
Wilson upper ≤ 5%. Both fail, and the failure is decisive, not marginal:

- Under a true 1% false-veto rate, P(≥ 5 in 125) = 0.87% and
  P(≥ 6 in 125) = 0.17%. The true false-veto cost of these rules is almost
  certainly well above the 1% design maximum.
- With n = 125, only 0 or 1 false vetoes could have passed the gate
  (1/125 = 0.8%, Wilson upper 4.39%). The observed counts are 5× and 6× the
  passable maximum.
- The failure mode is **structural, not sampling noise**. All 11 failures
  (5 + 6, overlapping sets) are confined to the 0.2 μs injection cell — the
  weakest amplitude, below the detector's ≈ 0.32–0.485 μs 90% crossings. Of
  the 13 eligible 0.2 μs cases, the minimum post-deletion statistics span
  20.7–37.2, with roughly half within a few units of the locked threshold
  23.334. A candidate sitting just above a fixed threshold will be pushed
  below it by removing almost any of the 433 rows or 316 days, because the
  expected Δχ² scales down with deleted data. An
  all-deletions-must-remain-significant rule therefore acts as a hidden
  threshold increase that selectively vetoes exactly the marginal genuine
  signals the search exists to find. No failure involved frequency
  instability: the recovered frequency stayed within one independent Fourier
  bin in every failed case, so the failures are not single-point-artifact
  signatures.

The gate performed its intended function: it measured the true-signal cost of
a proposed veto before adoption and rejected it. The failure indicts the
hard-veto *rule*, not the detection statistic, whose own false-positive gates
passed on all three structured-tail variants.

## 6. Answers to the five packet questions

**Q1 — Does the borderline clustered-day result require rebaseline?**
**No.** The exact frozen trip-wire (Wilson lower strictly > 1%) did not fire:
0.9872% < 1%. The independent exact binomial tail probability against the 1%
target is 4.79% — marginal, not compelling — and rebaselining a formally
passing detector would be a post-hoc rule change with only downside
(threshold can only rise under the max rule). The result is binding in the
other direction, however: this 1,000-case set must never be rerolled or
pooled into a gate (already frozen), and every future candidate report must
carry the clustered-day contaminated false-positive bound (Wilson upper
2.5832%) alongside the nominal 1% (condition C4).

**Q2 — May the deletion checks remain prospectively frozen advisory
diagnostics, or is a new robust detection statistic required?**
**They may remain advisory; a new robust statistic is not required.** The
failed criterion was the *hard-veto adoption gate* — a predeclared
cost-measurement whose frozen failure disposition
(`remain_advisory_and_block_search_pending_independent_review`) is precisely
what occurred. The detection statistic itself passed all three false-positive
gates and the exact 160-case replay with zero mismatches. The deletion
failures are a structural property of any fixed-threshold statistic near
threshold (§5), so replacing the statistic to rescue a redundancy veto would
discard a validated detector for an unvalidated one and restart the entire
calibration chain — an unforced process risk responding to no failure of the
detector. The mandatory consequence is the reverse: because the cost gate
failed, single-paired-row and single-UTC-day dependence are **prohibited from
acting as hard vetoes** in the one-shot freeze (condition C1); the config's
`hard_veto_if_cost_gate_passes` classification is conditioned on a gate that
did not pass.

**Q3 — What exact predeclared reporting and escalation rule prevents
subjective post-candidate disposition?**
The following rule, frozen verbatim (with exact field names and numeric
bounds) in the one-shot freeze before unblinding:

1. For any candidate exceeding the locked threshold, both deletion sweeps are
   executed exactly as validated: all 433 paired-row units and all 316
   UTC-day units, reduced-covariance/design rebuild, full frozen grid, same
   stability definition (statistic strictly above 23.33426855482562 and peak
   frequency within one independent Fourier bin of the undeleted peak).
2. The report must contain, per mode: minimum trigger statistic over all
   units; the unit ID attaining it; the count of units failing stability; the
   maximum frequency error in independent-bin units.
3. Deterministic flag: if any unit in either mode fails stability, the
   candidate is labeled `DELETION_FRAGILE`; otherwise `DELETION_STABLE`. The
   label is computed mechanically from (2) and cannot be overridden.
4. The flag changes required reporting language only. It cannot veto,
   demote, rescue, or create a candidate, and it cannot trigger any
   additional analysis. Candidate status is determined solely by the locked
   threshold rule.
5. Escalation is fixed in advance: the candidate report — including the flag
   and the full per-mode fields — is published in the frozen report schema
   regardless of outcome, and goes to independent review with this
   validation's false-veto rates (4.0%, 4.8%, concentrated at 0.2 μs) quoted
   as the known probability that a genuine marginal signal is flagged
   fragile. No post-candidate deletion analysis beyond the frozen 749 units
   is permitted.

This removes all discretion: the sweep inventory, the fields, the flag rule,
and the publication obligation are each mechanically checkable, and no
threshold crossing anywhere in the rule is dispositive.

**Q4 — Is an ordinary-versus-robust candidate refit acceptable as a
predeclared advisory comparison, and what fields must be reported?**
**Yes, acceptable, under three restrictions that prevent a second detection
branch.** (a) The robust refit is evaluated **only at the candidate
frequency already selected** by the locked ordinary statistic — never as a
scan over any grid, so it can find nothing on its own. (b) The robust
estimator (loss function and all tuning constants) is frozen by hash before
unblinding. (c) The output is advisory: no numeric outcome of the comparison
may create, rescue, veto, or re-rank a candidate. Required reported fields,
with agreement bands frozen in advance and reported as within/outside band:

- amplitude difference, microseconds (ordinary minus robust);
- phase difference, radians;
- peak-frequency difference at refit, in independent-bin units;
- Δχ² (or equivalent significance) difference at the candidate frequency;
- robust-refit convergence status (non-convergence of the *ordinary* refit
  remains the existing hard abort; robust non-convergence is reported,
  advisory).

**Q5 — Disposition:** see §7.

## 7. Disposition

**`ONE_SHOT_FREEZE_PREPARATION_MAY_RESUME_WITH_DELETION_CHECKS_ADVISORY`**

Statistical basis: the detection statistic passed every false-positive gate
on 3,000 structured-tail nulls (two comfortably; one formally, with the
borderline character handled by binding reporting conditions rather than by a
post-hoc rebaseline that no frozen rule demands). The exact 160-case replay
reproduced with zero mismatches. The only failed criterion measured the
true-signal cost of a *proposed candidate-disposition rule*, found it
decisively too high (5× and 6× the passable count, structurally concentrated
in marginal signals, with zero frequency-instability failures), and carries a
frozen failure disposition — remain advisory, block pending independent
review — that this document now discharges.

Process-integrity basis: rebaselining would override a formally passing
frozen rule after seeing the outcome; a new robust-statistic program would
discard a fully validated detector in response to a failure that indicts only
an optional veto rule. Either alternative introduces the discretion this
project's freeze discipline exists to eliminate. Resuming freeze preparation
with the deletion checks demoted to advisory follows the predeclared failure
path exactly, changes no threshold, rerolls nothing, and leaves the observed
search locked behind the separate final sign-off.

## 8. Mandatory conditions

All conditions are objective and testable against the one-shot freeze
document before final sign-off. Failure of any condition blocks that
sign-off.

- **C1 (advisory demotion).** The one-shot freeze must classify
  `single_paired_row_dependence` and `single_utc_day_dependence` as advisory
  diagnostics and must contain `deletion_checks_as_hard_vetoes: false`. No
  candidate-disposition rule in the freeze may make any deletion outcome
  dispositive. *Test:* grep of the freeze for the classification fields; no
  hard-veto or abort clause references deletion outcomes.
- **C2 (frozen deletion reporting rule).** The freeze must contain, verbatim
  and hash-bound, the sweep inventory (433 paired-row + 316 UTC-day units,
  unit inventory SHA-256
  `617809921a1598b120514273bbab9ce0374b322601fcdb96c346d75933164eb4`), the
  per-mode report fields, the mechanical `DELETION_FRAGILE`/`DELETION_STABLE`
  flag rule, and the unconditional-publication clause of §6 Q3. *Test:*
  field-by-field presence check; flag rule contains no discretionary clause.
- **C3 (no rerolls, no new randomness).** The freeze must carry forward
  `further_tail_reroll_authorized: false` and
  `new_recovery_randomness_authorized: false`, and must state that the
  16/1,000 clustered-day set, the 5/125 and 6/125 veto-cost results, and the
  7/500 and 7/1,000 tail history are final and may not be rerolled, pooled
  into any gate, or re-measured on new draws. *Test:* presence of both flags
  set false; presence of the enumerated frozen counts.
- **C4 (borderline result travels with any candidate).** The freeze's
  candidate report schema must include mandatory fields quoting the
  clustered-day contaminated false-positive result (16/1,000; Wilson
  0.9872%–2.5832%) and the deletion false-veto rates (5/125 and 6/125 with
  Wilson uppers 9.02% and 10.08%, all failures at 0.2 μs), so any candidate
  is interpreted against the stress-scenario bound of ≈ 2.6%, not only the
  nominal 1%. *Test:* fields present in the frozen report schema with these
  exact numbers.
- **C5 (robust refit containment).** If the ordinary-versus-robust
  comparison is included, the freeze must restrict it to the selected
  candidate frequency only, hash-pin the robust estimator and its constants,
  freeze the agreement bands, and state that no field of the comparison is
  dispositive. Otherwise it must be omitted entirely. *Test:* no robust scan
  over any frequency set appears in the frozen execution plan.
- **C6 (unchanged locked detector).** The freeze must retain the locked
  threshold 23.33426855482562, the 30–2,000-day grid at one-fifth
  independent-bin spacing, the frozen annual-mask semantics
  (strongest-unmasked-cell candidate; masked cells are sensitivity gaps
  only), and `threshold_retuning_authorized: false`. *Test:* exact value and
  field match against `config/pilot1_preunblinding_validation_v0.1.yaml`.
- **C7 (authority boundary preserved).** The freeze must state that this
  disposition authorizes preparation only, and that observed-residual access
  requires (a) Fable's separate final hash-bound pre-execution sign-off on
  the completed one-shot freeze and candidate-disposition contract, by a
  reviewer who has inspected no observed periodic content, and (b) the
  user's explicit authorization. *Test:*
  `observed_residual_access_authorized: false` and
  `observed_periodic_search_authorized: false` present in the freeze at
  preparation time; sign-off clause names both requirements.

— Claude Fable 5, 2026-08-09
