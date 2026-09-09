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
| J1453+1902, NG15 | Not established | 47/513 = 9.2% | Noise-sensitive | Unavailable; alternate reduction shares observations |
| J1939+2134, InPTA, 567 days | Not established | 41/513 = 8.0% | Noise-sensitive | Not corroborated by overlapping PPTA data |
| J1327-6222, UTMOST | Not established | 512/513 = 99.8% | Noise-sensitive | Underpowered TPA comparison, 11.7% conditional detection power |
| J1359-6038, UTMOST | Not established | 481/513 = 93.8% | Noise-sensitive | Not corroborated; TPA conditional power 91.2% |
| J0908-4913, UTMOST | Not established | 496/513 = 96.7% | Noise-sensitive | Not corroborated; TPA conditional power 79.4% |
| J1048-5832, UTMOST | Not established | 513/513 = 100% | Noise-sensitive | Underpowered; TPA conditional power 2.8% |
| J1752-2806, UTMOST | Not established | 1/513 = 0.195% for each of four generators | Noise-sensitive | Underpowered; propagated median TPA power 22-31% |

All retain INCONCLUSIVE_NOISE_SENSITIVE and their original historical crossing.
The owner also saved [hypothetical companion estimates](HYPOTHETICAL_COMPANIONS_2026-09-09.md)
as motivation. Those estimates are separate from these evidence grades.
Evidence hashes, individual explanations and source paths are in
[`assessments.json`](../results/research/candidate-grading-20260909/assessments.json).
The four new UTMOST assessments are bound in [batch 04 grades](../results/research/candidate-grading-utmost-batch04-20260909/assessments.json) and explained in the [review report](UTMOST_BATCH04_CANDIDATE_REVIEWS_2026-09-09.md). J1752's zero exceedances are a finite conditional diagnostic, not zero FAP or established global significance.
The two previously invalidated EPTA import crossings are preserved in Searches
and Work log and excluded from this scientific candidate list.

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
