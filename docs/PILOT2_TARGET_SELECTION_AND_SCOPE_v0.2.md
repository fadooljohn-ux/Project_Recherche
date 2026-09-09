# Pilot 2 target selection and bounded scope v0.2

## Outcome

The deterministic metadata-only selection chose **PSR B1937+21** as the second
target for Project Recherche. The inventory found 68 combined wideband
model/timing pairs; six passed every frozen hard gate. B1937+21 ranked first
with a score of 0.9042924339781505. No target was manually substituted.

The selection did not compute residuals or inspect periodic content. The
complete machine-readable cohort, gate results, component scores, selected
archive-member hashes, and authority boundary are preserved in
`results/pilot2/target_selection_v0.2.json`.

## Selected-target facts from the release

| Field | Result |
|---|---:|
| Active wideband TOAs | 660 |
| Unique floor-MJD observing days | 457 |
| Span | 5,798.043043897873 days |
| Median released TOA uncertainty | 0.008 microseconds |
| 90th-percentile released TOA uncertainty | 0.024 microseconds |
| Absolute ecliptic latitude | 42.29675207385422 degrees |
| Observatories | Arecibo and Green Bank Telescope |
| Binary timing model | No |
| Released red-noise terms | Yes |

All six eligible targets have released red-noise terms, so the frozen 5%
absence-of-red-noise component awarded no points to any eligible target. The
ranking still selected B1937+21 on the other fixed components.

## Limited MacBook pilot

Pilot 2 begins with one separately authorized preflight, not a full search:

1. verify the existing 638,719,668-byte archive against its frozen SHA-256;
2. extract only the six selected B1937+21 products into a dedicated external
   data root;
3. reproduce the released model/TOA loading and ordinary wideband fit without
   running a periodic scan; and
4. run a 50-case synthetic-only mechanics and runtime benchmark.

The preflight is capped at one wall-clock hour, 16 GiB peak memory, 1.5 GiB for
the complete data root, and zero additional download bytes. Raw or extracted
science data remain outside Git.

## Promotion path

A passing preflight only establishes that B1937+21 can enter target-specific
calibration. A later calibration must independently establish its null
threshold, sealed false-positive behavior, structured-noise behavior,
injection recovery, and annual identifiability mask. A proposed observed search
would remain a separate, explicit decision after those gates.

No external adviser is scheduled for the preflight. External review is reserved
for a critical milestone and remains passive: audit and recommendations only.

## Current state

- Target selection: complete.
- Selected artifacts: hash-bound.
- Preflight design: frozen.
- Product extraction: not executed.
- Observed-residual reproduction: not executed and not authorized by this
  package.
- Observed periodic search: prohibited.
