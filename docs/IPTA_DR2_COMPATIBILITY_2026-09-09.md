# IPTA DR2 Version B compatibility review — 9 September 2026

**Outcome: 14 isolated datasets pass the coverage screen; none is ready for the current adapter.** All 14 pulsars have previous Recherche searches, but the release adds potentially useful observation coverage. J1721−2457 is the preferred bounded adapter target. No calibration, fit, periodogram or observed search was performed.

## Scope and acquisition

The owner authorized the compatibility review after the UTMOST-NS combined-input gap. This review inventories public IPTA files, compares observation coverage with the master, and checks model import. Binary support and J1752-specific NS follow-up remain deferred. UTMOST-NS remains awaiting inputs; it is not exhausted.

The complete public GitLab archive is pinned to commit `96a7c69caaf5da5cd22532784a3063b98b500dbe` (11 March 2021, Nançay clock correction update). Archive size is 202,867,320 bytes and SHA-256 is `c9f3dfdacab22070c832d51d36b356477fc22b42867a9d37a6464a6a8e4da0d0`. Inputs remain outside Git under `../Project Recherche Data/ipta-dr2-review-20260909/`. Only the final `release/VersionB` and `release/clock` were reviewed; earlier working versions in the archive were excluded.

The [official release description](https://gitlab.com/IPTA/DR2/-/blob/96a7c69caaf5da5cd22532784a3063b98b500dbe/release/README.md) supplies timing files, combined-data white/red/DM noise parameters and clock files, and specifies TEMPO2 processing. This is a combined historical PTA release, so it is not a low-traffic, wholly independent survey. Background: [Perera et al. (2019), IPTA second data release](https://academic.oup.com/mnras/article/490/4/4666/5586597).

## Inventory and overlap

The 65 released targets reconcile as **44 binary models + one known wide-companion target (J1024−0719) + six isolated coverage exclusions + 14 isolated coverage candidates**. All 20 isolated identities already appear in completed Recherche searches. There are zero new isolated pulsar identities.

The six short datasets are J0340+4130, J0645+5158, J0931−1902, J1747−4036, J1832−0836 and J1923+2515. All span less than 1,200 days; three also have fewer than 40 observing days. The duration and observing-day screen was retained without selecting a new search period range.

The 14 coverage candidates contain **40,088 TOAs**. Active INCLUDE trees resolve without missing files and their TOA counts match the released NTOA field for all 65 models. Each isolated dataset's active groups has a released EFAC and EQUAD entry. These are input checks, not noise adequacy or sensitivity results.

| Target | Released TOAs | Span (years) | Observing days | Site-days without prior match* |
|---|---:|---:|---:|---:|
| J0030+0451 | 3,362 | 15.07 | 916 | 2 |
| J0711-6830 | 507 | 17.10 | 323 | 69 |
| J1721-2457 | 150 | 12.76 | 150 | 150 |
| J1730-2304 | 646 | 20.28 | 487 | 85 |
| J1744-1134 | 9,834 | 19.88 | 964 | 100 |
| J1801-1417 | 126 | 7.05 | 126 | 7 |
| J1824-2452A | 276 | 5.65 | 147 | 21 |
| J1843-1113 | 224 | 10.06 | 219 | 7 |
| J1911+1347 | 140 | 7.48 | 138 | 4 |
| J1939+2134 | 13,659 | 29.44 | 2388 | 2175 |
| J1944+0907 | 1,696 | 5.71 | 48 | 22 |
| J2010-1323 | 8,057 | 7.38 | 465 | 395 |
| J2124-3358 | 1,182 | 20.00 | 905 | 164 |
| J2322+2057 | 229 | 7.89 | 221 | 15 |

*Compare physical telescope plus integer observing day against the retained original TIM inputs bound to all matching master Search records, allowing ±1 day for reprocessing/time-boundary differences. A site-day counts once per physical telescope and day, even if many channel TOAs exist. Counts indicate possible additional coverage, not confirmed independent measurements. Original files can include observations later excluded in preparation, making this comparison conservative. Exact site/MJD/frequency matches are separately retained in the CSV/JSON but are not used to claim independence; newer wideband reductions need not have identical timestamps or frequencies. No imported dataset has been concatenated with prior inputs.

TIME offsets are accumulated through active INCLUDEs, and timestamp offsets use Decimal arithmetic. Commented INCLUDEs, comments and local END boundaries are respected. The site code `w` is Nançay here (the release's NRT.DDS file and pinned PINT ncyobs alias), not Westerbork; WSRT is identified separately. Effix and Jodrell ROACH aliases are grouped by physical telescope. [LEAP](https://www.epta.eu.org/the-leap-project.html) epochs conservatively mark possible overlap at its five member telescopes, avoiding false novelty from a combined-array label. Backend-specific clock routing must retain this distinction even though coverage groups by physical site.

## Compatibility findings

1. **Legacy timing convention is the common blocker.** All 65 released TDB models specify `T2CMETHOD TEMPO`, `TIMEEPH FB90`, `DILATEFREQ N`, `EPHEM DE436` and `CLK TT(BIPM2015)`. Their TDB variants avoid an unnecessary TCB conversion. Model-only imports of J1721−2457, J0711−6830 and J1939+2134 in the pinned Intel PINT environment each changed T2CMETHOD to IAU2000B with a warning. The [PINT timing-model implementation](https://nanograv-pint.readthedocs.io/en/latest/_modules/pint/models/timing_model.html) and installed source confirm this limitation. Successful import does not preserve the published model. No imported model was used to calculate residuals.
2. **Clock and ephemeris binding needs its own intake path.** The archive supplies eight clock files, including Nançay's chain. Recherche's existing PTA entry point binds DE440 and other BIPM versions for its supported releases; reusing it unchanged would substitute conventions. DE436 and BIPM2015 were not found in the retained Recherche data resources. No TEMPO2 executable was found on the current shell PATH. These are implementation/resource tasks, not an author-access barrier. Full clock-chain coverage and observatory coordinates remain to be checked during adapter preparation.
3. **Noise representation needs an explicit translation.** EFAC/EQUAD, optional ECORR, power-law red and DM noise, and group/system jumps are present. PINT recognized the relevant noise components in the three imports, but recognition alone does not establish equivalent covariance. The existing adapter already handles related white-noise scaling and DM-amplitude conventions for EPTA/PPTA; IPTA normalization, group masks, Fourier mode counts and ECORR epoch grouping need comparison with the release's TEMPO2 conventions. `TNSubtractDM` was unrecognized during import and its handling must be resolved explicitly rather than treated as permission to remove a stochastic signal. Preserve raw arrivals and use the released noise in the null covariance.
4. **TIM mechanics are bounded and familiar.** Active data use FORMAT/MODE/TIME directives, multi-file INCLUDEs and phase-offset flags. The existing normalizer already covers these broad forms, and PINT supports `padd`; telescope-clock semantics and phase connection still require a direct preparation check. No evidence here calls for changing Recherche's qualified search solver or adding binary support.

This review establishes a feasible adapter route, not an operational pass. Sensitivity, phase connection, residual agreement and noise adequacy have not been measured.

## Recommended next bounded work

Start with **J1721−2457**: 150 observing days over 12.76 years, comprising 71 Nançay and 79 Westerbork days. Our completed run used MeerKAT, so this offers the clearest new telescope coverage among the small, uncomplicated packages. Its released residual RMS is about 17.7 microseconds; that is a descriptive fit statistic, not a planet sensitivity estimate.

1. Prepare a minimal TEMPO2-backed timing front end that honors the released TDB model, clocks and DE436, passing residuals, design matrix and noise bindings into the existing Recherche interface. Keep it separate from the qualified search solver. An alternative conversion to PINT would need an explicit timing comparison; changing the model label alone is insufficient.
2. Use J1721−2457 for one bounded timing/noise equivalence and phase-connection check. Resolve any concrete mismatch there before scaling to other targets. This is preparation, with no planet search needed to demonstrate compatibility.
3. If that succeeds, prepare J2010−1323 as the next dataset with substantial previously unrepresented Nançay/Jodrell coverage. Keep J1939+2134 as a separately labeled follow-up: its long old European coverage is useful but mixed-source noise and shared historical data make it a more complex first adapter case.
4. Only after preparation and calibration should a new target list, period range and campaign false-alarm allocation be frozen for an owner-directed launch. Do not rerun any consumed destination or count overlapping PTA measurements as independent confirmation.

J0030+0451, J1801−1417, J1843−1113 and J1911+1347 add only two to seven unmatched site-days each; these are low-priority reanalyses, not compelling fresh pools. The recommendation is a small adapter task followed by a decision on measured compatibility. It does not authorize installing a broad timing stack, launching 14 searches or expanding to binaries. No authors were contacted and no account credentials were created during this review.

## Evidence and register

- `results/research/ipta-dr2-review-20260909/inventory.json`: all 65 dispositions and source bindings.
- `isolated-targets.csv`: all 20 isolated targets, including six exclusions.
- `input-manifest.json`: hashes of the selected release inputs, clock files and retained comparison TIMs.
- `model-import-probe.json`: three model-only imports and exact warnings.
- `outputs/ipta-dr2-review-20260909/inventory.py`: repeatable metadata/overlap inventory; no science execution entry point.
- The canonical master receives four Work log rows and no Target/Search/Candidate grade additions. The source queue records this review as awaiting adapter preparation.
- `preservation-check.json` and `master-workbook-update.json` record historical evidence and workbook preservation at closeout.
