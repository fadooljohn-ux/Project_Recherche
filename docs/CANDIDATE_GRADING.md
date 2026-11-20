# Candidate evidence grading

The owner adopted three separate measures on 9 September 2026. Grade each
valid threshold-crossing **search record**, retaining its target, dataset,
original result hash and review evidence. Never average the measures into a
score or infer a planet probability from them.

| Measure | Recorded grades | Meaning |
|---|---|---|
| Statistical significance | REVIEW_PENDING; NOT_ESTABLISHED | Record global false-alarm probability (FAP) and equivalent sigma only when a supported calibration covers the declared search and noise treatment. Blank numeric fields mean unavailable, never zero. |
| Signal robustness | NOT_ASSESSED; NOISE_SENSITIVE; MIXED; ROBUST_WITHIN_REVIEW | Describe survival under the declared noise alternatives, observing-day checks, time/phase and radio-band comparisons. Unavailable checks must remain explicit. |
| Independent confirmation | NOT_ASSESSED; UNAVAILABLE; UNDERPOWERED; NOT_CORROBORATED; CORROBORATED | Distinguish missing independent observations, insufficient sensitivity, lack of support in an informative comparison and actual corroboration. A second reduction of the same observations is not independent. |

These are evidence categories, not equal numerical steps. An independent
non-corroboration does not automatically rule out a companion. Robustness and
corroboration require a written assessment with source evidence; software does
not infer them from an isolated p-value. A confirmed planetary interpretation
requires an adequate orbital explanation and consideration of other timing
processes in addition to statistical significance.

## Significance and diagnostic tails

Keep the original statistic and frozen threshold in Searches. The conditional
1% allowance belongs to the original batch and specified noise model; it is
not a project-wide discovery probability. A global FAP must state its family
of searched periods, targets, datasets and model choices, including how repeated
searches and nuisance/noise uncertainty are handled.

