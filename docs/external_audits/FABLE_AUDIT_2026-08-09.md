# Independent audit and responses to 5.6 Sol — 2026-08-09

**Auditor:** Claude Fable 5 (read-only engagement; no code, configuration,
protocol, or result file was modified).

**Blinding statement:** No observed-residual periodic-search result was
inspected, and none exists to inspect: the release record confirms
`observed_residual_periodic_search_authorized: false`, and every executed
artifact examined was either synthetic or a non-periodic time-domain
diagnostic. No recommendation below is informed by observed periodic content.

**Scope note:** The working repository (Project Spectre, TESS
massive-companion pilot) contains the pulsar-timing *scope* document, but the
executed pulsar-timing work that all seven of Sol's questions reference lives
in the sibling repository **Project Recherche**. Both were audited; Sol's
questions are answered against Project Recherche.

---

## Part 1 — Project and tool audit

### 1.1 What was independently verified (Project Recherche)

| Check | Method | Result |
|---|---|---|
| Test suite | `pixi run test` | 78/78 pass (2.2 s) |
| Release record, in-repo hashes | `python -m pulsar_pilot.release` | PASS, 22/22 promotion, zero failures |
| External run records (5 controlled records under the data root) | `release --check-external` | PASS, zero hash/size failures |
| Wilson 95% upper bound, 7/1000 | independent recomputation | 1.4378% — matches |
| Wilson 95% upper bound, 7/500 | independent recomputation | 2.8613% — matches |
| Wilson 95% upper bound, 14/1500 | independent recomputation | 1.5606% — matches |
| Contamination-mixture excess kurtosis (p = 1%, multiplier 2.82374…) | independent recomputation | 1.262140834554 — matches theoretical claim to ~1e-13 |
| Threshold lock 23.33426855482562 | rank check | conservative nearest-rank 99th percentile at rank 990 of 1,000, as claimed |
| R1 result JSON vs. R1 result document | field-by-field comparison | consistent (7/1000, threshold unchanged, 160 regrades, 5/5 monotonic and bracketed, 0 audit failures) |
| Original sealed Gaussian evaluation | JSON inspection | 2/500 FP (0.4%), Wilson upper 1.447% — passed its gates |

### 1.2 Source-code accuracy of the tool (statistical kernels)

Read directly and checked against their mathematical definitions:

- `wilson_interval_95` (`pilot1_evaluation.py:111`) — correct Wilson score
  interval, z = 1.959963984540054, correctly clipped to [0, 1].
- `conservative_nearest_rank` (`pilot1_runtime.py:236`) — correct
  `ceil(q·n)` nearest-rank estimator; rejects non-finite and empty input.
- `theoretical_mixture_excess_kurtosis` and `generate_contaminated_null`
  (`tail_robustness.py`) — the 1%-probability scale mixture is analytically
  normalized to unit variance *before* multiplication by the released
  covariance Cholesky factor, so contamination changes tail shape without
  inflating total variance. Correct.
- Seed derivation is SHA-256 per case ID with explicit disjointness assertions
  between calibration and evaluation families (`build_null_orders` raises on
  any case-ID or seed overlap). The R1 freeze additionally pins inventory
  hashes, prior-result hashes, code hashes, and the environment lockfile.

**No numerical, statistical, or provenance discrepancy was found anywhere I
checked. Every quantitative claim Sol quoted reproduces exactly** (her
"Δχ² = 23.334" is the locked 23.33426855482562, rounded).

### 1.3 Process-integrity findings (hidden researcher degrees of freedom)

The project's discipline is unusually good: pre-run freezes with hashes,
preserved failures (the 20/22 tail failure and the earlier C1 grader failure
are retained un-regraded), a one-sided threshold ratchet (max rule), disjoint
seeds, and hard prohibitions on observed-residual access. Four residual
degrees of freedom deserve explicit acknowledgment:

1. **Sequential re-evaluation (the R1 re-roll).** The corrective evaluation
   exists *because* the first one failed. Under a truly borderline 1% detector,
   each fresh 1,000-null evaluation passes the rate gate with probability
   ≈ 58%, so "keep re-rolling until pass" would be a real loophole. It is
   mitigated here (see Q1) but must not be repeated: a future tail failure
   must trigger rebaseline, not a third evaluation set.
2. **Post-failure reclassification of the Behrens reference gate.** A hard
   promotion gate (100-day sensitivity within 1/3–3× of the published 0.56
   lunar-mass limit) was converted to a contextual disposition after it
   failed. The discrepancy dossier's justification is substantively sound —
   the published experiment (white-noise residuals, post-fit LS injection, a
   global 2.5× fudge factor, EFAC=1/EQUAD=0) is demonstrably not
   method-matched to TOA-level full-covariance injections — and the original
   failure was preserved. But it is structurally a post-hoc gate change and
   should be labeled as such in any external write-up.
