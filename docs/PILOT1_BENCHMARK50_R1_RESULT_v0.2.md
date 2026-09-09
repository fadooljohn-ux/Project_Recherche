# Pilot 1 corrective first-50 result v0.2

## Outcome

The exact corrective replay passed all 17 frozen benchmark gates. The 50 cases,
seeds, order, detector, and scientific tolerances were unchanged from the
failed run. The only corrected hard measurement was the timing-application
accuracy metric frozen in v0.2.

The maximum high-precision TOA-adjustment error was 0.00000896 microseconds
against the 0.001-microsecond limit. The separate uncentered residual-target
difference was retained as a diagnostic and was not substituted for the direct
application measurement.

All ordinary and joint fits converged. Four explicit-full-covariance audits
passed their amplitude, phase, and chi-squared tolerances. Null whitening,
warning hygiene, artifact integrity, projected runtime, memory, and storage all
passed. The complete Pilot 1 workload projects to 1.19 hours on this MacBook.

## Progression boundary

The replay authorizes preparation of the remaining 990 calibration-null scans.
It does not authorize the sealed 500-case evaluation, an observed-residual
search, a candidate claim, or promotion to initial v0.1.
