# Gate G2 reproduction report

## Decision

Gate G2 **passes the frozen acceptance criteria, pending review**. Injection
work remains unauthorized until this report is reviewed and merged.

## What was reproduced

PINT 1.1.5 loaded the 433 released wideband TOAs for PSR J1744-1134 using the
release clock files, DE440, TT(BIPM2019), the fixed release noise model, 169 DMX
parameters, and the ten released base fit parameters. The released
`WidebandDownhillFitter` configuration was run with a 20-iteration cap.

All 179 fitted parameter values remained unchanged. The recomputed weighted
TOA RMS was 0.940689 microseconds before and after the fit. Recomputed
wideband chi-squared was 734.608063 before and after the fit, compared with
734.621234 stored by PINT 0.9.3 in the release model. Updated parameter
uncertainties differed by at most 0.0505 percent; the largest change was F1.

## Acceptance results

| Criterion | Result |
|---|---|
| Released configuration and free-parameter set | Pass |
| Fitter convergence | Pass |
| 179 parameter values within 3 sigma or 64 ULP | Pass; no failures |
| Weighted RMS within 5 percent | Pass; 0 percent difference |
| Material warnings dispositioned | Pass; no unexpected warnings |
| Runtime below 60 minutes | Pass; 5.67 seconds total |
| Peak memory below 16 GiB | Pass; 245.5 MiB |

The two release-clock override warnings are intentional. Two PINT 1.1.5
`toa_noise_params` warnings refer to a covariance-matrix axis label that the
fitter tries to treat as a timing-model parameter while updating uncertainty
metadata. The parameter update is skipped for that non-model label; all 179
actual model parameters and their uncertainties are present in the recorded
comparison.

## Interpretation limits

The public archive contains only the final post-fit J1744-1134 wideband model,
not an earlier or deliberately displaced parameter model. This is therefore a
strong environment and idempotence check, but it does not demonstrate
convergence from an independent starting solution.

The component whitening diagnostics also require caution. The 433 DM
residuals are consistent with a unit-normal distribution under both recorded
tests (KS p=0.960; Anderson-Darling p=0.995). The 433 TOA residuals are not:
their whitened mean is 0.971, KS p is approximately 3.27e-64, and the
Anderson-Darling p-value underflows to zero. Normality was explicitly
descriptive rather than a frozen G2 acceptance criterion, so this does not
reverse the gate result. It does mean Stage C must retain the matched-null C0
control and must not attach Gaussian false-alarm or discovery significance to
periodic diagnostics.

## Provenance and execution history

The authoritative external record is
`run_records/g2_refit_20260809T014352Z.json` under `RECHERCHE_DATA_ROOT`; its
SHA-256 is
`a3e722a85355f7d9e0f5a95a85a5e5b50fb4eab3dbde9064a91a1bc637046d28`.
The complete parameter table, PINT log, and post-fit model remain outside Git.

The first execution reached the diagnostic recorder but did not create a gate
record because PINT returned a one-element Anderson-Darling p-value array
despite a scalar type annotation. A second development pass succeeded. The
authoritative third pass added separate TOA and DM whitening diagnostics. No
fit setting or acceptance tolerance changed between these executions.

## Review disposition

- Gate result: **pass**.
- Review status: **pending**.
- Injection authorization: **false**.
- Next authorized action after review: run frozen C0 first, then C1-C3 only if
  C0 establishes the matched-null baseline expected by the protocol.
