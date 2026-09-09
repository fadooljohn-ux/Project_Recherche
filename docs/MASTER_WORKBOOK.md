# Project Recherche master workbook

Current handoff (2026-09-09): 754 targets, 277 observed identities and 351
search/refinement records after IPTA hold resolution. Counts later in this file
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
