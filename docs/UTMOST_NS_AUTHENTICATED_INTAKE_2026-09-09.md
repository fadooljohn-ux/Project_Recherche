# UTMOST-NS authenticated acquisition and preparation assessment

9 September 2026. **28,305 raw arrival times acquired from 173 pulsars.
No calibration or observed search launched: combined timing inputs remain missing.**

The owner authorized acquisition, reconciliation, representative preparation and
execution of compatible isolated datasets in batches up to 25. The owner also
authorized a temporary portal API token for download and its subsequent
revocation. Both actions are complete. The portal confirms that no API token
remains, and the downloader has exited. Recherche remains private.

## Downloaded observations

All 174 inventoried portal names received a completed, paginated query against
`MONSPSR_TIMING`, using one frequency channel, total intensity, one integrated
arrival time per observation and no per-observation DM correction. This matches
the broad timing-product convention described by the official
[PSRDB downloader](https://github.com/OZGrav/psrdb/blob/main/psrdb/tables/toa.py).
MJDs remain full-precision decimal strings; frequencies, uncertainties, source
IDs, flags and linked model IDs are retained in the original JSON responses.
Raw observations are stored outside Git.

| Finding | Count |
|---|---:|
| Completed target queries | 174 |
| Targets returning this one-channel timing product | 173 |
| Unique raw arrival times | 28,305 |
| Raw TOAs with S/N > 7, before manual exclusions | 14,098 |
| Linked ephemeris records acquired | 173 |
| Duplicate TOA IDs or duplicate archive/MJD/frequency/site rows | 0 |
| Standalone NS datasets reaching 1,200 days | 0 |
| Targets overlapping retained EW DR1 | 146 |
| Raw EW+NS unions reaching 1,200 days | 146 |
| Eligible isolated targets with a linked, nonplaceholder model covering the full union | 0 |
| Verified combined packages / calibrations / observed searches | 0 / 0 / 0 |

J1939+2134 returned zero TOAs for this exact product selection. That is a product
availability gap, not a non-detection or a claim that no observations exist.
The unresolved portal name J1357-62 remains unresolved; acquiring its records
does not establish a canonical pulsar identity or create a master target row.

Raw NS spans range from 98.728511 to 814.768571 days. The earlier metadata
inventory's maximum was about 819 days; metadata observations and returned TOAs
are different inventories. The previous 1,200-day minimum, 40-observing-day
screen and 30–400-day search range remain in force.

These are **not asserted to be the publication's cleaned dataset**.
[Dunn et al. (2025)](https://arxiv.org/abs/2506.22697) report 34,575 observations,
18,360 TOAs above S/N 7 and 17,990 after 370 manual RFI exclusions. Our live
portal product differs in count, and its manual exclusion list was not verified.
We have not silently reconciled that difference by accepting or rejecting
observations based on their residuals.

## Why preparation cannot advance to a search

The timing-model inventory has 59 generic 1970–2106 validity windows; these are
placeholders, not long observational baselines. Two other model windows exceed
1,200 days: J0820−1350's window ends in 2018, before NS observations, while
J1022+1001 is a binary and outside current scope. No eligible isolated target's
linked model has a nonplaceholder validity window covering its raw EW+NS union.

Two representative checks make the gap concrete:

| Input | J0134−2937 | J1327−6222 |
|---|---:|---:|
| Raw NS TOAs | 437 | 102 |
| S/N > 7 TOAs, not manually vetted | 123 | 99 |
| NS span, days | 784.85 | 797.82 |
| Potential EW+NS union, days | 2,834.21 | 2,989.81 |
| Linked model validity span, days | 76.79 | 198.46 |
| Linked model's declared TOAs | 6 | 38 |
| Complete NS noise binding | Unverified | Missing in linked record |

J0134's record uses `TRACK -2` without supplied pulse numbers in the retrieved
TOA schema. Its EFAC/EQUAD numbers equal the old EW parameters; equality is not
evidence of a separate NS fit. Across the inventory, 125 overlapping targets
share at least one numeric noise parameter with their retained EW model.
J1327's linked record has no active EFAC/EQUAD/red-noise binding. The serialized
model records also do not provide the original fitted/fixed parameter flags.

Consequently, concatenating old and new arrival times would not establish the
pulse count across the gap, the instrument offsets or a valid combined noise
model. The older EW scans remain completed, consumed searches; reusing those
measurements in a future combined analysis would not constitute independent
confirmation.

The authenticated `filePulsarList` request returned **“You do not have permission
to perform this action.”** Raw-TOA access works, but this account cannot use that
file index. No alternate account, permission bypass or membership change was
attempted. No complete publication combined PAR/TIM/noise package was found in
the sources checked.

## Execution and preserved evidence

The first broad query timed out after saving 25 pages / 12,500 TOAs. Those files
are preserved. Per-target queries then completed successfully for all 174 names.
Every partial-query TOA ID appears in the complete download, and its core timing
fields agree. Partial files are not counted again. Pagination response files
and hashes provide the acquisition record; a minor cursor-label issue in the
first downloader's receipt is explained in `access-closeout.json` and corrected
in the reusable downloader.

The master workbook receives four additional work-log rows covering acquisition,
reconciliation, preparation gaps and the retained authorization. Its existing
targets, searches, candidate grades, operator notes and history are preserved.
No scientific solver or prepared search package was changed. No background
search remains active, so the search heartbeat stays paused.

Evidence:

- `results/research/utmost-ns-authenticated-20260909/reconciliation.json` and CSV.
- `results/research/utmost-ns-authenticated-20260909/access-closeout.json`.
- The original partial inventory in `results/research/utmost-ns-inventory-20260909/`.
- Raw responses and linked models under
  `../Project Recherche Data/utmost-ns-inventory-20260909/authenticated/`.
- Workbook update and preservation receipts alongside the reconciliation.

## Next action

Obtain the publication's full-precision combined PAR/TIM files, pulse-count and
fit conventions, instrument offsets/noise parameters and final exclusion list.
The [request draft](UTMOST_NS_DATA_REQUEST_DRAFT_2026-09-09.md) is ready for review
but has not been sent. The paper explicitly offers its products through the
portal or reasonable request to the corresponding author.

With those inputs, resume the already authorized representative preparation and
launch compatible datasets. No changed period range or new scientific design is
needed to resolve this input gap. J1752−2806's separate follow-up still waits
until the first observed run completes.
