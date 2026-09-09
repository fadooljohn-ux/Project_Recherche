# J1752-2806 focused review - 9 September 2026

The owner authorized the dedicated report and further review of J1752-2806.
This scope implements the three proposed checks, preserving the consumed
UTMOST batch-04 search, first four-step review and all other pulsars.

1. Jointly fit circular signal and continuous power-law red-noise amplitude
   and slope, separately with the released 12-mode basis and 32/64-mode bases.
   Keep white noise and the existing timing design fixed. Limit the candidate
   period to the first review's +/-10% interval. Use bounded multistart fits
   and a 161-point local period profile with noise refitted at each period.
2. Assess the earlier finite-family statistic under three additional declared
   null generators: released covariance, 64-mode published power law, and the
   best continuous noise-only fit from step 1. Use 512 simulations each and
   reuse the already completed 512 under steeper 64-mode noise. Reselect the
   same eight-member family and original eligible-plus-local period grid in
   each simulation. This checks the earlier diagnostic; it does not calibrate
   the new continuous statistic or establish global FAP.
3. Propagate local period and sine/cosine coefficient uncertainty to the saved
   TPA observations. Use 2,048 deterministic-seed parameter draws for each of
   three noise-basis fits with profile-likelihood period weights and conditional
   Gaussian coefficients. Report conditional power and waveform envelopes,
   not a Bayesian posterior or averaged p-value. These approximations retain
   period/coefficient dependence but not full noise-parameter uncertainty.

Log-amplitude bounds are released value +/-1 dex; spectral index bounds are
[0, 7]. Bounds, seeds, starts, grids and input hashes are saved before fits.
No new blind observed search or broad qualification is authorized. Real errors
may be repaired locally, preserving completed numerical stages. If a parameter
or profile reaches a bound, report it rather than repeatedly widening the work.

Deliver a scientific PDF with method, original and new evidence, figures,
limitations, references and provenance. Update the canonical master and current
J1752 evidence grade while preserving its original assessment manifest. Keep
private; no GitHub push or visibility change is part of this scope. Use the
existing quiet 30-minute heartbeat and pause after verified closeout.

Status: COMPLETE - focused numerical review and six-page scientific report.

## Results

Joint continuous fits retain periods 81.67-81.76 days. Within-basis objective
improvements are 58.42 (12 modes), 9.89 (32), 12.56 (64); selecting the basis
separately under each hypothesis gives 20.94, not a calibrated significance.
The released 12-mode red process has shortest Fourier period 121.65 days and
no explicit component at the candidate period. Broader noise coverage weakens
its distinction from stochastic timing structure. No fitted noise parameter
or local support envelope reaches the declared bounds.

All four declared generators produce 0/512 exceedances of the FIRST review's
finite-family statistic 25.908. Three ensembles are new (1,536 realizations);
one is reused. The per-generator plus-one tail is 1/513 (0.195%). Counts are
not pooled, and these simulations do not calibrate the new continuous-fit
statistic or establish global FAP.

Period/coefficient propagation uses 6,144 local approximation draws. Median
conditional TPA detection power is 31.4%, 22.2%, 25.0% for 12/32/64 modes.
Phase uncertainty broadens across the later TPA span. Confirmation remains
UNDERPOWERED; significance NOT_ESTABLISHED; robustness NOISE_SENSITIVE.
Disposition: INCONCLUSIVE_NOISE_SENSITIVE.

The [dedicated PDF](../output/pdf/J1752-2806_Candidate_Report.pdf) and
[editable manuscript](../output/pdf/J1752-2806_Candidate_Report.md) contain six
pages, three figures, methods, results, limitations and references. Evidence:
`results/research/j1752-focused-review-20260909/`. The master records numerical
closeout, report and current assessment while preserving earlier manifests.
Monitoring is paused after verified closeout. No new search is authorized.
