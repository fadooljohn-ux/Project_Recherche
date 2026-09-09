# Result scorecard convention

Every completed Project Recherche phase reports the following scorecard. A
phase passes only when every hard-gate row passes; diagnostic rows never rescue
a failed hard gate.

| Area | What it tests | Hard gate |
|---|---|---|
| Protocol control | The executed case and criteria match a pre-run freeze. | Yes |
| Injection integrity | The requested waveform was applied accurately without changing the TOA count. | Yes for injected controls |
| Ordinary refit | The release timing fit completes and exposes signal transfer or absorption. | Yes |
| Frequency recovery | The preregistered injected frequency is compared with its matched-null comparator. | As frozen for the case |
| Joint recovery | The compatible physical-signal model measures the frozen amplitude and phase. | As frozen for the case |
| Independent cross-check | A methodologically distinct covariance calculation agrees with the primary solver. | Yes when specified |
| Warning hygiene | Every material warning is absent or explicitly fails the gate. | Yes |
| Reproducibility | Inputs, environment, code/config freeze, and external outputs have verified hashes. | Yes |
| Resource envelope | Runtime, memory, and storage remain within the pilot caps. | Yes |
| Scientific authorization | The result explicitly states which later cases, if any, may proceed. | Yes |

Scorecard outcomes use **PASS**, **FAIL**, **BLOCKED**, or **DIAGNOSTIC**. The
overall outcome is never an average: one failed hard gate fails the phase.
Whether a recovery row is a hard gate or diagnostic must itself be frozen
before the run. A diagnostic result cannot rescue a failed hard gate, and a
weak diagnostic recovery is not automatically an execution failure.
