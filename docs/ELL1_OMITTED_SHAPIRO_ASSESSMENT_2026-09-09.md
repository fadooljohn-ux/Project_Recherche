# ELL1 models without fitted Shapiro terms — 9 September 2026

The owner authorized the next practical assessment following binary expansion 02.
This review reconciles all 14 missing-parameter exclusions with their pinned
NG15 PAR metadata and companion literature. It does not implement the extension,
prepare timing residuals, calibrate thresholds, or launch searches.

## Finding

Five targets are reasonable candidates for a separate conditional adapter branch:
two with optically established white dwarfs and three with likely white-dwarf
companions. Start development with J1012+5307 and J1738+0333. They combine the
strongest companion classification with the longest released coverage in this set.

| Priority | Pulsar | Companion evidence | Released TOAs | Released span, years | Prospective period range, days |
|---|---|---|---:|---:|---:|
| 1 | J1012+5307 | Optical white dwarf | 624 | 15.53 | 30–2,000 |
| 2 | J1738+0333 | Optical white dwarf | 336 | 10.73 | 30–1,960 |
| 3 | J1125+7819 | Likely white dwarf | 206 | 6.30 | 154–1,150 |
| 4 | J0509+0856 | Likely white dwarf | 66 | 3.56 | 49–651 |
| 5 | J0557+1551 | Likely white dwarf | 47 | 4.57 | 48–834 |

Counts and spans above are NTOA/START/FINISH summaries from the pinned PAR files,
not a fresh TOA ingestion. Period ranges apply the existing max(30 days, ten inner
periods) and min(2000 days, half-span) rules; they are prospective, not frozen grids.
None is yet declared timing/noise compatible or calibrated.

Primary companion evidence:
[J1012 optical analysis](https://arxiv.org/abs/2004.02901),
[J1738 spectroscopy](https://arxiv.org/abs/1204.3948),
[J1125 discovery and optical limits](https://par.nsf.gov/servlets/purl/10315467),
[J0509 discovery analysis, section 3.2](https://arxiv.org/abs/1906.05071), and
[J0557 discovery analysis](https://arxiv.org/abs/1501.03746).
The latter three remain likely identifications, not equivalent to optical mass
measurements. J0509's discovery analysis discusses a likely low inclination and
undetected Shapiro delay. This supports investigating its released model; it does
not establish that omitted effects are negligible in our search.

## Reconciliation of all 14 cases

- Five recommended for conditional-branch preparation, listed above.
- J0406+3039 has the same five fitted core parameters and adequate nominal span,
  but this bounded literature check did not establish its companion classification.
  Retain it as a classification gap, not as a confirmed white-dwarf system.
- J0023+0923, J0636+5128, J1705−1903 and J2214+3000 use fitted orbital-frequency
  polynomials (FB0 and higher derivatives). PB being absent is a different
  parameterization, not corrupted data. They need a separate adapter assessment.
- J0610−2100, J1745+1017 and J2234+0944 use PB but belong to the
  [black-widow sample](https://adsabs.harvard.edu/pdf/2013IAUS..291..127R).
  Companion-related timing structure is outside this detached-white-dwarf step.
- J1719−1438 is an existing known-companion benchmark. Its NG15 coverage is not
  a new isolated or ordinary white-dwarf pilot identity; preserve the prior record.

## Smallest useful implementation

Inspection of `tools/binary_wideband.py` finds an unconditional requirement for
seven free parameters, including M2 and SINI. All five recommended PARs omit those
two terms entirely while retaining fitted PB, A1, TASC, EPS1 and EPS2 with positive
uncertainties. This is a published model choice, not the same failure as the four
systems with measured but nonlinear SINI uncertainty.

A bounded extension should:

1. Add an explicit profile mode for a released ELL1 model with Shapiro terms
   omitted. Check the original PAR and imported model, preserve its fitted/fixed
   choices, and project all actual free orbital derivatives. Keep the current
   fitted-Shapiro branch and its checks intact. Do not turn a nonlinear hold into
   an omitted-term model by deleting measurements.
2. Retain the joint timing/DM/noise preparation, derivative and local-linearity
   checks for the included parameters, pulse connection and independent likelihood
   check. Report thresholds and sensitivity as conditional on the released model.
3. Use J1012 and J1738 for one bounded assessment of omitted-Shapiro leakage,
   using published companion constraints and their actual sampling. Refit/project
   existing nuisance terms when measuring leakage; the full raw Shapiro amplitude
   alone is not the long-period contamination. Recalibrate only after a justified
   model change. No unconstrained new mass/inclination fit is needed for this check.

The physical gravitational delay does not vanish because M2 and SINI are absent
from a PAR file. Parts can be absorbed by fitted orbital parameters; irregular
sampling can transfer remaining structure into other periods. The proposed mode
must state that limitation and measure its relevance before observed execution.
It is a targeted extension of the existing ELL1 ingestion, not full nonlinear
binary inference. The actual compatibility and sensitivity cost remain unmeasured.

## Closeout

[Machine-readable assessment](../results/research/ell1-omitted-shapiro-20260909/assessment.json)
records all 14 dispositions, hashes, metadata and references. The master receives
one assessment work-log entry and updated next-step information for these targets.
All 353 existing Search rows, 279 observed identities and 783 registered targets
remain unchanged. No scientific runtime source was changed, no job is active,
and this local assessment has not been published.
