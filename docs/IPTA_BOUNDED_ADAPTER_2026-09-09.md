# IPTA J1721−2457 bounded adapter — 9 September 2026

**TIMING_NOISE_COMPATIBLE.** The adapter retains all 150 released arrivals and
reproduces the released timing statistics. Preparation is complete for this
target. No threshold calibration, sensitivity injection or planet search ran.

The owner authorized bounded adapter development and the subsequent timing/noise
comparison after the [compatibility review](IPTA_DR2_COMPATIBILITY_2026-09-09.md).
The scope remained J1721−2457. J2010−1323, binary support and the deferred
J1752−2806 NS follow-up were not advanced.

## Implementation

`tools/recherche ipta-prepare` is the supported preparation entry point. It runs
the coordinator in Recherche's pinned Intel environment and invokes a separate,
locked Intel TEMPO2/libstempo runtime to calculate timing quantities. Both Python
runtimes retain a 63-bit long-double mantissa. No qualified scientific source or
root environment dependency was changed.

The new files are `tools/ipta_prepare.py`, `tools/ipta_tempo2_export.py` and
`tools/ipta_tempo2_reference.C`. The reference plugin calls TEMPO2's own timing,
Fourier-basis and noise-prior functions without fitting or searching. The Python
adapter assembles the corresponding noise covariance independently from those
exported covariance matrices. This is a comparison of two code paths using the
same timing engine, not independent evidence of an astrophysical signal.

The separate dependency definition and lock are saved in `tools/tempo2_runtime/`.
The installed runtime lives outside Git at
`../Project Recherche Data/ipta-adapter01-20260909/runtime/`. It pins libstempo
2.5.1 and the conda-forge TEMPO2 package 2025.02.1. That package's executable
reports the internal version string `2025.01.2`; package and binary identities
are recorded separately. DE436 and BIPM2015 were supplied by this runtime.

The original May 2019 TDB model, active TIM includes and release clock files are
preserved. The derived model retains T2CMETHOD TEMPO, DE436, TT(BIPM2015), all
released coefficients and all 150 arrivals. It adds `DM_SERIES POLY` to preserve
the historical DM2 coefficient meaning. The model file's GitLab history dates
it to 2 May 2019, before TEMPO2 changed its default from polynomial to Taylor
coefficients in June 2020. This adjustment is supported by
[TEMPO2's preprocessing source](https://bitbucket.org/psrsoft/tempo2/src/2025.02.1/preProcess.C)
and [parameter reader](https://bitbucket.org/psrsoft/tempo2/src/2025.02.1/readParfile.C).

White noise uses EFAC-scaled measurement variance plus EQUAD variance outside
EFAC. Red and DM covariance retain 74 sine/cosine pairs each, the released
START/FINISH frequency span, barycentric radio frequencies, DM constant and
TEMPO2's historical normalization (`3.16e7` seconds in its amplitude factor,
`365.25` days in the frequency pivot). These conventions were checked against
the library's own [noise constraints](https://bitbucket.org/psrsoft/tempo2/src/2025.02.1/constraints_nestlike.C)
and [Fourier derivatives](https://bitbucket.org/psrsoft/tempo2/src/2025.02.1/t2fit_nestlike.C).
This target has no released ECORR term; it does not validate ECORR support for
other IPTA targets. `TNSubtractDM` does not replace the raw residual array with
a noise-subtracted series; the adapter uses the full covariance instead.

## Timing and noise comparison

Final evidence is `J1721-2457/attempt03/receipt.json` under the external data root.
The repository retains a copy at
`results/research/ipta-adapter01-20260909/preparation-receipt.json`.

| Check | Measured result |
|---|---:|
| Retained arrivals | 150 / 150 |
| Weighted residual RMS | 17.74333565 µs; released 17.743 µs |
| Reduced chi-square after linear timing projection | 0.982057925; released 0.9821 |
| Residual difference from direct TEMPO2 export | 0 at exported precision |
| Barycentric time difference | 0 at exported precision |
| White uncertainty maximum relative difference | 2.26 × 10⁻¹⁶ |
| Red covariance relative matrix difference | 6.94 × 10⁻¹⁶ |
| DM covariance relative matrix difference | 1.00 × 10⁻¹⁵ |
| Timing design rank | 13 / 13 |
| Normalized whitened design condition number | 423.22 |
| Residual phase span | 0.06544 cycles |
| Largest representative derivative relative difference | 1.05 × 10⁻⁵ |

The finite-difference checks cover spin frequency, right ascension, DM2 and an
instrument jump. TEMPO2's matrix describes residual corrections, so it is
checked against the negative residual derivative. Only temporary in-memory
parameter perturbations were made and then restored. The chi-square check uses
a linear GLS nuisance projection; no nonlinear timing refit or noise-parameter
optimization was performed. No frequency grid or periodogram was evaluated.

The runtime used date-appropriate GPS/GPST or GPS/UNSO clock paths followed by
UTC, TAI and TT(BIPM2015). The final run contains no missing-clock or fallback
approximation warnings. Some unused release clock tables have out-of-order
entries and produce parser warnings during discovery; those tables are not on
J1721's Nançay/Westerbork correction paths. Their original bytes are preserved.

## Diagnosed repairs and retained attempts

- Early probes hit a legacy Fortran ephemeris-reader crash on a path containing
  spaces. A dedicated space-free runtime alias fixes this without relocating or
  altering the original project.
- The modern DM2 default was made explicitly historical as described above.
- Attempt 01 retained the initial timing/noise exports and derivative diagnosis.
- Attempt 02 failed during preparation because a reduced clock directory lacked
  legacy UT1 and alternate date-dependent GPS routes. It is preserved with its
  failure receipt. Restoring the complete pinned runtime clock set, with the
  release's overrides, resolved the error in attempt 03.

No scientific search failed or was rerun. The canonical workbook receives a
development record, the failed preparation record, the successful comparison
record and the next-step record. Existing Search and Candidate grade rows remain
unchanged. Prior result files, qualified source and the root Pixi lock are checked
against the saved pre-work hashes in the closeout preservation receipt.

## Prepared outputs and next step

The final attempt contains `arrays.npz` with barycentric times, covariance, the
13-column timing design and its instrument/dispersion baseline; `observed.npz`
holds residuals separately. Reference exports, logs, resource hashes and checks
are retained alongside them. The arrays pass the existing Recherche calibration
input validator, but no calibration profile with an approved period policy has
been frozen yet.

**Next: calibrate J1721−2457's threshold, annual mask and sensitivity for a
specified search range.** A subsequent observed launch should consume a frozen
package once. This preparation result does not establish a planet signal or the
noise model's validity outside the supplied data and fixed released parameters.

To inspect the completed check, read `results/research/ipta-adapter01-20260909/closeout.json`.
Do not rerun preparation merely to refresh the workbook. The operator command
creates a new, retained attempt when a real adapter/input change warrants it:

```sh
tools/recherche ipta-prepare --data '../Project Recherche Data/ipta-adapter01-20260909'
```

On a replacement machine, restore the pinned public intake and target copy first,
copy `tools/tempo2_runtime/pixi.toml` and `pixi.lock` into that external data root's
`runtime/` directory, then run `pixi install --locked --manifest-path` against
that copied manifest. Preparation uses the installed runtime; it does not install
dependencies or access the network. Binary timing, additional noise components
and targets other than this 150-arrival J1721 dataset are explicitly unsupported
by this bounded adapter.
