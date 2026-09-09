# UTMOST-NS intake and launch readiness

**Update:** Authenticated acquisition is now complete: 28,305 raw TOAs and 173
linked models. Combined timing-package gaps still prevent launch. See the
[authenticated assessment](UTMOST_NS_AUTHENTICATED_INTAKE_2026-09-09.md).
The original pre-login assessment below is retained as history.

9 September 2026. **Public metadata inventoried; timing-data acquisition blocked.
No calibration or observed search launched.**

The owner authorized the four-step UTMOST-NS route: acquire timing inputs,
reconcile coverage, prepare a representative subset, and launch compatible
datasets in batches of up to 25. The existing isolated-pulsar 30–400-day scope,
1,200-day minimum baseline and 40-observing-day screen apply. Binary support
remains deferred. J1752−2806's follow-up is deferred until the first observed
run completes; no candidate-specific residual analysis was performed here.

## What is available

The [Pulsar Portal](https://pulsars.org.au/?mainProject=MONSPSR) publicly exposes
174 Molonglo target summaries and 33,361 observation records, all under
`MONSPSR_TIMING`. The inventory was obtained through the same GraphQL query used
by the portal and cross-checked against its visible Molonglo selector and totals.
The source snapshot is retained outside Git with SHA-256 hashes.

These portal counts differ from the 173 regularly monitored pulsars described
in [Dunn et al. (2025)](https://arxiv.org/html/2506.22697v1). They are a live
portal inventory, not a verified copy of the publication's cleaned timing
sample. Observation counts are not TOA counts or distinct observing-day counts.

| Inventory finding | Count |
|---|---:|
| Portal targets | 174 |
| Identities resolved against retained ATNF catalogue | 173 |
| Known binary or wide-companion flags | 11 |
| Resolved other targets, all below 1,200 days | 162 |
| Unresolved portal identity, also below 1,200 days | 1 |
| Targets previously searched by Recherche in other datasets | 104 |
| Overlap with UTMOST EW DR1 inventory | 146 |
| Overlap with the original EW DR1 coverage candidates | 71 |
| New resolved target identities appended to master | 11 |
| Standalone NS datasets meeting current duration criterion | 0 |
| Combined EW+NS datasets confirmed ready | Not established |

The unresolved portal identifier is `J1357-62`. It remains in the source
inventory without inventing a canonical identity or adding a possible duplicate
to the master. The 71 overlapping EW coverage candidates are not 71 ready NS
searches. Full combined timing and noise inputs have not been verified.

Coverage computed from the public first/last observation timestamps spans
98.728449–818.773900 days. The portal's rounded integer values are 99–819 days.
Thus the NS observations alone cannot satisfy the current 1,200-day screen.
Combining old EW measurements with new NS observations would require validated
phase connection, instrument offsets, clock corrections, noise parameters and
duplicate checks. Previous searches on the EW measurements remain consumed and
must not be represented as independent new data.

## Access and preparation findings

- An anonymous raw-arrival-time query to the public API returned
  `You must be logged in to perform this action`. No access restriction was
  bypassed. Sign-in is required; whether the account also needs project
  membership remains unverified.
- A public representative J0134−2937 query returned no TOA download link and a
  zero visible TOA count. This does not prove that the observations do not exist.
  Its accessible folding ephemeris covers a short 2021 interval and reports six
  TOAs. It is not a complete combined scientific timing solution.
- The website hides the bulk TOA download controls for Molonglo. Its API exposes
  a raw-TOA schema, but the authenticated response has not been inspected.
- The [official NS clock release](https://github.com/Molonglo/UTMOST-NS_clock)
  was acquired and verified against its Git blob hashes at commit
  `5bd1168b308b50fb5d5739d42a5801948348391b`. It supplies `mons2gps.clk` and the
  `MOST_NS` / `mons` observatory position. This is a distinct binding from EW;
  it has not been installed into or substituted for an existing science run.
- No complete EW+NS PAR/TIM/noise package was obtained from the public sources
  checked. The publication says products are available through the portal or
  by reasonable request to its corresponding author. No author was contacted.

## State of the four steps

1. **Acquisition: partial, awaiting authenticated timing-file access.** Public
   inventory and clock acquired; actual arrival-time package missing.
2. **Reconciliation: preliminary metadata complete.** Canonical identities,
   previous Recherche coverage, EW overlap and standalone duration assessed.
   Exact measurement deduplication awaits the arrival times.
3. **Preparation: blocked on inputs and a compatible baseline.** No simulated
   substitute, new noise model, threshold or prepared target was created.
4. **Execution: not launched.** No first run has completed, and the separate
   J1752 follow-up remains deferred. The authorization is retained for resumption.

## Resume from here

After portal sign-in, inspect whether access provides the cleaned NS TOAs,
publication timing solutions and instrument/noise definitions. If the portal
does not provide the combined package, obtain it from the authors. The needed
package is: original full-precision EW/NS TOAs with uncertainties and flags;
phase-connected PAR models and fit conventions; clock and observatory binding;
per-instrument EFAC/EQUAD and red-noise amplitude, index and Fourier-mode policy;
and cleaned sample/exclusion information. Reconcile shared EW observations
against the saved manifest before freezing any combined search.

Do not silently shorten the baseline criterion or period range, call a metadata
assessment a completed observed run, or start J1752's deferred follow-up because
this inventory is complete. No healthy long job needs a heartbeat here.

## Evidence and workbook

- `results/research/utmost-ns-inventory-20260909/inventory.json` and `inventory.csv`.
- External access responses, source files and workbook baseline:
  `../Project Recherche Data/utmost-ns-inventory-20260909/`.
- Reproducible metadata assessment and workbook-only update:
  `outputs/utmost-ns-inventory-20260909/`.
- Master updated with eleven new resolved identities and four intake work-log
  records. Original Targets, Searches, Work log rows and candidate grades are
  preserved. No new search row is added. Closeout verification and workbook
  hashes are saved beside the inventory.
