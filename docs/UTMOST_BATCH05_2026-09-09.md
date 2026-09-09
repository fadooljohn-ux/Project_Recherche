# UTMOST batch 05 - 9 September 2026

The owner authorized saving the J1752 hypothetical companion estimate and
preparing and launching the next batch. This is the final seven coverage-eligible
UTMOST DR1 datasets, selected from the saved ranking after the 79 consumed
UTMOST searches. Consult the current canonical master and exclude consumed
source-target observations. Selection uses no residual peaks.

Prepare, calibrate, freeze and execute each selected dataset once under the
existing 30-400-day circular model, fixed published noise and masks, and a
conditional 1% batch allowance bound to the actual seven selections. Preserve
previous searches, failed attempts, qualification and candidate reviews.
Diagnose actual adapter errors and continue within this scope. Update the master
at every terminal run. Each valid crossing receives the standing bounded deep
review and three-measure grading. Keep private; binaries remain deferred.

This batch exhausts the current eligible UTMOST DR1 pool if all seven can be
processed. Preserve the 214 inventory exclusions; pool completion does not mean
all 300 pulsars were searched. Additional releases remain future work.

Data: `../Project Recherche Data/utmost-batch05-20260909/`.
Preparation: `results/research/utmost-batch05-20260909/`.
Observed results: `results/observed/utmost-batch05-20260909/`.

```sh
tools/recherche utmost-prepare inventory --data '../Project Recherche Data/utmost-batch05-20260909' --batch-size 7
tools/recherche utmost-prepare prepare --data '../Project Recherche Data/utmost-batch05-20260909'
tools/recherche utmost-prepare calibrate --data '../Project Recherche Data/utmost-batch05-20260909'
tools/recherche utmost-search freeze --data '../Project Recherche Data/utmost-batch05-20260909'
tools/recherche utmost-search run --data '../Project Recherche Data/utmost-batch05-20260909' --target TARGET
```

Status: COMPLETE - six NO_TRIGGER results and one documented preparation model gap.

## Preparation revision and compatibility gap

The original seven-target selection is preserved under `preparation-deferrals/`.
J1825-0935 failed before observed execution: its source uses DE405 and
`T2CMETHOD TEMPO`. The pinned PINT implementation supports IAU2000B and silently
coerces that requested legacy convention. No local Tempo2 or DE405 kernel is
available. Replacing conventions without validated reproduction would change
the source model. This dataset is therefore DEFERRED_UNSUPPORTED_TIMING_CONVENTIONS,
not NO_TRIGGER and not a failed planet detection. See the retained source check
and traceback in `preparation-deferrals/J1825-0935-diagnosis.json`.
Primary reference: https://nanograv-pint.readthedocs.io/en/latest/_modules/pint/models/timing_model.html

The six launchable datasets are J1705-1906, J1820-0427, J1703-3241, J2048-1616,
J2006-0807 and J1842-0359. Their revised selection and six-target calibration
policy were fixed before calibration. The first two completed preparations were
preserved and rebuilt solely to bind the revised selection; their residual
arrays are exactly unchanged. No shared scientific adapter or solver was changed.
A localized workbook change allows explicitly deferred batch targets to receive
context records without creating a fictitious observed search.

Final preparation contains 651 TOAs over 624 target-specific observing days.
Reduced null chi-square ranges 0.954910-1.020700, with no noise-adequacy warnings.
Evidence: `results/research/utmost-batch05-20260909/preparation-summary.json`.
After six searches the inventory will reconcile to 85 searched, one legacy-model
gap, and 214 preserved inventory exclusions, rather than 86 completed searches.

## Calibration

Completed 24,576 fixed-noise nulls and 18 deterministic
template checks. Thresholds span 23.277-23.608;
28 of 1194 grid cells are masked. The six-target 1% allowance
is conditional on the saved covariance and design. These calibrations are not
observed detections.

## Observed closeout

All six frozen observations were searched once: six NO_TRIGGER, zero candidates,
zero observed execution failures and zero noise-adequacy flags. The master was
updated after every search and preserves all 331 earlier search/refinement rows,
all seven candidate grades and operator notes. Its current totals are 743 targets,
277 observed targets and 337 search/refinement records. The 1,150 historical
result-file hashes and workbook receipt chain are unchanged/verified.

The selected pulsars had earlier searches using other observations; these six
runs add UTMOST dataset coverage without adding new target identities. No
additional candidate review was triggered. J1825-0935's failure and compatibility
disposition are explicitly registered without a fictitious observed-search row.

UTMOST DR1 closes at 85 searched datasets: 80 NO_TRIGGER and five original
crossings, all previously reviewed as noise-sensitive. The complete 300-target
inventory is 85 searched + one legacy-model gap + 214 earlier exclusions.
No compatible unprepared target remains in the assessed pool. Other releases
and binary support remain deferred; future intake requires its own scope.
Monitoring is paused after closeout. Do not rerun consumed destinations.

| Pulsar | Result | Peak period (days) | Statistic | Threshold |
|---|---|---:|---:|---:|
| J1705-1906 | NO_TRIGGER | 36.9673 | 8.577 | 23.340 |
| J1820-0427 | NO_TRIGGER | 88.2829 | 11.011 | 23.400 |
| J1703-3241 | NO_TRIGGER | 47.8360 | 9.072 | 23.350 |
| J2048-1616 | NO_TRIGGER | 312.9954 | 13.693 | 23.608 |
| J2006-0807 | NO_TRIGGER | 33.2514 | 7.115 | 23.277 |
| J1842-0359 | NO_TRIGGER | 178.5510 | 4.915 | 23.288 |

Terminal verification: `results/observed/utmost-batch05-20260909/closeout.json`.
