# IPTA held-case resolution — 9 September 2026

The owner authorized a bounded audit of the seven batch02 holds, correction of
the comparison or inputs as supported, and calibration/search of cases that
clear. The six completed batch02 searches remain preserved.

## Finding and repair

The blocking 0.1% comparison of historical PAR-file TRES/CHI2R against our
current raw RMS and marginal GLS statistic was an internal implementation
choice. It did not compare equivalent statistical quantities. It is replaced
by direct verification of the likelihood, with the historical values and their
differences retained as descriptive metadata.

For covariance C = N + F Fᵀ, the marginal GLS quadratic minimized over timing
parameters equals the minimum white-noise residual quadratic **plus** the
squared Gaussian noise coefficients in an augmented least-squares problem.
F already contains the released physical noise amplitudes. Timing parameters
have no prior penalty. The independent calculation uses TEMPO2's exported noise
factors and scaled measurement errors, versus the adapter's covariance route.
This tests the numerical likelihood; it does not establish that the fixed
noise model captures every astrophysical or instrumental effect.

| Representative | Marginal GLS χ² | White residual χ² | Noise-prior penalty | Sum minus marginal, absolute |
|---|---:|---:|---:|---:|
| J1843−1113 | 203.144024916 | 162.282251495 | 40.861773421 | 3.98×10⁻¹³ |
| J0711−6830 | 524.862239171 | 524.840129357 | 0.022109813 | 1.14×10⁻¹³ |

TEMPO2's SVD fit code reports its data-only quadratic, excluding the prior
penalty (`reference/TKfit.C`, lines 430–440 in the pinned reference snapshot).
For J1843 this reproduces the earlier direct TEMPO2 fit's 0.776470 reduced χ².
Recherche's corresponding marginal statistic is 0.971981. Requiring these
different quantities to agree would be an error. The historical PAR value,
0.9599, remains a separate historical summary, not a validation oracle.

The primary publication also distinguishes timing RMS from RMS after removing
estimated correlated noise; its table values should not be substituted for
raw-residual RMS without matching that convention. See
[Perera et al. (2019)](https://academic.oup.com/mnras/article/490/4/4666/5586597).
Exact historical reproduction is not claimed: J0711's RMS difference remains,
and switching to the released TCB variant did not resolve it.

Correction to one earlier narrative diagnostic: the saved J1843 check gives
**0.97198098**, not 0.94781902. The earlier diagnosis JSON transcribed the sign
of its difference incorrectly. Its original numerical checks, batch table and
held disposition remain preserved; this note corrects the narrative explicitly.

## Bounded acceptance and execution

- Pinned target identity, original bytes and exact direct timing exports remain
  required, along with full-rank timing design and the existing phase check.
- New reference output checks TEMPO2's actual fit-window indices, including
  arrivals otherwise not marked deleted. All intended arrivals must agree.
- White/red/DM/ECORR covariance comparisons retain the original numerical bounds.
- The independently solved marginal and penalized likelihoods must agree within
  1e−7 relative / 1e−5 absolute χ², with full joint rank. The adapter likelihood
  must also agree with the reference-factor calculation. This was declared in
  `results/research/ipta-hold-review-20260909/plan.json` before the audit.
- No noise amplitude, period range, mask or detection threshold is adjusted to
  match a publication summary. The qualified scanner and calibration source
  remain unchanged.
- The exact original 13-target manifest and target seeds are reused in a
  separate continuation directory. The allowance remains conditional 1% across
  those thirteen searches. Seven new searches may complete the reserved slots;
  none of the original six is repeated.
- Each cleared target receives 4,096 nulls, its own threshold/mask/sensitivity,
  and one 30–min(2,000, half-span)-day circular search. Valid crossings invoke the
  standing deep-review policy. The master records historical-summary differences.

Review evidence: `results/research/ipta-hold-review-20260909/`.
Continuation evidence: `results/observed/ipta-hold-release-20260909/`.
Full inputs and logs: `../Project Recherche Data/ipta-hold-release-20260909/`.
These new records preserve the complete prior closeout and its failed attempts.

## Completed continuation

All seven holds cleared the numerical timing/noise checks and independent
likelihood audit. Each was calibrated and searched once: seven NO_TRIGGER,
zero new candidates, zero execution failures. 0 noise-adequacy flags were reported.
The original six searches were not repeated. All thirteen batch02 datasets
are now searched, or fourteen IPTA datasets including the earlier J1721 case.

| Target | TOAs | Peak period (days) | Peak Δχ² | Threshold | Median sensitivity (µs) | Result |
|---|---:|---:|---:|---:|---:|---|
| J1911+1347 | 140 | 39.138 | 10.261 | 26.545 | 1.125 | NO_TRIGGER |
| J1843-1113 | 224 | 43.518 | 12.140 | 27.147 | 0.960 | NO_TRIGGER |
| J0711-6830 | 507 | 1677.665 | 20.299 | 28.209 | 0.966 | NO_TRIGGER |
| J1730-2304 | 646 | 51.343 | 14.068 | 28.550 | 0.879 | NO_TRIGGER |
| J2124-3358 | 1,182 | 162.151 | 8.737 | 28.522 | 1.021 | NO_TRIGGER |
| J1744-1134 | 9,834 | 72.743 | 23.808 | 28.510 | 0.178 | NO_TRIGGER |
| J1939+2134 | 13,659 | 81.977 | 18.538 | 29.294 | 0.049 | NO_TRIGGER |

Sensitivity is the median over eligible cells of the worst-phase circular
on-grid amplitude for 95% detection probability under the fixed supplied noise
model; it is not a posterior upper limit. Each calibration includes 4,096 null
realizations and preserves its annual mask and full sensitivity curve.

Historical PAR summary differences remain flagged for all seven datasets.
The repair establishes numerical consistency of the current fixed model;
it does not claim exact historical-analysis reproduction. NO_TRIGGER applies
to the calibrated unmasked period grid, not to all possible planets.
No new crossing requires a candidate review. J1939’s earlier source-specific
candidate and deep-review disposition remain intact; overlapping IPTA
observations do not constitute an independent replication.

The compatible IPTA pool is complete: 14 searched, six coverage exclusions
and 45 companion exclusions. UTMOST-NS still requires its combined timing
inputs. No further observed run is queued by this closeout.

## Record closeout

The canonical master is updated after each new observed result and receives
four additional work-log entries for the diagnosis, acceptance, execution and
source closeout. Historical searches, failed attempts, operator notes and
candidate grades remain preserved. Verification is saved in
`results/research/ipta-hold-review-20260909/preservation-check.json`.
The continuation archive and its file verification are recorded in
`results/observed/ipta-hold-release-20260909/backup-receipt.json`.
Monitoring is paused at closeout. Code, workbook and evidence remain private.
