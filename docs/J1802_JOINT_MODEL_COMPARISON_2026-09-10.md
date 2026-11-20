# J1802-2124 joint orbital/noise comparison — 10 September 2026

**The bounded comparison is complete and J1802 remains on hold. No model is
ready for calibration.** Noise and orbital structure trade against each other;
the preferred noise slope reaches opposite grid edges depending on the orbital
treatment. Adding the literature-constrained Shapiro delay provides little
improvement in this local comparison. Flexible orbital harmonics improve the
fit but exceed the checked orbital-shift domain and reduce prospective signal
information. No observed planet-period scan or calibration ran.

## Fixed scope and inputs

This successor uses the preserved 126-TOA/126-DM J1802 preparation, including all
66 timing columns, original model parameters and phase exclusions. No previous
result or adequacy report is changed. The scope was saved before this comparison:

- 57 covariance choices: the released covariance and 56 red alternatives with
  seven RMS values (0.125–8 microseconds), eight slopes (0–6), and 64 Fourier
  pairs covering the prospective search band.
- Three orbital treatments: the released Shapiro omission, nine physical Shapiro
  stress scenarios, and ten freely profiled sine/cosine coefficients at inner
  orbital harmonics 3–7. Noise is selected separately for every treatment/scenario.
- Synthetic information checks at 30, 60, 100, 300 and 600 days. These use
  templates only, without scanning observed residuals at those periods.

The physical grid uses companion masses 0.66, 0.78 and 0.90 solar masses and
absolute inclination cosines 0.143, 0.176 and 0.209: marginal medians and plus/minus
three quoted uncertainties from Ferdman et al. The grid is a set of nine stress
scenarios, not their joint posterior or a confidence region. The exact third-and-
higher Shapiro harmonics are evaluated at the saved native orbital phase; the
constant and first two harmonics are excluded because they are already absorbed
in the apparent released orbital parameters. The released PAR is not edited.
[Ferdman et al. 2010, Table 2 and Sections III–IV](https://arxiv.org/html/1002.0514v1).

## Results

Objectives use a common timing-marginalized Gaussian likelihood, including the
covariance determinant. Free orbital harmonics are profiled without an added
model-complexity penalty. Their raw improvement cannot by itself select a model
or establish evidence for a companion. Lower objective is better within this
conditional comparison; values do not give discovery significance.

| Treatment | Best red RMS / slope | Objective improvement over best omitted treatment | Largest local orbital shift |
| --- | --- | ---: | ---: |
| Omitted Shapiro | 2 us / 0 | Reference | 1.335 published sigma |
| Physical Shapiro stress grid | 2 us / 0 | 0.583 | 8.568 sigma in A1 |
| Ten free orbital harmonics | 2 us / 6 | 22.625 | 9.142 sigma in EPS2 |

The best omitted treatment improves the objective by **22.247902** relative to
the released covariance. Its amplitude is now interior to the expanded grid,
but its slope is at the lower boundary. A slope of zero here means a flat
spectrum within a finite Fourier band, not an independently fitted white-noise
or instrument-jitter model.

After reselecting noise, the residual harmonic diagnostic tail for the omitted
treatment rises to **0.093785**. Thus the earlier orbital-structure warning is
not robust to this noise treatment. This does not establish that the new noise
choice is physically adequate: it is a selected boundary solution, not a noise
posterior, and its diagnostic tail is conditional rather than model-selection
adjusted.

Across all nine physical stress scenarios, objective improvements relative to
the best omitted treatment range from **−0.111 to +0.583**. The smallest mass and
largest cosine produce the best case (0.66 solar masses, inclination 77.936 deg).
It still selects a slope-zero boundary and moves A1 by **8.568** published sigma
and EPS1 by **4.641** sigma, beyond the preparation's checked three-sigma domain.
Its residual harmonic tail is 0.109188. These are local linear comparison
results, not a valid replacement nonlinear timing solution or a test refuting
the established physical companion/Shapiro measurement.

Allowing ten free orbital harmonics selects the opposite noise-slope boundary,
**gamma = 6**, and shifts A1, EPS1 and EPS2 by 6.773, 8.164 and 9.142 published
sigma. The fit can allocate structure differently between orbital terms and
noise. A smaller residual is not enough to justify this model, especially when
its shifts leave the checked domain and its slope remains at an edge.

## Cost of flexible orbital terms

At the best harmonic-branch covariance, adding the ten nuisance coefficients
retains the following worst-phase information for a circular outer signal:

| Synthetic period | Information retained | Additional amplitude uncertainty factor |
| ---: | ---: | ---: |
| 30 days | 58.9% | 1.303 |
| 60 days | 46.5% | 1.466 |
| 100 days | 59.8% | 1.293 |
| 300 days | 48.4% | 1.437 |
| 600 days | 74.7% | 1.157 |

Ratios compare the same covariance with and without the extra orbital
coefficients after the original timing projection. They do not include the
additional covariance uncertainty or the selection of noise on observed data.
The factors represent template-information loss, not calibrated detection
probability, mass limits or injected-planet recovery. Flexible orbital removal
has a material sensitivity cost even before such calibration.

## Verification and disposition

The analytic physical waveform agrees with pinned PINT's native exact ELL1H
third-and-higher delay to **8.48e-22 seconds**. Independent full-covariance
calculations reproduce the three selected objective differences within
**2.45e-8**. Original input hashes, all 71 publication-source bindings and the
binary adapter remain unchanged. The prior 19 adapter checks were reused.

The first comparison completed calculations but could not write its result
because the new output parent directory did not exist. That failure and initial
code are retained. Directory creation was moved before calculation and the
same deterministic scope rerun successfully. No search attempt or threshold was
consumed, and no model was regraded to pass.

**Retain J1802's existing preparation hold and calibration block.** The current
comparison does not produce a replacement profile or overwrite the prior
adequacy findings. The omission branch retains a noise-boundary limitation;
physical and free-harmonic alternatives additionally exceed the local orbital
range. None supplies a validated interior joint solution.

Recommend **parking J1802 and prioritizing the four remaining binary holds**
before more implementation. If J1802 is revisited, the named next problem is
white/instrument covariance versus finite-band noise, coupled to a native
nonlinear orbital fit. Another unconstrained widening of the red grid is not
the recommended next step. This report does not execute that further work.

## Evidence and register

[Saved comparison](../results/research/j1802-joint-model-20260910/)
contains the full noise grid, physical scenarios, information checks, scope,
verification, failure record and closeout. Numerical inputs remain in the
original external preparation. New external evidence is under
`RECHERCHE_DATA/j1802-joint-model-20260910`.

`tools/j1802_joint_model.py` runs this comparison with `--data` pointing at the
saved preparation, `--scope config/j1802-joint-model-comparison.json` and a fresh
`--output` path. Use the pinned Intel runtime, single-thread BLAS, `PYTHONPATH=src`
and offline sandbox as in the preparation report. It refuses an existing result.
Inspect the saved output for continuity rather than repeating the analysis.

Four Work log rows record the repaired output failure, comparison, information
loss and closeout. All historical workbook cells are preserved. Counts remain
**783 registered targets, 286 observed identities, 360 search/refinement records
and eight candidate grades**. No worker remains active; no push or release is
included.