3. **The R1 quantile change (99th → 99.5th percentile).** Prospective, frozen
   before execution, conservative in direction, and ultimately moot (the max
   rule retained the old threshold). Low risk, but it is discretion exercised
   between a failure and a retest.
4. **Single-day, single-operator cadence.** Every freeze, amendment, run, and
   review in Pilot 0 and Pilot 1 is dated 2026-08-09. Each step is
   individually documented, but same-session freeze→run→amend cycles
   concentrate discretion; the "reviewed" in "separately reviewed one-shot
   freeze" should mean review by a party who was not the operator (Sol's
   scorecard request is exactly the right instinct).

### 1.4 Project Spectre repository state (brief)

- 38/38 tests pass. The uncommitted work is v0.6 scaffolding: additive CLI
  wiring for three new subcommands, `diagnostics_v06.py`, `v06_inventory.py`,
  new configs/manifests/protocols, and `test_v06_freeze.py`, consistent with
  the frozen v0.6 research brief (metadata-only, sealed cohort untouched).
- The TESS pilot correctly remains on hold at grade B with sealed controls and
  blind candidates unopened. Nothing in the Spectre tree bears on Sol's
  questions; its uncommitted branch should be committed or the freeze-hash
  tests may drift from the working tree.

---

## Part 2 — Scorecard for 5.6 Sol's questions

| # | Question | Verdict |
|---|---|---|
| 1 | Does the seed-disjoint R1 pass resolve the 7/500 failure? | **Pass with required changes** |
| 2 | May the two evaluations be pooled (14/1,500)? | **Pass as currently handled — keep contextual only** |
| 3 | Is the contamination model realistic enough? | **Pass with required changes** |
| 4 | Do the localized diagnostics indicate outlier vs. misspecification? | **Pass with required changes** |
| 5 | Is retaining Δχ² = 23.3343 defensible (LEE, annual mask)? | **Pass** |
| 6 | Robustness checks: hard veto vs. advisory? | **Pass with required changes** |
| 7 | Proceed to one-shot freeze, validate first, or rebaseline? | **Proceed to freeze preparation, with the required changes folded in** |

No question receives a Fail. All "required changes" are protocol/freeze
content, not detector or threshold changes.

---

## Part 3 — Detailed answers

### Q1 — Does the R1 pass adequately resolve the 7/500 failure?

**Pass with required changes.** Substantively, yes:

- The original failure is statistically unremarkable for a compliant detector:
  under a true 1% rate, P(≥ 7 FP in 500) ≈ 23.7%. The gate did its job by
  refusing to average that away.
- The R1 pass is genuinely informative, not a lucky re-roll: if the true rate
  were the originally observed 1.4%, P(≤ 7 FP in 1,000) ≈ 3.1%. The data now
  favor a rate near the 1% design target rather than above it.
- The design-after-failure discretion was contained about as well as it can
  be: criteria unchanged (≤ 1% rate, ≤ 2.5% Wilson upper), seeds and case IDs
  provably disjoint from both original null sets, the failed set banned from
  grading, the threshold *not* retuned (max rule retained 23.3343, so the
  passing evaluation used the identical detector as the failing one), the 160
  recovery artifacts regraded from immutable hash-bound scan statistics, and
  the original failure preserved as authoritative.

Required changes:

1. The one-shot search freeze must state that **no further tail evaluations
   may be re-rolled**; any future tail-gate failure goes directly to
   rebaseline or robust-statistic replacement (the R1 protocol already says
   this — carry it forward verbatim).
2. Any downstream document quoting "0.7%" must also quote the failed 7/500
   and the evaluation count (two attempts), so the sequential structure is
   never invisible.
3. Treat the true contaminated FP rate as "consistent with ≤ 1%, bounded
   above by ≈ 1.6%" (the pooled Wilson upper), not as "0.7%."

### Q2 — May the two evaluations be pooled as 14/1,500?

**Keep it contextual only — the current handling is exactly right.** The two
sets are disjoint and were scored at the identical threshold, so the pooled
count is a legitimate descriptive summary, and it is reassuring that the
pooled numbers (0.933% rate, 1.561% Wilson upper) would pass both frozen
limits anyway. But the second sample exists *conditionally on the first
failing*: under that adaptive stopping rule, a naive pooled Wilson interval
does not have exact nominal coverage, and promoting the pooled estimate to a
gate would retroactively let the larger sample dilute a recorded failure —
precisely the regrading the protocol forbids. Use 14/1,500 as the honest
point estimate in prose; never as a gate input.

### Q3 — Is the contamination model realistic enough?

