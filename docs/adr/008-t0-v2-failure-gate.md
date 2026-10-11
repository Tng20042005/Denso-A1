# ADR-008: T0-v2 failure-analysis gate and final holdout

- Status: Accepted; negative result recorded
- Date: 2026-10-07
- Protocol freeze SHA-256: `5232deca09ddc0ab1f80ff280e5e03577c5ecee25745721a5fa72139fa3f19e9`

## Decision

The original T0 utility hypothesis is not supported. A diagnosis-only analysis
was run on Paderborn N15_M07_F10 train/dev fault groups, excluding the previous
test groups. It measured RMS, kurtosis, crest factor, Welch PSD band energy,
envelope spectrum, resonance peak/bandwidth, spectral JS/cosine distance, and
signal-only C2ST.

The observed failure was a reproducible distribution mismatch: C2ST ROC-AUC
was 1.0 in every train/dev population; generated kurtosis and crest factor
were about 1.7 pooled standard deviations higher; generated envelope peaks were
about 223–235 Hz versus measured damage around 95–106 Hz; and generated energy
was shifted toward 10–32 kHz.

## T0-v2 boundary

T0-v2 makes only three changes: physics-only 100 Hz/5 kHz defaults, Gaussian
impulse smoothing with width 8 samples, and k≥1 calibration of frequency
anchors from selected training fault groups only. k=0 never reads real fault
signals. Damping, amplitude, modulation, SNR, and severity remain frozen.

The final holdout uses train/validation at `N15_M07_F10` and a new
bearing-/condition-disjoint measured test at `N09_M07_F10` on `K003`, `KI14`,
and `KI16`. No validation or final-test fault group is used for calibration.

## Outcome

The frozen 5-seed E0/E1/E2 run has 40 rows and all public-real, leakage,
budget, training-difference, and calibration audits pass. T0-v2 PR-AUC deltas
are negative for k=1 and k=2 with 95% CIs excluding zero, and k=0 does not
improve. This is recorded as a negative result; T2 and slide/submission
validation remain deferred.
