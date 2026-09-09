# Pilot 2 metadata-only target-selection protocol v0.2

## Purpose

Select one second pulsar to test whether the v0.1 circular-signal pipeline
generalizes beyond PSR J1744-1134. Selection uses only the existing NANOGrav
15-year v2.1.0 archive, timing-file metadata, and released model metadata. It
does not calculate timing residuals or inspect periodic content.

## Cohort construction

Inventory combined wideband timing/model pairs and exclude observatory-split
variants ending in `gbt` or `ao`. Exclude J1744-1134 because it is the completed
v0.1 target. Require the matching released noise, configuration, DMX, and
correlation products needed for reproducible extraction.

Hard gates bound both scientific usability and MacBook cost:

- 300–700 active wideband TOAs;
- at least 150 unique floor-MJD observing days;
- at least 4,500 days of span;
- median released TOA uncertainty no greater than 1.5 microseconds;
- absolute ecliptic latitude at least 10 degrees; and
- exact agreement between the active timing rows and released `NTOA` value.

The span supports at least 2.25 cycles at the v0.1 maximum 2,000-day search
period. The latitude gate reduces, but does not eliminate, annual astrometric
degeneracy. A new target must still receive its own injection-based annual
eligibility map.

## Ranking

Hard-eligible targets receive a fixed capped-linear score:

- median TOA precision: 35%;
- observing span: 20%;
- unique observing days: 15%;
- active TOA count: 10%;
- absolute ecliptic latitude: 10%;
- absence of a released red-noise component: 5%; and
- isolated timing model: 5%.

Every continuous component is clipped to the bounds frozen in the selection
configuration. Highest score wins; ties use lower median uncertainty and then
lexical pulsar name. No manual override is authorized after inventory.

This ranking chooses a bounded pipeline-generalization target. It is not a
claim that the selected pulsar has the highest astrophysical companion
probability in the release.

## Pilot 2 stage boundary

Selection authorizes documentation only. The next stage may extract only the
selected target's six named products from the already verified archive and run
a reproduction plus 50-case synthetic benchmark. That preflight is capped at
one hour, 16 GiB peak memory, and 1.5 GiB complete data-root size.

The J1744-1134 threshold, recovery surface, annual mask, and null distribution
do not transfer to the new pulsar. Pilot 2 must calibrate its own covariance,
threshold, structured-tail behavior, injection recovery, and annual mask before
any observed search can be proposed.

## Authority and claims

No observed-residual access, observed periodic search, target override, or
discovery claim is authorized by this protocol. John Fadool remains the sole
project authority. External advisers are passive observers only and are not
part of routine target selection or calibration work.
