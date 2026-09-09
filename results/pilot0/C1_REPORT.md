# C1 strong positive-control report

## Decision

C1 **fails its frozen recovery gate, pending review**. C2 and C3 remain
blocked. This is an informative validation failure, not a failed scientific
detection: the injection was applied correctly, but neither frozen recovery
path is adequate for later scientific use in its present form.

## Injection integrity

The injected circular delay had a 100-day period, 20-microsecond amplitude,
phase 1.0471975512 radians, and reference epoch MJD 56078.0 TDB. It was added
to all 433 authoritative high-precision arrival times. The largest application
error was 0.0000084 microseconds, well below the frozen 0.001-microsecond
tolerance. The injection and ordinary 179-parameter refit completed without a
software or resource failure.

## Blind recovery failure

After the ordinary release-model refit, the exact 100-day residual sinusoid was
stronger than the C0 exact-frequency baseline but was not the strongest peak in
the frozen search.

| Quantity | C0 null | C1 result |
|---|---:|---:|
| Exact 100-day power | 0.01457 | 0.14937 |
| Exact 100-day fitted amplitude | 0.1651 us | 5.7655 us |
| Exact 100-day diagonal delta chi-squared | 49.29 | 66,673.43 |
| Strongest-peak period | 30.4484 d | 30.0962 d |
| Strongest-peak power | 0.18097 | 0.24413 |

The strongest C1 peak was 132.96 independent Fourier bins from the injected
frequency, so the frozen one-bin criterion failed. After phase-aware C0
subtraction, the blind residual amplitude was 5.7860 microseconds: 28.93% of
the injected amplitude. The ordinary timing-model refit therefore absorbed or
redistributed approximately 71.07% of this injected waveform.

The 30.096-day boundary peak must not be interpreted as another signal. The
blind periodogram uses diagonal scaled-TOA uncertainties, does not include the
released correlated red-noise covariance, and has no calibrated false-alarm
probability. C1 demonstrates that “strongest residual peak recovers the
injection” is not a reliable hard gate after a full timing refit.

## Joint-grader invalidation

The frozen joint grader added a fixed-frequency PINT WaveX sine/cosine pair to
the full timing fit. Numerically, phase-aware subtraction of the same-run C0
fit recovered 20.00016 microseconds and a phase error of only 0.000019 radians.
That numerical result is **not accepted as a valid recovery**.

PINT 1.1.5 emitted 15 material warnings that Wave, WaveX, and PLRedNoise cannot
be used together because they model the same effect. The release timing model
already contains PLRedNoise. Consequently, the chosen joint component violates
the model's compatibility constraint, and the frozen warning criterion failed.
The near-perfect amplitude is retained for diagnosis only and must not be used
as scientific support.

## Resource and integrity checks

- Ordinary injected-data refit convergence: pass.
- Same-run C0 and C1 WaveX numerical convergence: pass, but scientifically
  invalidated by the component conflict.
- TOA count: 433, unchanged.
- Ordinary injected-data weighted RMS: 10.8058 microseconds.
- Ordinary injected-data reduced chi-squared: 320.786.
- Total runtime: 21.02 seconds.
- Peak memory: 250.8 MiB.
- Unexpected material warnings: 15 WaveX/PLRedNoise incompatibility warnings.

The authoritative full record is
`run_records/c1_positive_control_20260809T021523Z.json` under
`RECHERCHE_DATA_ROOT`, SHA-256
`6e228f1d074d19324f2e605a79be8fdce1b26e0af5aeb3ea4ba99e3e3271a9fe`.
The run used Pixi lock SHA-256
`7412baa7d224dfdc419066b706f27257684931df9a0ad0f57949e1fe31cf68c8`.

## Review disposition and corrective gate

- C1 result: **fail**.
- Review status: **pending**.
- C2/C3 authorization: **false**.
- C1 rerun authorization: **false** under the current freeze.

The next action after review is a new, separately frozen C1-R1 corrective
experiment. It should replace WaveX with a deterministic circular-delay
component that is compatible with the release PLRedNoise model and replace the
global strongest-peak requirement with preregistered recovery tests at the
injected frequency. The corrected method should be independently cross-checked
against a covariance-aware linear recovery before another authoritative run.
C2 and C3 must not proceed until C1-R1 passes and is reviewed.
