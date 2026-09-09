# Targeted annual solver diagnosis

Owner authorization: “Proceed with the targeted annual solver diagnosis before
advancing toward operational release.” Starting point: closeout commit `7845f85`.

## Findings and retained repair

The signal delay evaluates sine/cosine at the delay-corrected emission time, but
its analytic CSSIN/CSCOS derivatives previously used the uncorrected time. This
is a concrete forward-model/Jacobian mismatch. PINT calls these derivatives
without passing the accumulated delay, so the component now obtains the delay
entering itself from its parent model, excluding its own contribution. Detached
component calls use the explicitly supplied delay. The signal waveform is unchanged.

Four finite-difference regressions cover both coefficients, nonzero accumulated
delays, and the attached-model call path. The signal component is now included
in the current implementation digest. The old formal execution freeze remains
unchanged at its original release; this modified development code is not that
qualified release.

## Numerical evidence

A separate fixed 365.25-day, phase-pi, 5-microsecond fixture uses case ID
`recherche-dev-annual-diagnosis-20260908-pi` and seed `8183475920083870252`, disjoint
from the formal inventory. The consumed formal case was never rerun.

At the starting model, the normal-equation condition number was about
4.73e11. Direct augmented and whitened full-covariance least-squares updates
agreed to roughly 2e-9 microseconds; the native normal-equation update differed
by roughly 9e-5 microseconds. Ill-conditioning is real, but that linear algebra
comparison alone does not account for the complete formal discrepancy.

The explicit-covariance audit always runs all 20 iterations; its finite return
value is a linearized chi-square, not a convergence declaration. A trace on the
separate fixture found a late-iteration amplitude span of 0.02107 microseconds,
more than the 0.01-microsecond audit limit, while chi-square changed only slightly.
The primary fitter instead stops on chi-square improvement and retains its best
model. Agreement in this nearly unidentifiable annual direction is sensitive to
iteration selection and numerical precision.

| Separate phase-pi fixture | Amplitude disagreement, microseconds |
|---|---:|
| Original implementation | 0.00425015 |
| Derivative correction alone | 0.00651454 |
| Experimental convergence-limited audit | 0.0000768733 |

The derivative repair reduced the residual signal-parameter step by more than
an order of magnitude, but did not by itself improve the final inter-solver
amplitude disagreement on this fixture. It is retained because the Jacobian
must differentiate the actual forward model, not because it makes a gate pass.

## Rejected experiment

A bounded prototype applied the existing 0.01 chi-square convergence tolerance
to the explicit-covariance audit and retained its best evaluated model. It
improved the phase-pi fixture but failed the other annual development fixture:
0.01338506 microseconds of amplitude disagreement, above the unchanged 0.01
limit. The prototype was removed. The production solver implementation,
iteration behavior and scientific limits remain unchanged.

The failed development attempt and the exact rejected source are preserved in
external evidence. Its source hash matches that attempt's manifest. This result
rules out treating a simple stopping-rule change as a reliable fix.

## Validation and disposition

The retained code passed 76 focused tests in 1.83 seconds. The supported
`tools/recherche develop` run `pilot2-ioc-dev-jacobian-final-20260908` passed all
four fixed fixtures, with 8 primary fits, 2 solver audits and zero offline-resource
violations, in 215.821 seconds.
The final annual amplitude disagreement was
0.00311521 microseconds.

All three development terminal inventories have exact file-set, size and SHA-256
parity, including the rejected attempt. The 344 formal case artifacts, two formal
stage results and four bound terminal artifacts remain unchanged and verify.
Machine-readable closeout: `results/qualification/annual-solver-diagnosis.json`.

The formal 344-case result remains FAIL. These observations identify a derivative
defect and demonstrate annual numerical sensitivity; they do not establish a
single sufficient cause of the historical case's failure or a counterfactual
formal PASS. Operational release and another formal attempt have not started.

The remaining focused engineering question is how to make the independent
solvers numerically consistent in the annual weakly constrained direction.
A future repair must succeed on both retained annual development fixtures;
relaxing the agreement gate or rerunning formal cases until they pass is not
supported by this diagnosis.

Detailed evidence: `../Project Recherche Data/annual-diagnosis-20260908/`.

Backup: `../Recherche Recovery/20260907T223404/annual-solver-diagnosis-20260908.tar`.
All 71 archived files matched their exact content hashes and file set.
