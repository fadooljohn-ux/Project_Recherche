# UTMOST DR1 bounded preparation — 9 September 2026

The owner authorized adapter and noise-model preparation on a small representative
subset, with no observed searches and binary support deferred. This preparation
is complete for four isolated pulsars and 873 observations. No periodic template
was applied to the observed residuals, no search result was produced, and no
execution freeze or launch intent was created. Recherche remains private.

## Selected data and results

The selection was fixed before importing residuals: two released white-noise
models, two red-noise models, and one fully pulse-numbered dataset. All four
passed the saved coverage screen and had no previous Recherche observed search.
This is a representative adapter subset, not a discovery-yield ranking or a
claim that these pulsars have never appeared in other planet searches.

| Pulsar | Released noise | TOAs | Null reduced chi-squared | Conditional threshold | Eligible / total grid cells | Median worst-phase 95% amplitude |
|---|---|---:|---:|---:|---:|---:|
| J1807-0847 | White | 74 | 1.010 | 22.6192 | 199 / 204 | 47.6 microseconds |
| J0134-2937 | White | 198 | 0.996 | 22.4664 | 184 / 189 | 50.2 microseconds |
| J1453-6413 | White + red | 234 | 1.029 | 22.5493 | 193 / 197 | 22.9 microseconds |
| J1224-6407 | White + red | 367 | 0.979 | 22.5392 | 192 / 196 | 26.7 microseconds |

The threshold is the existing circular GLS statistic. Calibration uses a shared
conditional 1% allowance for four prospective 30–400-day searches, oversampling
5, and 4,096 independent fixed-noise null realizations per target: 16,384 total.
The analytic sensitivity is the median across eligible frequency cells of the
worst-phase on-grid amplitude giving 95% detection probability under that model.
It is not a planet mass, an observed detection, or an empirical 95% recovery rate.
Twelve deterministic injected-template checks at 60, 150 and 250 days recovered
the input sine/cosine coefficients within the declared numerical tolerance.
These are development checks, not another formal qualification.

Timing projection excludes 4–5 cells per target, with the mask calculated from
each target's actual sampling and released timing design. Per-cell masks and
sensitivity, null maxima, calibration receipts and input hashes are saved in
`results/research/utmost-preparation01-20260909/`. Source observations, prepared
residuals and covariance profiles remain outside Git under
`../Project Recherche Data/utmost-preparation01-20260909/`.

## Adapter and actual repairs

`tools/utmost_prepare.py` is a small source-specific adapter using the existing
calibration runtime. It has only `prepare` and `calibrate` actions. The qualified
`src/` solver was not modified.

The adapter preserves the pinned UTMOST release, inclusive START/FINISH selection,
Molonglo observatory, DE430 ephemeris and TT(TAI) clock convention. DE430 was
downloaded from NASA JPL and hashed separately; the existing qualified resource
bundle was not changed. Scientific preparation executes offline using the pinned
Intel Python environment.

J1807-0847 and J0134-2937 omit UNITS with EPHVER 5. Tempo2 initializes these
models in SI/TCB units; the adapter explicitly supplies TCB and permits PINT's
conversion to TDB. The two red-noise models explicitly declare TDB. The adapter
does not silently treat all four as TDB. Released spin and position columns plus
an offset are projected; fixed dispersion and solar-wind parameters are retained.
The phase arcs are 0.0027–0.0079 cycles. J1224-6407's 367 pulse numbers additionally
agree with the calculated integer phase up to one constant offset.

Direct PINT import ignores `TNGlobalEF` and `TNGLobalEQ`. The adapter constructs
the white variance explicitly as `(EFAC * TOA_error_seconds)^2 + 10^(2*log10_EQUAD)`.
This follows Tempo2's implementation, which adds EQUAD after EFAC scaling. The
two red-noise targets retain their released amplitude, spectral index and ten
Fourier modes using the established Recherche covariance implementation.

The release's `mo2gps.clk` has an out-of-order pair near MJD 58106. PINT rejected
the first preparation attempt. Tempo2's loader warns but retains the order; its
binary-search interpolation therefore differs from simply sorting the table.
The adapter replays that calculation at the bound observation MJDs and TZRMJD,
writing a target-specific sampled clock. The original file is preserved. This
is compatibility with the published calculation, not an independent correction
of the physical observatory clock. The sampled file must not be reused for other
TOAs. A second attempt exposed an endpoint precision mismatch; retaining the
original clock's coverage endpoints repaired it. Both failed attempts are retained
and entered in the master work log. All four final imports then completed.

## Single-band noise policy and limits

UTMOST's small changes around 835 MHz do not supply useful independent frequency
coverage. The released white/red covariance is treated as **total timing noise**,
conditional on fixed published hyperparameters. No independent dispersion or
scattering time series is inferred, and no free DM parameter is added to each
one-band epoch. Such columns could absorb the prospective orbital signal.

The null-model goodness-of-fit values are a useful import and scaling check.
They do not prove that the residual process is stationary, Gaussian or
achromatic. Noise hyperparameter uncertainty, unmodeled frequency-dependent
effects, clock uncertainty, off-grid loss and eccentric/multiple companions are
not included in the stated sensitivity. A future compelling feature requires
the standing candidate deep review and, where available, independent telescope
or frequency evidence.

The subset supports proceeding to a separately directed freeze and bounded
launch of these four datasets. It does not qualify the other 82 coverage
candidates automatically. All 86 remain unsearched in UTMOST; four now have
conditional preparation and 82 remain unprepared. Binary and glitch extensions
remain outside this work.

## Operation and evidence

```sh
tools/recherche utmost-prepare prepare
tools/recherche utmost-prepare calibrate
```

Optional `--target` restricts either action to one of the four saved selections.
Completed preparation is reused only for the same adapter version. Calibration
uses the existing input-bound cache. These commands expose no observed-search
action. Consult the master first; do not recreate the completed preparation to
refresh documentation or workbook entries.

The canonical workbook records four conditional preparations, one calibration
closeout, two retained failures and the source-queue boundary. Its historical
search rows and operator notes are preserved. The overview still reports 221
observed targets and 252 search/refinement records; no UTMOST observation has
been counted as searched.

Primary conventions used:

- [UTMOST DR1 pinned release](https://github.com/Molonglo/TimingDataRelease1/tree/e6c36c26b54749d89d29c148da98f0919b3ce5a8).
- [Tempo2 global-noise preprocessing](https://github.com/ipta/tempo2/blob/master/preProcess.C).
- [Tempo2 time-unit initialization](https://github.com/ipta/tempo2/blob/master/initialise.C) and [EPHVER handling](https://github.com/ipta/tempo2/blob/master/preProcessSimple.C).
- [Tempo2 clock-table lookup](https://github.com/ipta/tempo2/blob/master/tabulatedfunction.C).
- [NASA JPL DE430 kernel](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de430.bsp).

Downloaded convention files and the kernel have SHA-256 provenance in
`results/research/utmost-preparation01-20260909/conventions.json`.