**Pass with required changes.** The current model (i.i.d. 1%-probability
single-multiplier Gaussian scale mixture, unit variance, kurtosis matched to
the observed 1.26214 advisory, released covariance preserved) is a
well-chosen *first* stress model and was honestly labeled as a stress model
rather than a generative claim. Its known gap is structure: the observed
advisory is block-asymmetric — timing-block absolute excess kurtosis 2.05
versus DM-block 0.687 — and an i.i.d. innovation mixture reproduces neither
that asymmetry nor any temporal or instrumental clustering.

Required additions, in priority order, all as *advisory* stress variants
frozen before the one-shot search (they should not retroactively become hard
gates for an already-passed detector):

1. **Block-separated contamination** — timing-only and DM-only variants
   matched to the observed per-block kurtosis. Highest priority because the
   observed data demand it.
2. **Clustered bad epochs** — contaminate whole UTC observing days rather
   than independent TOAs, at matched total contamination energy. Clustered
   outliers are the realistic failure mode for a periodic-search FP rate.
3. **Backend-specific contamination** — one backend group contaminated;
   directly exercises the leave-one-group machinery that already exists.
4. **Student-t innovations** (e.g., ν chosen to match kurtosis ≈ 1.26) —
   optional; useful because it puts mass in the extreme tail that a bounded
   two-point mixture cannot, but lowest incremental value of the four.

If any variant pushes the FP rate at the locked threshold materially above
1%, that is a rebaseline trigger — decide and freeze the numeric trip-wire
(suggest: variant FP rate > 1% with Wilson lower bound > 1%) *before* running
the variants.

### Q4 — Outlier problem or model misspecification?

**Pass with required changes — the evidence says mild distributed
misspecification, not a removable outlier, and it does not block unblinding
by itself.** The localization is unambiguous on this: removing the single
most influential projected coordinate reduces combined kurtosis by only
36.7%, the top five coordinates carry just 8.70% of projected squared energy,
and every other moment/correlation diagnostic (energy, variance, skewness,
MAD, max residual, lag correlation) sits inside its frozen 99% interval. A
single corrupt TOA would concentrate; this does not. The correct reading is
that the released noise model is slightly light-tailed for these residuals —
which is exactly the hypothesis the contamination stress program tested, with
the result that the FP rate at the locked threshold stays at ~0.7–0.9%.

Required changes: retain the advisory as a standing limitation in the
one-shot freeze; run the Q3 block-separated variant (because the timing-block
kurtosis of 2.05 is the part least well bounded by the current
kurtosis-1.26-matched mixture); and include candidate-level influence vetoes
(Q6) so that any future observed trigger is automatically tested against
exactly this failure mode. No pre-unblinding TOA surgery: editing or
down-weighting individual TOAs now, guided by influence diagnostics computed
on the observed residuals, would be a far worse researcher degree of freedom
than the misspecification it would purport to fix.

### Q5 — Is retaining Δχ² = 23.3343 statistically defensible?

**Pass.** Point by point:

- **Look-elsewhere effect:** fully internalized by construction. The
  statistic is the *global maximum* Δχ² over the entire frozen 30–2,000-day
  grid (1/5-Fourier-bin spacing), and the threshold is the empirical 99th
  percentile of that maximum over 1,000 Gaussian nulls. No separate LEE
  correction is needed or appropriate; the 1% is already a per-search global
  rate. The claim is valid only for this grid, this target, this noise model,
  and a *single* one-shot search — any second look (another grid, another
  pulsar, a re-run) voids it and must be said so in the freeze.
- **Annual mask:** the calibration maximizes over the full grid including the
  masked 350/365.25/380-day cells, while those cells cannot produce an
  eligible candidate. Whether the observed search maxes over the full grid
  and then applies eligibility, or maxes over unmasked cells only, the
  realized eligible-candidate FP rate is ≤ the calibrated 1%. The threshold
  is therefore conservative with respect to the mask. **Requirement folded
  into Q6/Q7:** the freeze must state explicitly which of those two mask
  semantics the one-shot search uses, before unsealing.
- **Robustness of the number itself:** the retained value survived an
  independent re-derivation — the R1 99.5th percentile from 2,000 *heavier-
  tailed* contaminated nulls came out at 23.2674, within 0.3% of the Gaussian
  99th percentile from 1,000 nulls — and the max rule can only ever raise it.
  Monte-Carlo uncertainty on a rank-990 estimator is real but bounded, and
  the sealed Gaussian evaluation (2/500) plus both contaminated evaluations
  confirm the realized rate at this threshold from disjoint samples.

### Q6 — Which robustness checks are hard vetoes vs. advisory?

**Pass with required changes.** The check families in the corpus are sound;
what is missing is a frozen, quantitative classification. Recommended split,
with the classification and every numeric bound frozen before unsealing:

**Hard vetoes** (signal-independent integrity, or physically impossible for a
genuine years-long periodic companion signal):

