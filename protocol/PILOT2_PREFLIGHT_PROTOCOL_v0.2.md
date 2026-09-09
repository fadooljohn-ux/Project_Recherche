# Pilot 2 B1937+21 preflight protocol v0.2

## Purpose and authority

This preflight tests whether the released v0.1 circular-signal machinery can be
ported safely to B1937+21 on the current MacBook. It is a generalization test,
not an observed-data companion search. This document freezes the design only;
execution remains locked until John Fadool gives a subsequent project
instruction to proceed with this preflight.

Fable or any other external adviser may later audit the package and recommend
changes, but cannot authorize, veto, or execute project work. Routine preflight
and calibration do not consume an external audit.

## Why B1937+21 is a useful stress target

The frozen metadata ranking selected B1937+21 without manual intervention. It
has 660 active wideband TOAs on 457 observing days over 5,798.043 days, a
median released TOA uncertainty of 0.008 microseconds, observations from both
Arecibo and the Green Bank Telescope, and an isolated timing model. It also has
released red-noise terms and fitted frequency-dependent terms. That combination
makes it computationally bounded but materially different from J1744-1134.

The selection is about pipeline generalization. It is not a statement that
B1937+21 is unusually likely to host a detectable companion.

## Controlled extraction

The preflight may reuse only the already verified NANOGrav 15-year v2.1.0
archive. It extracts exactly the six hash-bound B1937+21 products recorded in
`results/pilot2/target_selection_v0.2.json`: parameter, timing, noise,
configuration, DMX, and correlation files. No network download is allowed.

Extraction must reject absolute paths, parent traversal, links, unlisted
members, archive-hash mismatches, member-hash mismatches, and any output outside
a dedicated Pilot 2 data root. The expected selected payload is 427,936 bytes;
the complete data root remains capped at 1.5 GiB and outside Git.

## Reproduction gate

The released model and TOAs must load under the pinned environment and reproduce
the frozen metadata exactly within the stated numerical tolerances. A normal
wideband timing fit must converge with finite timing and DM residuals and no
unexpected material warning. This limited reproduction necessarily accesses
the released residual vector, which is why it remains locked until the user
authorizes the preflight.

Reproduction may report fit health and aggregate diagnostics. It may not scan
periods, rank peaks, inspect candidate-like periodic content, or derive a
threshold from the observed residuals.

## Fifty-case synthetic benchmark

After reproduction passes, generate exactly 20 covariance-model null cases and
30 injected circular-signal cases. The injection grid contains five periods
(50, 200, 365.25, 1,000, and 2,000 days), two amplitudes (1 and 5
microseconds), and three fixed phases. Synthetic cases use the B1937+21 epochs,
design matrix, and complete released covariance but never the observed
residual vector.

Ten injection identifiers, selected by the lowest SHA-256 rank, receive an
explicit full-covariance solver audit. The benchmark gates only integrity,
finite outputs, solver agreement, completion, and a projected full-calibration
runtime no greater than six hours. Trigger rate, recovery rate, annual behavior,
and boundary behavior are diagnostics because 50 cases cannot calibrate a
detector or support a sensitivity claim.

## Non-transfer rule

Nothing empirical from J1744-1134 transfers: not the delta-chi-squared
threshold, null distribution, injection-recovery surface, annual eligibility
mask, structured-tail result, or observed-search disposition. Reusing code is
permitted only after target-specific dimensions, covariance, fit parameters,
and hashes are rebuilt and checked.

## Stop and next gate

Any integrity, reproduction, solver, resource, or scope failure stops the
preflight without an observed periodic search. Passing permits preparation of a
separately frozen B1937+21 full-calibration design. It does not authorize that
calibration and does not authorize an observed search.
