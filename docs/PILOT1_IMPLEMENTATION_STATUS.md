# Pilot 1 implementation status

- **Phase:** P1-A detector implementation and noninjected numerical preflight.
- **Outcome:** pass.
- **Execution state:** calibration remains unauthorized; zero Pilot 1 synthetic
  realizations have been generated and no global observed-residual search has
  been run.

## Implemented research controls

The implementation now provides a covariance-whitened generalized
least-squares circular scan over a deterministic frequency grid. It uses the
complete 866 by 866 released wideband covariance, projects the 180-column
timing design, and precomputes the projected signal workspace so later case
scans can reuse the expensive matrix work.

The same module provides the frozen covariance Gaussian generator, a complete
deterministic case inventory, disjoint per-case seeds, lowest-SHA-256 audit
selection, the conservative nearest-rank threshold estimator, ensemble
whitening diagnostics, and a resumable external artifact ledger that refuses
inventory or implementation drift.

The ensemble-correlation gate is implemented as the maximum absolute pooled
post-whitening lag correlation over lags 1 through 32. It uses the complete
whitened vector at every lag. A raw maximum over all 866-coordinate sample
correlations was rejected before execution because its multiple-comparisons
behavior would make a 0.10 threshold fail routinely even for independent
Gaussian draws.

## Preflight findings

The preflight was intentionally allowed to fail before calibration. Its first
attempt caught a material numerical defect: the 180 timing columns carry
different physical units, and a raw-magnitude rank decision retained only two
directions. Normalizing each whitened column before the rank decomposition
restored all 180 directions without changing their projected subspace.

The authoritative preflight then compared the analytic trigger against direct
`ProjectCircularSignal` explicit-full-covariance fits at the predeclared 100
and 365.25-day frequencies. At 100 days, the absolute differences were
0.00000251 microseconds in amplitude, 0.00000723 radians in phase, and 0.000147
in delta chi-squared. At the deliberately near-singular annual point, the
delta-chi-squared difference was 0.00156 and the phase difference was 0.00535
radians, within its separately recorded annual stress tolerance.

The complete three-attempt audit trail and external hashes are recorded in
`results/pilot1/implementation_preflight_summary.json`. Failed attempts were
retained rather than overwritten.

## Boundary and next gate

This implementation does not authorize the null ensemble, sealed evaluation,
injection matrix, or observed-data search. The next change must freeze hashes
for the implementation, inventory, runtime environment, and benchmark
procedure. Only that separate freeze may authorize the first 50-case synthetic
benchmark.
