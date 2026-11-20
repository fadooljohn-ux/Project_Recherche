# ELL1 omitted-Shapiro preparation — 9 September 2026

The explicit released-model mode is implemented. J1012+5307 and J1738+0333 both
passed timing/noise preparation. A bounded synthetic leakage assessment supports
advancing J1738 to conditional calibration; J1012 needs a Shapiro model comparison
before treating omission as negligible. No calibration or observed planet search
was executed. This is local development, not a new public release.

## Adapter and preparation

The selection manifest now declares `shapiro_mode`, defaulting to the existing
`fitted` behavior. The new `omitted_in_release` mode requires the original ELL1
PAR to omit Shapiro terms and the imported model to have no free or nonzero M2/SINI.
It does not remove measured terms. Both modes project every actual free binary
parameter with the timing, DM and instrument columns, retaining derivative,
three-sigma local-linearity, rank, orbital-shift and pulse-connection checks.
An independent least-squares calculation also verifies the projected null
likelihood. The previously repaired local PINT derivative remains in use;
the 71 preserved scientific source hashes are unchanged.

| Preparation measurement | J1012+5307 | J1738+0333 |
|---|---:|---:|
| Released wideband TOAs | 624 | 336 |
| Observing-day epochs | 318 | 104 |
| Actual TDB span, days | 5,672.614 | 3,920.253 |
| Prospective outer periods, days | 30–2,000 | 30–1,960.127 |
| Joint design columns / rank | 192 / 192 | 118 / 118 |
| Largest orbital derivative relative error | 2.54e-7 | 1.53e-7 |
| Largest three-sigma Taylor remainder / TOA σ | 2.80e-7 | 6.88e-7 |
| Largest fitted orbit shift / published σ | 0.0585 | 0.0342 |
| Null reduced χ² under released covariance | 1.0608 | 1.0094 |
| Independent null χ² relative disagreement | 4.06e-16 | 2.03e-16 |

J1012 includes fitted PB, PBDOT, A1, A1DOT, TASC, EPS1 and EPS2. J1738 includes
PB, A1, TASC, EPS1 and EPS2. Neither preparation required a retry. These numerical
checks support local model compatibility; reduced χ² alone does not validate
every noise assumption or supply a search false-alarm probability.

## Omitted-delay measurement

The [J1012 optical study](https://academic.oup.com/mnras/article/494/3/4031/5819465)
reports a conservative companion mass of 0.165 ± 0.015 solar masses and inclination
50 ± 2 degrees. The [J1738 mass study](https://academic.oup.com/mnras/article/423/4/3316/1747458)
gives 0.181 (+0.007/−0.005) solar masses and inclination 32.6 ± 1.0 degrees.
The saved configuration takes each central value and the endpoints at three times
the quoted uncertainty: nine Cartesian scenarios per target. This deliberately
simple stress grid is not a joint posterior, confidence region, or continuous
worst-case bound; optical mass and inclination constraints are correlated.

For each scenario the calculation constructs the ELL1 Shapiro delay
`−2 (GM_sun/c³) M_WD ln(1 − sin(i) sin(orbital_phase))` at the actual released
sampling. It places delay in TOA rows and zero in the auxiliary DM rows, then
whitens with the released joint covariance and projects all timing/orbit nuisance
columns. Only this synthetic perturbation is scanned: the tool never loads
`observed.npz`. All prospective frequency cells are included before an annual
mask exists (933 for J1012; 645 for J1738).

| Synthetic leakage measurement | J1012+5307 | J1738+0333 |
|---|---:|---:|
| Central scenario maximum Δχ² | 0.3379 | 0.02009 |
| Largest maximum Δχ² across nine scenarios | 1.2434 | 0.04240 |
| Central / largest projected whitened norm² | 4.698 / 18.258 | 0.1567 / 0.3450 |
| Period of largest scenario peak, days | 120.601 | 149.628 |
| Fitted sinusoid amplitude at that peak, μs | 0.09134 | 0.02224 |

The largest case for each uses its largest mass and inclination grid values.
Independent normalized least-squares projection agrees within 5.5e-12 in whitened
vector norm. Every synthetic periodogram maximum is below the total projected
norm², as required. Raw peak-to-peak delays can reach 4.90 and 2.65 μs, respectively;
the full nuisance projection is essential to interpret the smaller long-period
leakage.

These are deterministic contamination statistics, **not observed candidates,
sigma significances, calibrated thresholds, or planet recoveries**. Synthetic
power also has a cross term with noise or a real signal; a value below a future
threshold would not by itself prove that omission cannot affect a marginal result.
The phase and design are held at the released model, and this check does not
perform nonlinear inference or vary the released noise covariance.

## Next step and operator handoff

J1738 is the stronger next calibration case: leakage remains small over the tested
scenarios. Its threshold, annual mask and sensitivity still need to be calculated.
For J1012, retain the compatible preparation but compare a fixed,
literature-constrained Shapiro model with this omission before committing to an
observed-search model. Its remaining projected delay is not negligible enough to
discard without that comparison. This does not reopen the four measured-Shapiro
nonlinearity holds or authorize a general nonlinear binary fit.

The reproducible preparation commands use external inputs and a fresh directory:

```sh
tools/recherche binary-pilot select --data "$NEW_DATA" --archive "$NG15_ARCHIVE" \
  --inventory "$NG15_INVENTORY" --selection config/ell1-omitted-shapiro-pair.json
tools/recherche binary-pilot prepare --data "$NEW_DATA" --target J1012+5307
tools/recherche binary-pilot prepare --data "$NEW_DATA" --target J1738+0333
tools/recherche ell1-shapiro-leakage --data "$NEW_DATA" \
  --constraints config/ell1-omitted-shapiro-pair.json --output "$NEW_DATA/leakage.json"
```

Use the saved preparations for follow-on work; do not repeat them to update the
register. Selection, constraints, original inputs, resources, adapter, profiles
and orbital phases are hash-bound. The [closeout and evidence](../results/research/ell1-omitted-shapiro-preparation01-20260909/closeout.json)
preserve exact receipts and all 18 scenario measurements. Raw inputs and profile
arrays remain external. The master records two development closeouts and their
different next steps, preserving all 353 Search rows, 279 observed identities,
783 target rows and operator notes. No science process remains active.
