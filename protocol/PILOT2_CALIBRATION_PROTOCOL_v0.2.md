# Pilot 2 B1937+21 calibration protocol v0.2

## State and authority

This package defines a target-specific full-calibration design for B1937+21.
Execution is not authorized. It does not permit observed-residual access, an
observed periodic search, threshold calibration, or a companion claim until a
later implementation and execution freeze is separately prepared and approved
by John Fadool.

External advisers are optional passive auditors. They do not authorize or veto
routine calibration work, and no Fable review is scheduled for this design
gate.

## Detector and non-transfer rule

The detector retains the validated covariance-whitened GLS circular scan and
`ProjectCircularSignal` joint grader. It rebuilds the 1,320-dimensional released
white-noise plus red-noise covariance and the rank-284 timing-design projection
from the hash-bound B1937+21 products.

The search grid spans 30–2,000 days at one-fifth-independent-bin spacing. The
J1744-1134 threshold, null distribution, recovery surface, annual mask, and
observed-search disposition do not transfer.

## Stage A — Gaussian threshold calibration

Generate exactly 1,000 covariance-Gaussian nulls at the actual B1937+21 epochs.
Each case scans the complete frozen period grid and retains its global maximum
delta chi-square. Lock the conservative nearest-rank 99th percentile and use a
strict greater-than trigger. Commit the threshold record and hashes before the
sealed evaluation can start.

The calibration ensemble must pass its whitened variance and pooled lag-
correlation gates. No statistic from a later stage may retune the threshold.

## Stage B — sealed Gaussian evaluation

Generate exactly 500 seed-disjoint evaluation nulls after the threshold lock is
committed. Apply the threshold without adjustment. Pass only if the empirical
false-positive rate is at most 1% and its Wilson 95% upper bound is at most
2.5%. A failure stops calibration; the evaluation set cannot be rerolled.

## Stage C — structured-tail readiness

Apply the locked Gaussian threshold to three disjoint 1,000-case stress sets:

1. a timing-native-innovation scale mixture;
2. a DM-native-innovation scale mixture; and
3. an observing-day-clustered scale mixture applied to paired timing and DM
   coordinates.

Each uses 1% contaminated draws, a standard-deviation multiplier of 3, and
analytic unit-variance normalization. The marginal innovation excess kurtosis
is 1.6296296296 before covariance mixing and projection. No structured-tail
calibration set exists. A variant requires rebaseline if its Wilson 95% lower
false-positive bound is strictly greater than 1%. Variants are not pooled and
cannot be rerolled.

## Stage D — injection recovery

Run 240 main injections using five period-specific amplitude ladders, four
phases, and three covariance-noise realizations per phase. The ladders are
smaller at 50–200 days and larger at 500–1,000 days because the preflight showed
strong period dependence. This design choice was frozen before calibration and
does not constitute a sensitivity estimate.

For each case, apply the signal to high-precision TOAs, execute the ordinary
timing refit, scan the complete grid, and jointly fit the circular component at
the proposed frequency. Record recovery, amplitude and phase error, ordinary-
model absorption, circular-to-astrometric correlation, warnings, timing, and
hashes. Twenty-nine SHA-256-selected cases receive an explicit full-covariance
solver audit.

A sampled 50% or 90% sensitivity crossing may be reported only when the tested
amplitudes bracket it. At least three main periods must bracket both crossings,
and at least three must show monotonic detection fractions. The strongest
amplitude at every main period is the strong control and must reach the frozen
recovery gate.

## Stage E — annual and boundary maps

The annual map contains 28 cases at 300, 330, 350, 365.25, 380, 400, and 450
days. A period becomes ineligible if maximum circular-to-astrometric correlation
or ordinary-model absorption reaches 0.8. Ineligible periods are explicit
sensitivity gaps and cannot produce candidates.

The 16 boundary cases separately test 30 and 2,000 days. Boundary behavior is
reported and cannot silently extend the calibrated domain.

## Operational controls

The frozen inventory contains 4,784 unique science cases and 4,784 unique
seeds. Checkpoint every 25 cases and emit an operational heartbeat at least
every 30 seconds. A desktop-visible health record must expose stage, process
health, elapsed time, completed/checkpoint counts, and last heartbeat while
keeping incomplete-stage scientific outcomes sealed. Manual refresh must be
available.

Resume is allowed only when inventory and implementation hashes match exactly.
Any integrity mismatch, unexpected material warning, nonfinite statistic,
resource-cap breach, or failed stage stops the run. Failed or sealed sets may
not be rerolled.

## Resources and promotion

The workload contains 4,784 scans, 568 primary injection fits, and 29 explicit
full-covariance audits. Applying measured B1937+21 preflight costs plus a 25%
contingency projects 2.6754 wall hours. Hard caps remain six hours, 16 GiB peak
memory, 1.5 GiB for the complete v0.2-r1 data root, and zero downloads.

Passing all stages promotes B1937+21 to a calibrated second target and permits
preparation of a separate observed-search design. It never authorizes that
search. A failed stage produces a complete scorecard and rebaseline decision,
not another seed set.
