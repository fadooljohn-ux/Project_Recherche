# Pilot 1 published-reference discrepancy dossier v0.1

## Decision

**PASS WITH ADVISORY — the conversion and covariance checks pass, but the
published factor-of-three comparison is not a valid numerical promotion gate.**

The 0.56-lunar-mass quantity is real and was cited correctly. The defect is its
use as though it were a method-matched replication target. It should remain a
contextual literature value while an amended, lower-amplitude sensitivity grid
measures this pipeline's own 50% and 90% recovery crossings.

Initial v0.1 remains unauthorized until that amended grid passes every remaining
hard benchmark.

## What the published value measures

Behrens et al. report 0.56 lunar masses for J1744-1134 at 100 days in Table 1.
The table note identifies a circular orbit, 90% recovery/confidence convention,
and inclusion of a factor 2.5 timing-fit adjustment (SRC-001, PDF p. 3).

The underlying injections are not TOA-level, casewise full-refit injections.
The authors generated Gaussian white-noise residuals using reported TOA errors,
injected sinusoids after timing fitting, and applied a maximum Lomb–Scargle
threshold from 10,000 white-noise trials (SRC-001, PDF p. 4). They then
multiplied all limits by 2.5, a penalty estimated by injecting before TEMPO for
one isolated synthetic pulsar with uniform 1-microsecond errors and constant DM
(SRC-001, PDF pp. 4–5).

The published analysis also set EFAC to 1 and EQUAD/ECORR to zero for its
residual search. Pilot 1 instead uses the released 15-year wideband J1744 model,
433 epochs spanning 15.7 years, its white and red covariance, timing-design
projection, an empirical global maximum-delta-chi-squared threshold, TOA-level
injections, and compatible joint timing refits (SRC-D01, PDF pp. 3, 5, 30, 65;
SRC-D02, PDF pp. 10–12, 52). These are materially different experiments.

## Conversion audit

For a circular orbit viewed at projected amplitude `x = a_p sin(i) / c`, the
low-companion-mass relation is

`m sin(i) = x c M / [G M P^2 / (4 pi^2)]^(1/3)`.

An independent implementation reproduces the project function exactly. At
0.5 microseconds, 100 days, and 1.4 solar masses, both give
0.08054709634 lunar masses. Solving the exact two-body relation gives
0.08054709645 lunar masses, a relative difference of 1.42e-9. The conversion
therefore passes.

The published 0.56-lunar-mass value corresponds to 3.476 microseconds at
1.4 solar masses or 3.320 microseconds at 1.5 solar masses. Changing the central
mass assumption accounts for only 4.50%, not the factor of at least 6.95 in the
failed comparison.

## Covariance adequacy check

The predeclared diagnostic compared the timing-projected, covariance-whitened
observed residual vector with 1,000 frozen Gaussian covariance realizations.
It did not compute a periodogram, scan any frequency, inspect a peak, or make a
candidate inference.

| Diagnostic | Observed | Empirical central 99% interval | Outcome |
|---|---:|---:|---|
| Projected energy / dof | 1.0709 | 0.8776–1.1422 | PASS |
| Maximum absolute residual | 4.5124 | 2.6197–4.5234 | PASS |
| Maximum block lag correlation | 0.1031 | 0.0786–0.2352 | PASS |
| Variance | 0.8492 | 0.6960–0.9049 | PASS |
| Absolute skewness | 0.1353 | 0.0007–0.2524 | PASS |
| Absolute excess kurtosis | 1.2621 | 0.0071–0.9882 | ADVISORY FAIL |
| Median absolute deviation | 0.5394 | 0.4996–0.6283 | PASS |

All hard diagnostics pass. One of four advisory metrics—excess kurtosis—falls
outside the interval, below the predeclared two-advisory failure rule. The
covariance model is adequate for the bounded sensitivity extension, but the
heavy-tail flag must be retained as a limitation and rechecked before any
claim beyond this single target/model.

## Disposition

1. Preserve the original 20/22 promotion failure unchanged.
2. Replace the invalid numerical literature-ratio gate prospectively with a
   hard applicability-disposition gate: source verified, conversion verified,
   method differences recorded, and ratio retained for context only.
3. Freeze a 240-case lower-amplitude extension at 0.1, 0.2, 0.3, and
   0.4 microseconds over the five existing interior periods, reusing—not
   rerunning—the immutable 0.5–5.0-microsecond cases.
4. Define recovery as both exceeding the locked global threshold and placing
   the global peak within one independent Fourier bin of the injection. This
   is stricter than the original surface aggregator's trigger-only fraction;
   it does not alter any parent cell because all detected parent injections
   recovered their frequencies.
5. Require both 50% and 90% crossings at at least three periods, all extension
   fits to converge, frequency recovery at least 95%, zero independent-audit
   failures, and continued compliance with the four-hour total runtime cap.
6. Do not run an observed-residual periodic search until a separate
   post-promotion freeze is reviewed.

## Evidence limits

This dossier establishes method non-equivalence; it does not prove which
pipeline yields a better real-world mass limit. The covariance diagnostic is a
bounded posterior-predictive check, not a guarantee against nonstationary,
quasi-periodic, or unmodeled astrophysical noise.
