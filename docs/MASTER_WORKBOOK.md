# Project Recherche master workbook

Latest development (2026-11-18 UTC): [second-stage sensitivity curve](JOINT_NOISE_STAGE_2026-11-18.md#sensitivity-curve)
adds one Work log row. No Searches or Candidate grades row changes; totals
remain 783 / 286 / 360.

Latest grade update (2026-11-18 UTC): on the owner's instruction the
[second stage is the standing rule](CANDIDATE_GRADING.md#second-stage-rule)
and the Candidate grades rows of J1453, J1939, J1327, J1359, J0908 and J1048
now carry their second-stage tails (46, 812, 1,006, 240, 476 and 835 of 1,024)
in place of the September deep-review tails. Grades and dispositions are
unchanged. Two Work log rows added; no Searches row changes; totals remain
783 / 286 / 360. These rows were changed by a checked script, as for J2043,
because `--review` does not edit existing grade rows.

Latest second-stage runs (2026-11-18 UTC): [the six other September candidates](JOINT_NOISE_STAGE_2026-11-18.md#the-six-other-september-candidates)
add seven Work log rows (implementation; J1453, J1939, J1327, J1359, J0908
and J1048, all below the joint threshold). Candidate grades rows and Searches
rows are unchanged; totals remain 783 / 286 / 360.

Latest second-stage test (2026-11-18 UTC): [J2043+1711 joint-noise stage 3](JOINT_NOISE_STAGE_2026-11-18.md#stage-3-nonlinear-orbit-and-j20431711)
adds two Work log rows and completes the diagnostic fields of J2043's Candidate
grades row (53 of 1,024; grades unchanged). No Searches row changes; totals
remain 783 / 286 / 360.

Latest development (2026-11-18 UTC): [second-stage joint-noise test](JOINT_NOISE_STAGE_2026-11-18.md)
adds four Work log rows (implementation; J1752, J1012 and J1738 development
runs, all below the joint threshold). Exposed-data development only: no
Searches, Targets or grades change; totals remain 783 / 286 / 360.

Latest observed searches (2026-11-18 UTC): [J0740, J2043 and J0613 nonlinear searches](HELD_NONLINEAR_SEARCHES_2026-11-17.md)
add thirteen Work log rows (verification, preparation, calibration and observed
search per target; J2043 review) and one Candidate grades row (J2043+1711,
INCONCLUSIVE_NOISE_SENSITIVE; exceedance fields blank because no tail was
computed with red noise admitted). Targets rows for J1857, J0740, J2043 and
J0613 now state the nonlinear search outcome in their next-step and dataset
columns. The nonlinear tool is outside the batch layout, so the Searches sheet
and the status column are unchanged; totals remain 783 / 286 / 360.

Latest observed search (2026-11-17): [J1857 nonlinear search](J1857_NONLINEAR_CALIBRATION_2026-11-17.md#observed-search)
adds one Work log row (NO_TRIGGER). The nonlinear tool is outside the batch
layout, so the Searches sheet is unchanged; totals remain 783 / 286 / 360.

Latest calibration (2026-11-17): [J1857 nonlinear calibration](J1857_NONLINEAR_CALIBRATION_2026-11-17.md)
adds two Work log rows (preparation; calibration and freeze). No observed search
ran; no Searches or grades change; totals remain 783 / 286 / 360.

Latest development (2026-11-17): [reusable nonlinear statistic](NONLINEAR_STATISTIC_2026-11-17.md)
adds two Work log rows (implementation; synthetic verification, no holds). No
Searches or grades change; totals remain 783 / 286 / 360.

Latest closeout (2026-11-17): two Work log rows, `QUALIFICATION-03` (PASS,
21/21 gates) and `THRESHOLD-STUDY-20261116` (NOT_ADOPTED). No Searches or grades
change; totals remain 783 / 286 / 360. See
[Qualification 03](QUALIFICATION_03_2026-11-16.md).

Latest prototype (2026-09-10): [J1857 native nonlinear compatibility](J1857_NONLINEAR_PROTOTYPE_2026-09-10.md)
adds four Work log rows. Bounded compatibility passes; no operational profile,
calibration or search is produced. The preceding four-target ranking added five
Work log rows. All historical cells and 783 / 286 / 360 counts are preserved.

Latest comparison (2026-09-10): [J1802 joint model review](J1802_JOINT_MODEL_COMPARISON_2026-09-10.md)
adds four Work log rows, including a repaired output-write failure. Its model
hold remains; no Searches or grades change. Totals remain 783 / 286 / 360.

Latest preparation (2026-09-10): [J1802](ELL1H_J1802_PREPARATION_2026-09-10.md)
adds four Work log rows. Timing-interface checks pass; orbital/noise adequacy
holds block calibration. No Searches or candidate-grade rows change; totals
remain 783 / 286 / 360. All historical cells and notes are preserved.

Latest review (2026-09-10): [J1802 source clarification](J1802_MODEL_CLARIFICATION_2026-09-10.md)
adds three Work log rows. Explicit source removal of H3/H4 is established; the
preparation hold remains. No Searches rows or grades change. Counts remain
783 registered targets, 286 observed identities and 360 search/refinement records.

Current handoff (2026-09-10): 783 targets, 286 observed identities and 360
search/refinement records after J2317's H3-only NO_TRIGGER search. The wrapper
registered the terminal run; two further Work log entries document verified
closeout. See [J2317 observed search](ELL1H_J2317_OBSERVED_2026-09-10.md).
The earlier J2145 H3-only search also returned NO_TRIGGER. Its wrapper
registered the terminal result; two further Work log rows document closeout.
See [J2145 observed search](ELL1H_J2145_OBSERVED_2026-09-10.md).
The earlier binary pilot06 completed J0557+1551 with NO_TRIGGER.
The subsequent [J2317 preparation](ELL1H_J2317_PREPARATION_2026-09-10.md) adds
two Work log records, with no new Search or grade. It passed on the first attempt
and is ready for conditional calibration; no released red component is present.
Its subsequent [calibration](ELL1H_J2317_CALIBRATION_2026-09-10.md) adds three
Work log entries for threshold, mask/sensitivity and closeout. Threshold 22.902100,
929/940 eligible cells and 95/96 diagnostic recoveries are preserved. No Searches
row or grade is added; counts remain unchanged.
The subsequent ELL1H model-only assessment adds four Work log records and no
Searches rows: two H3-only adapter candidates and one missing-Shapiro-model hold.
See [ELL1H compatibility](ELL1H_COMPATIBILITY_2026-09-10.md). All eight grades
and historical records remain unchanged.
The H3-only adapter extension and J2145 real-data preparation subsequently add
three Work log records, again without new Searches or grades. J2145 is ready
for calibration with the released H3 retained and red coverage extended to 128
modes. See [preparation closeout](ELL1H_J2145_PREPARATION_2026-09-10.md).
Its subsequent [calibration](ELL1H_J2145_CALIBRATION_2026-09-10.md) adds three
Work log records for threshold, mask/sensitivity and verified closeout. Threshold
21.203245, 390/402 eligible cells and 90/96 diagnostic recoveries are preserved.
No observed search or grade is added; counts remain unchanged.
The five-system queue is complete; see BINARY_PILOT06_2026-09-10.md. Original
searches, current candidate grades and individual noise/model limitations remain
preserved. The preceding J0509 run is documented below.
The original result, calibration, near-threshold peak and excess residual-scatter
caveat are recorded in Searches and Work log; see BINARY_PILOT05_2026-09-10.md.
The preceding joint-noise development
reanalyses of J1012/J1752 are recorded in Work log, preserving original Search
rows and grades; see JOINT_NOISE_IMPROVEMENT_2026-09-10.md.
The subsequent EPTA J1012 native compatibility and fixed-period follow-up adds
four Work log records, including the retained first clock hold. Its independent
confirmation grade is now NOT_CORROBORATED; significance, disposition and all
356 Search rows remain preserved. See EPTA_J1012_FOLLOWUP_2026-09-10.md and its
immutable successor assessment.
The original J1012 crossing is preserved with a noise-sensitive review grade. Counts later in this file
are dated historical milestones. For the public-dependency operator backend,
see [agent closeout instructions](../AGENT_README.md#5-close-out-every-run-in-the-canonical-workbook).

The owner requested a master Excel workbook on 2026-09-08 to prevent duplicate
work. Update this single workbook in place after future completed work:

[Project Recherche Master](../outputs/recherche-master-20260908/Project-Recherche-Master.xlsx)

Initial contents: 88 unique targets (83 MPTA inventory targets plus five other
targets), 15 targets with observed searches, 16 search/refinement records and
12 engineering, simulation, qualification and acquisition records. Two targets
remain data gaps. No new scientific scans were executed to create the workbook.

- `Overview`: formula counts and interpretation/update instructions.
- `Targets`: canonical IDs, aliases, latest results, remaining work, dataset
  status, prior-study membership and input hashes. Operator notes are editable.
- `Searches`: consumed observed runs and retained refinements, thresholds,
  periods, sensitivity definitions, evidence filenames and SHA-256 hashes.
- `Work log`: rehabilitation, original failed qualification, passing replacement,
  simulations, automatic calibration, data gaps and the older archive pointer.
- `Candidate grades`: current significance, robustness and independent-confirmation
  assessments by search record ID, with conditional diagnostic counts/tails and
  evidence manifests. See [grading definitions](CANDIDATE_GRADING.md).

Before selecting a target, compare its canonical ID and aliases, dataset and
input binding with this register. A completed target does not imply all its
datasets or orbital periods have been searched. Preserve existing rows; use a
new record ID and predecessor ID for genuinely new work or refinements.

Excel filters and frozen identifiers are present. Summary formulas cover rows
2–1001 of Targets and Searches; extend them if either exceeds 1,000 records.
The initial counts, a status edit and the next table-row extension were checked.
All four sheet previews and the exported XLSX structure were checked. Native
Microsoft Excel was not used for calculation verification.

The initial builder and source manifest are beside the workbook. The builder
recreates the initial snapshot and must not be rerun over later operator edits.
Earlier Pilot 0/1 history remains in its original repository/archive records;
the workbook indexes that history without claiming a fresh adjudication.

## Required run closeout

Update this workbook whenever a run concludes, including failed or stopped
attempts, before reporting closeout. Preserve source results, earlier rows and
operator notes. Record the target, dataset, scope, outcome, evidence and remaining
work. Do not count preparation, calibration or an incomplete attempt as a
completed observed search.

`tools/recherche mpta-batch run` now invokes the updater after the scientific
command exits. It reads saved records, adds missing terminal rows by stable ID,
updates target status and records incomplete run destinations separately. It
preserves historical scientific rows and checks their hashes. Other run types
must be added explicitly to this same workbook during their closeout.

To update from existing evidence without any new scientific work:

```sh
tools/recherche master-workbook '../Project Recherche Data/mpta-batch02-20260908'
```

The updater imports the current workbook, preserves notes, rejects conflicting
existing scientific results, and keeps a content-addressed backup in
`../Recherche Recovery/20260907T223404/master-workbook-history/` before replacing
the master. It writes `master-workbook-update.json` under the selected batch.
If updating fails, repair and rerun this update command alone. Do not run the
scientific search again to repair a spreadsheet failure.

For the completed chromatic development checks, use the same updater with
`--chromatic-development` after the data directory. This reads `diagnosis.json`,
adds one development record per target, and updates preparation status without
adding observed-search rows or changing observed-result counts:

```sh
tools/recherche master-workbook '../Project Recherche Data/chromatic-support-20260908' --chromatic-development
```

TPA preparation uses `--tpa-preparation` with its batch directory. This appends
all 597 TPA inventory targets and a preparation record, while preserving the
existing 24 observed records. The master now contains 685 targets. Inventory
column labels are generic to accommodate both MeerKAT releases; evidence paths
identify the source. The source queue is in `FUTURE_DATA_SOURCES.md`.

`tools/recherche tpa-batch run` now updates the master and source queue after
each observed run, including incomplete attempts. For a workbook-only repair,
use `tools/recherche master-workbook DATA --tpa-observed`. The first five TPA
searches are complete. The current master contains 685 targets, 28 observed
targets and 29 search/refinement records. Preparation records remain preserved.

After TPA batch 02, the master contains 33 observed targets and 34
search/refinement records. All ten TPA searches returned NO_TRIGGER. Each
observed run updated this same workbook, preserving earlier rows and notes.

After the 25-target TPA batch 03, the master contains 58 observed targets and
59 search/refinement records. All 35 TPA searches returned NO_TRIGGER. Batch
preparation and observed updates use the actual selection count; no new master
or worksheet was created for the larger batch.

After TPA batch 04, the master contains 83 observed targets and 84
search/refinement records, including 60 TPA NO_TRIGGER searches. Each of the
25 batch-04 runs updated this same workbook and preserved previous records.

After TPA batch 05, the master contains 108 observed targets and 109
search/refinement records, including 85 TPA NO_TRIGGER searches. All 25 runs
updated the master individually; closeout verified the continuous workbook hash
chain and preserved all 84 earlier observed-result hashes.

After TPA batch 06, the master contains 133 observed targets and 134
search/refinement records, including 110 TPA NO_TRIGGER searches. Every run
updated the same master; closeout verified the workbook hash chain and all
109 earlier observed-result hashes.

After TPA batch 07, the master contains 158 observed targets and 159
search/refinement records, including 135 TPA NO_TRIGGER searches. Every run
updated the same master; closeout verified the workbook hash chain and all
134 earlier observed-result hashes.

After TPA batch 08, the master contains 183 observed targets and 184
search/refinement records, including 160 TPA NO_TRIGGER searches. Every run
updated the same master; closeout verified the workbook hash chain and all
159 earlier observed-result hashes.

After TPA batch 09, the master contains 208 observed targets and 209
search/refinement records, including 185 TPA NO_TRIGGER searches. Every run
updated the same master; closeout verified the workbook hash chain and all
184 earlier observed-result hashes.

After final TPA batch 10, the master contains 214 observed targets and 215
search/refinement records, including all 191 eligible TPA targets with NO_TRIGGER
results. The 406 exclusions remain inventoried. Each of six runs updated the
master; one final workbook-only update marked the source pool complete. Closeout
verified the full workbook hash chain and all 209 earlier observed-result hashes.

NG15 batch 01 added 16 searches: 15 NO_TRIGGER and the J1453+1902 candidate.
Current totals are 691 targets, 220 observed targets, 231 search/refinement
records, one candidate and no confirmed new discoveries.

J1453+1902's published properties, prior planet searches, conditional orbital
interpretation and proposed follow-up are documented in nine Work log entries
`J1453-20260908-*`. Proposed checks are marked NOT EXECUTED. The source note is
`results/research/j1453-context-20260908.json`; the bookkeeping receipt is
`results/research/j1453-context-workbook-update-20260908.json`.
Use `--candidate-context CONTEXT_JSON` after a batch directory for this type of
workbook-only annotation. It preserves consumed search rows and operator notes,
binds the source result hash, and writes a separate receipt without replacing
the batch's terminal workbook receipt. No scientific run is performed.

## Compelling-candidate follow-up

The owner requires bounded deep review for compelling candidates every time.
Follow [the policy](CANDIDATE_DEEP_REVIEW.md); append noise, simulation,
influence/consistency, source-comparison and closeout records to Work log.
Keep original Searches rows intact and put the current review disposition and
next action in the target record. J1939 deep-review evidence is in
`results/research/j1939-deep-review-20260909/`; the original candidate remains
a historical trigger, with INCONCLUSIVE / NOISE-SENSITIVE follow-up.

On 2026-09-09, the owner authorized the three-measure grading improvement.
The three reviewed candidates are now graded from preserved evidence. Normal
updates register new valid threshold crossings as review pending. The dedicated
`--candidate-grades` mode reads an assessment directory without requiring or
running a scientific batch. It preserves Searches, Targets and previous Work log
rows. Global FAP/sigma remain unavailable for the current candidates; the saved
conditional review tails are displayed separately.