1. Freeze/hash verification failure of any input, code, config, environment,
   or run-record artifact — abort, not just veto.
2. Non-convergence of the ordinary or joint refit, or low-rank vs.
   explicit-full-covariance solver disagreement beyond the already-frozen
   tolerances (0.01 μs, 0.001 rad, 0.1 Δχ²).
3. Any unexpected material warning (existing warning-hygiene classifier).
4. Candidate frequency inside the annual mask or outside the frozen grid.
5. **Single-point/single-day dependence:** removing one TOA or one UTC
   observing day drops the candidate below the locked threshold. A genuine
   circular companion signal integrated over 433 epochs across 15.7 years
   cannot live in one epoch; this veto is near-zero-cost for true signals and
   directly targets the heavy-tail failure mode. Before adoption, verify the
   cost empirically by applying the same veto to the existing 160 immutable
   contaminated recovery artifacts (a threshold-independent regrade of stored
   statistics is already an approved pattern) and freeze the measured
   true-signal veto rate alongside the rule.

**Advisory diagnostics** (reported, never dispositive, because each one could
veto a real signal or requires judgment):

6. Backend/frontend/observing-system concentration of the candidate's
   projected energy (leave-one-group influence).
7. Post-candidate residual kurtosis and the standing 1.26214 advisory.
8. Amplitude/phase stability between data halves (sensitivity-costly).
9. The pooled 14/1,500 tail context and the Behrens contextual ratio.

The governing principle: a hard veto must be justifiable *without reference
to any observed result* and must have a measured, frozen false-veto cost on
injections. Anything requiring interpretation stays advisory, and the freeze
must state that advisory results cannot rescue or create a candidate.

### Q7 — One-shot freeze, more validation first, or rebaseline?

**Proceed to prepare the one-shot search freeze — with the Q3 stress variants
and Q6 veto classification built into that preparation — and do not
rebaseline.**

- **Against rebaselining:** the detector just passed a disjoint,
  heavier-than-Gaussian evaluation at the retained threshold with every
  recovery, monotonicity, bracketing, and audit gate intact. Rebaselining now
  in response to no failed gate would itself be an unforced researcher degree
  of freedom, and the max rule means a rebaseline could only raise the
  threshold and burn sensitivity that the 90% crossings (0.32–0.485 μs)
  currently deliver.
- **Against a separate blocking validation stage:** the outstanding items
  (block-separated/clustered contamination, veto cost measurement, mask
  semantics) are all specifiable now and are naturally part of the freeze
  document itself. A free-standing validation stage would add another
  freeze→run→amend cycle of exactly the kind flagged in §1.3(4), without a
  defined failure that motivates it.
- **Conditions on proceeding:** the freeze is *preparation only* (that is all
  the R1 pass authorizes); it must include the Q3 advisory variants with a
  pre-frozen rebaseline trip-wire, the Q6 hard/advisory classification with
  measured veto costs, the explicit mask-interaction semantics from Q5, the
  no-re-roll rule from Q1, and — given §1.3(4) — sign-off by a reviewer who
  did not operate the pipeline (Sol) before execution. If any of the new
  advisory stress variants trips its frozen trip-wire during freeze
  preparation, the answer converts to rebaseline at that point, under rules
  written before the outcome was known.

---

## Part 4 — Consolidated required changes (all protocol-level; none touch code or threshold)

1. Carry the no-further-re-roll rule into the one-shot freeze (Q1).
2. Always report 7/500 alongside 7/1,000; pooled 14/1,500 stays contextual (Q1, Q2).
3. Add block-separated (timing/DM) and clustered-epoch contamination variants
   as frozen advisory stress tests with a pre-frozen rebaseline trip-wire;
   backend-specific and Student-t variants optional (Q3, Q4).
4. Freeze the hard-veto vs. advisory classification with numeric bounds, and
   measure hard-veto false-veto cost on the 160 immutable recovery artifacts
   before unsealing (Q6).
5. Specify the annual-mask/global-max interaction semantics in the freeze (Q5).
6. Require independent (non-operator) review sign-off on the one-shot freeze
   before execution (§1.3(4), Q7).
7. Housekeeping: commit the Project Spectre v0.6 working-tree changes so the
   freeze-hash tests cannot drift from the tree.

## Bottom line

The tool is accurate: every statistic, threshold, interval, and hash I
checked reproduces independently, the full provenance chain verifies from the
repository through the external run records, and both test suites pass. The
process is unusually honest — failures are preserved, thresholds ratchet only
upward, and blinding has been maintained. The R1 pass is a legitimate
resolution of the 7/500 failure, the main residual risks are the two
sequential-decision points documented in §1.3, and the defensible next step
is preparation (not execution) of the one-shot observed-residual search
freeze with the six protocol additions above.
