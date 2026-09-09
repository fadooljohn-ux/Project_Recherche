# UTMOST batch 03 — 9 September 2026

The owner authorized loading and launching the next 25 eligible UTMOST targets.
Use the existing ranked inventory, current master and consumed run destinations
to avoid repeating the 29 completed UTMOST datasets. Retain the 30–400-day
circular model, actual 25-target conditional 1% batch allowance, target-specific
calibrations and frozen masks. Binary support remains deferred; keep private.

Prepare, calibrate and freeze before each selection is executed once. Update
the canonical master after every terminal run, including a failed or stopped
attempt. Diagnose actual errors, preserve attempts and continue within scope.
Valid threshold crossings receive the standing bounded deep review and the
three evidence grades. Do not use hypothetical companion estimates as priors
or search seeds.

Data: `../Project Recherche Data/utmost-batch03-20260909/`.
Preparation evidence: `results/research/utmost-batch03-20260909/`.
Observed evidence: `results/observed/utmost-batch03-20260909/`.

```sh
tools/recherche utmost-prepare inventory --data '../Project Recherche Data/utmost-batch03-20260909' --batch-size 25
tools/recherche utmost-prepare prepare --data '../Project Recherche Data/utmost-batch03-20260909'
tools/recherche utmost-prepare calibrate --data '../Project Recherche Data/utmost-batch03-20260909'
tools/recherche utmost-search freeze --data '../Project Recherche Data/utmost-batch03-20260909'
tools/recherche utmost-search run --data '../Project Recherche Data/utmost-batch03-20260909' --target TARGET
```

Status: COMPLETE. All 25 original searches returned NO_TRIGGER.


## Preparation and calibration

All 25 targets prepared: 2,850 TOAs across 2,580 target-specific observing days.
The selection excludes all 29 consumed UTMOST datasets and leaves 32 unprepared
coverage candidates. The same 30–400-day model and 25-target allowance apply.

J0742-2822 initially failed the compact-phase check at 0.501343 cycles. All 180
TOAs have released pulse numbers, whose integer offset agrees exactly with the
imported phase. A localized adapter repair uses those supplied counts when the
fractional cluster alone exceeds half a cycle. Missing or inconsistent counts
still fail. Its repaired null reduced chi-squared is 1.034835. The failed attempt,
bounded phase diagnostic and 21 earlier preparations are preserved; the 21
previous residual arrays are exactly unchanged after rebuilding with the repair.
No calibration or observed scan preceded this repair. The shared solver is unchanged.

J0536-7543 retains a preparation warning: null reduced chi-squared 0.129124 under
its released white-noise model. The source has no TIM error-scaling directives;
its published EFAC 3.41096 is applied once. The low scatter is retained as a
noise-model limitation, without rescaling to improve sensitivity. The observed
runner's existing flag checks excess scatter only; this preparation warning
must therefore be reported separately even if its observed flag is false.

Calibration completed 102,400 fixed-noise null realizations and 75 deterministic
injected-template checks. These are calibration/development evidence, not planet
recoveries. Counts, thresholds and sensitivity ranges are recorded in
`results/research/utmost-batch03-20260909/calibration-summary.json`.

## Observed closeout

All 25 frozen datasets were searched once: 25 NO_TRIGGER, zero candidates,
zero observed execution failures and zero excess-scatter flags. J0536-7543
retains its separate low-scatter preparation warning. No new candidate requires
deep review; all three existing candidate grades are unchanged.

The master updated after each run, followed by separate repair and noise-warning
context entries. All 655 prior result files, 281 historical search rows and
existing operator notes are preserved. Counts: 743 targets, 275 with observed
searches, 306 search/refinement records, three historical candidate targets and
zero confirmed new discoveries. The 25 workbook receipts and two context
receipts form a verified hash chain ending at `d0a4dcd84704b9bd6489cfa0e4856c39811e0140e0eb5e8f16a76593c4789ed6`.

| Target | Peak period (days) | Statistic | Threshold | Result |
|---|---:|---:|---:|---|
| J1623-4256 | 49.7145 | 7.0095 | 26.1631 | NO_TRIGGER |
| J1435-5954 | 62.5088 | 6.3735 | 26.1735 | NO_TRIGGER |
| J0536-7543 | 46.8371 | 1.9418 | 26.2547 | NO_TRIGGER |
| J0418-4154 | 100.1780 | 11.7082 | 26.1103 | NO_TRIGGER |
| J1306-6617 | 33.8306 | 6.0922 | 26.1103 | NO_TRIGGER |
| J0856-6137 | 33.9011 | 8.4198 | 26.1210 | NO_TRIGGER |
| J0924-5814 | 100.4712 | 7.2727 | 26.1210 | NO_TRIGGER |
| J1418-3921 | 37.5129 | 8.4391 | 26.2547 | NO_TRIGGER |
| J1707-4053 | 32.2689 | 9.4111 | 26.1838 | NO_TRIGGER |
| J1715-4034 | 102.9431 | 6.6257 | 26.1838 | NO_TRIGGER |
| J1231-6303 | 45.9630 | 4.7746 | 26.1103 | NO_TRIGGER |
| J1824-1945 | 103.7461 | 20.8033 | 26.1103 | NO_TRIGGER |
| J0601-0527 | 70.0743 | 9.7287 | 26.3038 | NO_TRIGGER |
| J0452-1759 | 31.9674 | 13.9806 | 26.3038 | NO_TRIGGER |
| J1848-0123 | 32.8042 | 12.6797 | 26.1735 | NO_TRIGGER |
| J0837+0610 | 30.0023 | 10.1460 | 26.3232 | NO_TRIGGER |
| J2330-2005 | 31.0777 | 10.1859 | 26.1941 | NO_TRIGGER |
| J0820-1350 | 111.7403 | 11.4851 | 26.2246 | NO_TRIGGER |
| J1847-0402 | 128.9905 | 12.0567 | 26.1941 | NO_TRIGGER |
| J1705-3423 | 49.5864 | 7.5535 | 26.1421 | NO_TRIGGER |
| J1836-1008 | 150.6405 | 8.8109 | 26.1941 | NO_TRIGGER |
| J0742-2822 | 97.1396 | 10.9098 | 26.1526 | NO_TRIGGER |
| J2046-0421 | 208.0202 | 9.2460 | 26.1316 | NO_TRIGGER |
| J0151-0635 | 33.8972 | 15.4155 | 26.3135 | NO_TRIGGER |
| J2046+1540 | 66.9731 | 12.0228 | 26.1210 | NO_TRIGGER |

UTMOST now has 54 completed searches, 32 unprepared coverage candidates and
214 retained inventory exclusions. The 30–400-day model, fixed masks and
conditional sensitivity limits remain in force. No further batch or binary
extension was launched. All run01 destinations are consumed.

Terminal receipt: `results/observed/utmost-batch03-20260909/closeout.json`.
The read-back-verified prelaunch archive remains outside Git with the frozen
input package.
