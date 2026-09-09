# UTMOST batch 02 — 9 September 2026

The owner authorized increasing UTMOST batches to 25 and preparing and launching
the next batch. The saved selection contains 25 isolated pulsars not previously
searched by Recherche, excluding all four consumed UTMOST batch-01 targets.
The existing 30–400-day circular search and conditional 1% batch allowance apply.
Binary support remains deferred; Recherche remains private.

## Selection and preparation

Selection uses the current master and prior UTMOST run destinations to exclude
completed work. Remaining coverage candidates are ordered by whether Recherche
has searched the target, membership count in the three named prior-study
inventories, published white timing error divided by the square root of TOA
count, then target ID. The white-error proxy includes released EFAC and EQUAD;
it is not a full red-noise sensitivity forecast. No observed peaks inform the
selection. Absence from those named inventories does not establish novelty.

All 25 datasets prepared without retries: 4,989 TOAs over 4,046 target-specific
observing days. Each passed the phase check and none raised the preparation
noise-adequacy flag. Null reduced chi-squared ranges from 0.956 to 1.076.
Released DE430, TT(TAI), explicit or implicit time units and the Molonglo clock
lookup conventions follow the [first preparation](UTMOST_PREPARATION01_2026-09-09.md).

Calibration used 4,096 fixed-noise null realizations per target, 102,400 total,
and 75 deterministic template checks. The 25-target allowance gives thresholds
26.1103–26.4980. Of 4,956 grid cells, 133 are excluded by each target's fixed
timing-projection mask. The median worst-phase 95% on-grid sensitivity ranges
from 26.0 to 487.9 microseconds across targets. These are conditional analytic
sensitivity estimates and development simulations, not observed detections.

Input profiles, calibrations and masks were frozen and backed up before launch.
The backup archive was read back against the source files. Existing solver
code in `src/` and `mpta_batch.run` remains unchanged. The UTMOST adapter and
wrapper now accept a saved batch via `--data`; selection size and false-alarm
accounting bind the actual selected count. Previous observed records and
prepared inputs remain preserved.

## Operator commands

```sh
tools/recherche utmost-prepare inventory --data '../Project Recherche Data/utmost-batch02-20260909' --batch-size 25
tools/recherche utmost-prepare prepare --data '../Project Recherche Data/utmost-batch02-20260909'
tools/recherche utmost-prepare calibrate --data '../Project Recherche Data/utmost-batch02-20260909'
tools/recherche utmost-search freeze --data '../Project Recherche Data/utmost-batch02-20260909'
tools/recherche utmost-search run --data '../Project Recherche Data/utmost-batch02-20260909' --target TARGET
```

These document the consumed preparation and launch sequence, not instructions
to rerun it. Each observed run updates the canonical workbook, including a
failed attempt. The batch driver also retains each workbook receipt and updates
the source queue. Input acquisition and prepared residuals remain outside Git.
Portable preparation evidence is in `results/research/utmost-batch02-20260909/`;
observed evidence is in `results/observed/utmost-batch02-20260909/`.

## Interpretation boundary

UTMOST is effectively single-band. Fixed released red and white noise describes
total timing variability; it does not separately identify orbital, dispersion
or scattering processes. Noise hyperparameter uncertainty and unmodeled
variability remain outside the conditional sensitivity estimate. NO_TRIGGER
does not exclude planets below sensitivity, in masked cells, outside the period
range or outside the circular model. A qualifying candidate requires the standing
bounded deep review before stronger interpretation.

## Observed batch closeout

All 25 original searches completed once: 24 NO_TRIGGER and one threshold
crossing, J1327-6222. No execution failures or noise-adequacy flags occurred.
The master updated after each run, adding 25 records without changing the
256 historical search records. Counts are now 250 observed targets and 281
search/refinement records.

| Target | Peak period (days) | Statistic | Threshold | Result |
|---|---:|---:|---:|---|
| J1210-5559 | 34.2608 | 7.9079 | 26.1838 | NO_TRIGGER |
| J1243-6423 | 89.5622 | 12.3806 | 26.2547 | NO_TRIGGER |
| J1644-4559 | 30.8083 | 6.8129 | 26.4980 | NO_TRIGGER |
| J1430-6623 | 50.9046 | 10.7862 | 26.2246 | NO_TRIGGER |
| J0837-4135 | 143.5361 | 7.9771 | 26.2646 | NO_TRIGGER |
| J1326-5859 | 160.9320 | 7.6287 | 26.2547 | NO_TRIGGER |
| J0255-5304 | 55.3628 | 16.3539 | 26.3232 | NO_TRIGGER |
| J1544-5308 | 86.2999 | 11.7843 | 26.2246 | NO_TRIGGER |
| J1604-4909 | 142.3509 | 9.7209 | 26.1631 | NO_TRIGGER |
| J0738-4042 | 56.0776 | 11.7416 | 26.2745 | NO_TRIGGER |
| J1157-6224 | 97.5629 | 11.4426 | 26.2043 | NO_TRIGGER |
| J1557-4258 | 30.5060 | 7.3824 | 26.2043 | NO_TRIGGER |
| J1253-5820 | 37.9001 | 4.2055 | 26.1103 | NO_TRIGGER |
| J1327-6222 | 63.2591 | 50.2870 | 26.2547 | CANDIDATE |
| J1559-4438 | 64.5931 | 8.8569 | 26.1103 | NO_TRIGGER |
| J1001-5507 | 35.1122 | 12.0396 | 26.2843 | NO_TRIGGER |
| J1401-6357 | 34.6366 | 11.3809 | 26.2145 | NO_TRIGGER |
| J1534-5334 | 82.7355 | 6.9260 | 26.2547 | NO_TRIGGER |
| J1751-4657 | 320.3723 | 8.1997 | 26.2447 | NO_TRIGGER |
| J0907-5157 | 191.2961 | 7.3119 | 26.1838 | NO_TRIGGER |
| J1651-5222 | 41.1814 | 8.0807 | 26.1103 | NO_TRIGGER |
| J1327-6301 | 241.2384 | 10.8967 | 26.1316 | NO_TRIGGER |
| J1320-5359 | 68.9014 | 8.2756 | 26.1838 | NO_TRIGGER |
| J1633-5015 | 156.1089 | 4.9440 | 26.3135 | NO_TRIGGER |
| J1305-6455 | 275.2467 | 5.6841 | 26.1631 | NO_TRIGGER |

J1327-6222's original 63.2591-day peak has amplitude 140.4 microseconds and
statistic 50.287 against threshold 26.255. It is a candidate, not a confirmed
planet. The standing candidate policy triggered a separate bounded deep review,
with original results and threshold preserved. See the candidate review report
for the final interpretation: [J1327-6222 deep review](J1327_DEEP_REVIEW_2026-09-09.md).
The feature weakens under extended red-noise models; final follow-up disposition
is INCONCLUSIVE_NOISE_SENSITIVE, with no confirmed planet.

UTMOST now has 29 completed target searches and 57 unprepared coverage
candidates remaining. The 214 excluded pulsars remain inventoried. No next
batch or binary extension was launched.