For a calibrated tail p, use one-sided Gaussian-equivalent Z = inverse-normal
survival(p). Five sigma corresponds to p approximately 2.8665e-7. This is not the
probability that no planet exists. A fixed-period two-coefficient sinusoid under
known Gaussian covariance has a two-degree-of-freedom chi-square tail; neither
sqrt(delta chi-square) nor that local tail is a discovery significance after
period selection. See the [PDG statistics review](https://pdg.lbl.gov/2023/reviews/rpp2023-rev-statistics.pdf),
sections 40.3.2 and 40.3.2.2.

The current reviews provide conditional simulation diagnostics. Store the
exceedance count k, simulation count N and (k+1)/(N+1) separately from global
FAP and sigma. Record precisely what observed statistic was compared with the
simulated maxima. In particular J1939's 567-day candidate comparison is distinct
from its separate 67-day residual maximum. The review noise families are limited
and differ by target; these tails are not interchangeable ranking scores.
With 512 simulations the smallest plus-one estimate is 1/513. Additional
simulation work is warranted only by a scientific need, not by the desire to
raise a grade. Grading itself launches no simulations or searches; bounded reviews supply the evidence.

## Current assessment

| Candidate | Statistical significance | Conditional diagnostic tail | Robustness | Independent confirmation |
|---|---|---:|---|---|
| J1453+1902, NG15 | Not established | 47/1025 = 4.6% | Noise-sensitive | Unavailable; alternate reduction shares observations |
| J1939+2134, InPTA, 567 days | Not established | 813/1025 = 79.3% | Noise-sensitive | Not corroborated by overlapping PPTA data |
| J1327-6222, UTMOST | Not established | 1007/1025 = 98.2% | Noise-sensitive | Underpowered TPA comparison, 11.7% conditional detection power |
| J1359-6038, UTMOST | Not established | 241/1025 = 23.5% | Noise-sensitive | Not corroborated; TPA conditional power 91.2% |
| J0908-4913, UTMOST | Not established | 477/1025 = 46.5% | Noise-sensitive | Not corroborated; TPA conditional power 79.4% |
| J1048-5832, UTMOST | Not established | 836/1025 = 81.6% | Noise-sensitive | Underpowered; TPA conditional power 2.8% |
| J1752-2806, UTMOST | Not established | 1/513 = 0.195% for each of four generators | Noise-sensitive | Underpowered; propagated median TPA power 22-31% |
| J1012+5307, NG15 binary pilot | Not established | 513/513 for the 128-mode generator; 1/513 under released 30-mode noise | Noise-sensitive | Not corroborated by the bounded native EPTA fixed-period comparison |
| J2043+1711, NG15 nonlinear, 37.48 days | Not established | 54/1025 = 5.3%, largest of seven generators in the second-stage joint-noise test (0/4096 under released white-only noise) | Noise-sensitive | Unavailable; Arecibo only, narrowband reduction shares observations |

All retain INCONCLUSIVE_NOISE_SENSITIVE and their original historical crossing.
All nine have now been through the [second-stage joint-noise test](JOINT_NOISE_STAGE_2026-11-18.md)
and none crosses its joint threshold. The tails above for the first six and
for J2043 are second-stage values: the largest per-generator count of 1,024
validation nulls at or above the observed joint statistic, not pooled. The
September deep-review tails they replace (47, 41, 512, 481, 496 and 513 of
513) are kept in the predecessor assessments; the
[successor assessment](../results/research/joint-noise-stage-20261118/candidates-assessments.json)
binds both. J1752 and J1012 keep their review tails.
J2043's [review and assessment](HELD_NONLINEAR_SEARCHES_2026-11-17.md#j20431711-candidate-and-review)
were added on 18 November 2026.
J1012's [bounded review](BINARY_PILOT03_2026-09-09.md) and
[assessment](../results/research/j1012-review-20260909/assessments.json) preserve all
five separate noise-generator tails. The largest is recorded without pooling;
it is not a probability of a noise origin or a global FAP.
The [EPTA follow-up](EPTA_J1012_FOLLOWUP_2026-09-10.md) subsequently resolved the
native T2/H3/H4 compatibility gap and found no corroboration at the saved
138.911-day period. Its [successor assessment](../results/research/epta-j1012-followup-20260910/assessments.json)
updates independent confirmation only in that bounded sense, retains the earlier
diagnostic tails, and records shared-noise and period/model-uncertainty limits.
The owner also saved [hypothetical companion estimates](HYPOTHETICAL_COMPANIONS_2026-09-09.md)
as motivation. Those estimates are separate from these evidence grades.
Evidence hashes, individual explanations and source paths are in
[`assessments.json`](../results/research/candidate-grading-20260909/assessments.json).
The four new UTMOST assessments are bound in [batch 04 grades](../results/research/candidate-grading-utmost-batch04-20260909/assessments.json) and explained in the [review report](UTMOST_BATCH04_CANDIDATE_REVIEWS_2026-09-09.md). J1752's zero exceedances are a finite conditional diagnostic, not zero FAP or established global significance.
The two previously invalidated EPTA import crossings are preserved in Searches
and Work log and excluded from this scientific candidate list.

## Second-stage rule

Adopted by the owner on 18 November 2026 ("Proceed with 1 & 2"), after all
ten fixed-noise crossings put through the
[second-stage joint-noise test](JOINT_NOISE_STAGE_2026-11-18.md) fell below
its threshold.

1. A fixed-noise threshold crossing is a trigger. It is recorded in Searches
   as before, and enters Candidate grades as REVIEW_PENDING, but it is not
   described as a candidate signal on that basis alone.
2. Before grading, the crossing goes through the second stage once: noise
   grid and null generators declared in a config file before the run,
   calibration on simulated data, sensitivity curve, freeze, one observed
   run. The grid is not
   changed after the run; a fit on a grid edge is reported, not repaired.
3. Below the joint threshold: record `BELOW_JOINT_NOISE_THRESHOLD`, grade
   INCONCLUSIVE_NOISE_SENSITIVE with the second-stage tail, and stop. A deep
   review is made only if the owner asks.
4. Above the joint threshold: bounded deep review and three-measure grading
   as described above. Crossing both stages is still not a detection.
5. This rule covers the one second-stage run for a crossing produced by an
   owner-authorized search. It authorizes no new search and no rerun.
6. Added 19 November 2026 ("Proceed with steps 1-2"): where a released noise
   chain exists for the target, the config declares a joint white-and-red
   chain generator and a per-receiver white family (scales and floors
   spanning the chain's EQUAD range). Without them the threshold can be too
   low ([evidence](JOINT_NOISE_STAGE_2026-11-18.md#per-receiver-white-noise-the-threshold-holds-under-joint-chain-draws)).
   Runs already consumed are not redone.
7. A non-detection is reported with its
   [detection limits](DETECTION_LIMITS_2026-11-19.md) where a sensitivity
   curve exists.

Known limit, measured on 18 November 2026 (see the
[sensitivity curve](JOINT_NOISE_STAGE_2026-11-18.md#sensitivity-curve)):
where the pulsar has strong red noise, long periods are hard for any test and
the second stage stays within about twice the ideal amplitude. On a quiet
pulsar the second stage itself needs 2–4 times the ideal amplitude beyond
about 450 days. Every frozen second-stage test now carries its own
period-by-period curve.

## Maintaining the register

The canonical workbook now has a Candidate grades table. Each ordinary master
update adds missing valid candidate search IDs as REVIEW_PENDING / NOT_ASSESSED,
preserving existing assessments. It uses the retained SUPERSEDED_INVALID_IMPORT
work-log bindings to exclude invalid import attempts.

After a bounded review, create an evidence manifest following the current
schema, with a new assessment ID for new evidence. Update the current grade row
by stable search ID, while appending an immutable Work log reference to the
manifest. Preserve older manifests and receipts. Grade revisions are recorded
assessments, not edits to the consumed scientific result.

```sh
tools/recherche master-workbook results/research/candidate-grading-20260909 --candidate-grades
```

The updater checks original result and review hashes and verifies simulation
counts and the plus-one tail against the saved diagnostic. Version 1 deliberately
accepts only unavailable global FAP/sigma: publishing a numerical global
significance will require an actual calibration artifact and a localized
extension to this reporting adapter. It cannot silently promote a diagnostic.
The workbook keeps a content-addressed backup before replacement. Repair a
workbook-only failure with this command; never repeat science to refresh grades.

J1752's [focused review](J1752_FOCUSED_REVIEW_2026-09-09.md) and
[dedicated PDF](../output/pdf/J1752-2806_Candidate_Report.pdf) update its current
assessment without changing its disposition. The [new manifest](../results/research/j1752-focused-review-20260909/assessments.json)
preserves the earlier batch-04 manifest as history. The current tail summarizes
the largest per-generator tail; all four have 0/512 and are not pooled. It
pertains to the first finite-family statistic, not the continuous joint fit.
