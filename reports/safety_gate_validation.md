# Safety-gate validation

This is a diagnostic validation of the gate, not a new synthesis experiment. The reference and corruption ladder use measured Paderborn training/validation fault populations only. No final-test population was loaded, and corruption outputs were not used for detector-training utility claims.

## Frozen validation boundary

- Condition: `N15_M07_F10`; train fault groups: `paderborn-bearing-KA04, paderborn-bearing-KA15`; validation fault groups: `paderborn-bearing-KA16, paderborn-bearing-KI04`.
- Protocol SHA256: `1d07f943790646b312be2f427a5cec24c07b25f0b5e6dd7c4dea65f6998fb5d5`; sample count per population: `128`.
- The measured-real comparison is an empirical reference/upper-bound, not a synthetic candidate and not an admission decision.

## 1. Real-vs-real reference

| statistic | measured-real train vs validation | matched train vs train |
|---|---:|---:|
| C2ST ROC-AUC | 0.9977 | 0.5085 |
| PSD cosine similarity | 0.9169 | 0.9967 |
| spectral JS divergence | 0.0230 | 0.0013 |
| envelope cosine similarity | 0.9577 | 0.9961 |
| envelope JS divergence | 0.0088 | 0.0011 |
| envelope peak drift (Hz) | 45.78 | 69.34 |
| nearest-neighbor median ratio | 1.8347 | 1.3003 |
| exact hash overlap | 0 | 0 |

Feature distribution gaps (standardized mean gap; train vs validation):

| feature | train mean | validation mean | standardized gap |
|---|---:|---:|---:|
| rms | 0.3348 | 0.4812 | -0.9622 |
| kurtosis | 4.907 | 5.852 | -0.5843 |
| crest_factor | 5.587 | 6.056 | -0.5457 |

Interpretation: the matched train-vs-train control checks metric noise, while the train-vs-validation comparison measures real bearing/group shift. If the latter is more separable, that is a dataset-relative domain difference—not evidence that the gate should silently treat real data as synthetic. Both comparisons stay outside candidate admission.
The historical absolute C2ST cutoff of 0.95 would reject the group-shift real-vs-real reference, while the matched control passes C2ST/PSD/JS but has an anchor-drift estimate of 69.34 Hz versus the historical 50 Hz cutoff. This is why those cutoffs remain retrospective prototype thresholds and SafetyGate-v1 uses reference-relative calibration.

## 2. Controlled corruption ladder

Each corruption starts from the same measured-real train-fault windows. Levels are diagnostic-only: band-limited noise, frequency-anchor shift, spectral distortion, impulse sharpening and envelope distortion. Full row-level results are in `safety_gate_corruption_ladder.csv`.

| corruption | metric | expected direction | consistent adjacent fraction | Spearman rho | interpretation |
|---|---|---|---:|---:|---|
| band_limited_noise | c2st_excess_over_chance | increase | 0.75 | 0.872 | consistent |
| band_limited_noise | psd_js_divergence | increase | 1.00 | 1.000 | consistent |
| band_limited_noise | psd_cosine_similarity | decrease | 1.00 | -1.000 | consistent |
| band_limited_noise | envelope_peak_drift_hz | increase | 1.00 | 1.000 | consistent |
| envelope_distortion | c2st_excess_over_chance | increase | 0.50 | 0.600 | mixed |
| envelope_distortion | psd_js_divergence | increase | 1.00 | 1.000 | consistent |
| envelope_distortion | psd_cosine_similarity | decrease | 1.00 | -1.000 | consistent |
| envelope_distortion | envelope_peak_drift_hz | increase | 1.00 | 1.000 | consistent |
| frequency_anchor_shift | c2st_excess_over_chance | increase | 1.00 | 1.000 | consistent |
| frequency_anchor_shift | psd_js_divergence | increase | 1.00 | 1.000 | consistent |
| frequency_anchor_shift | psd_cosine_similarity | decrease | 1.00 | -1.000 | consistent |
| frequency_anchor_shift | envelope_peak_drift_hz | increase | 1.00 | 1.000 | consistent |
| impulse_sharpening | c2st_excess_over_chance | increase | 1.00 | 0.975 | consistent |
| impulse_sharpening | psd_js_divergence | increase | 1.00 | 1.000 | consistent |
| impulse_sharpening | psd_cosine_similarity | decrease | 1.00 | -1.000 | consistent |
| impulse_sharpening | envelope_peak_drift_hz | increase | 1.00 | 1.000 | consistent |
| spectral_distortion | c2st_excess_over_chance | increase | 0.75 | 0.900 | consistent |
| spectral_distortion | psd_js_divergence | increase | 1.00 | 1.000 | consistent |
| spectral_distortion | psd_cosine_similarity | decrease | 1.00 | -1.000 | consistent |
| spectral_distortion | envelope_peak_drift_hz | increase | 1.00 | 1.000 | consistent |

The ladder is a sanity check, not a proof of universal monotonicity. Mixed trends are reported as mixed; no severity level is selected using final-test utility.

## 3. Gate diagnostics versus frozen downstream utility

The association table joins only already-frozen candidate configurations for which gate diagnostics and held-out measured-real utility are available. It does not rerun, tune or reclassify any branch.

| method/config | fidelity C2ST | PSD JS | PSD cosine | provenance | novelty | PR-AUC Δ vs E0 | PR-AUC Δ vs E1 | admission |
|---|---:|---:|---:|---|---|---:|---:|---|
| T0 / k=0:E2-E0 | 1.0 | 0.18595946377750283 | 0.5132549458061313 | PASS | UNKNOWN | -0.046313042051280354 | NA | REJECT |
| T0 / k=1:E2-E0 | 1.0 | 0.18595946377750283 | 0.5132549458061313 | PASS | UNKNOWN | -0.05594208707036753 | NA | REJECT |
| T0 / k=1:E2-E1 | 1.0 | 0.18595946377750283 | 0.5132549458061313 | PASS | UNKNOWN | NA | -0.04907025256092821 | REJECT |
| T0 / k=2:E2-E0 | 1.0 | 0.18595946377750283 | 0.5132549458061313 | PASS | UNKNOWN | -0.06518008383196357 | NA | REJECT |
| T0 / k=2:E2-E1 | 1.0 | 0.18595946377750283 | 0.5132549458061313 | PASS | UNKNOWN | NA | -0.07466262337480938 | REJECT |
| T0-v2 / k=0:E2-E0 | NA | NA | NA | PASS | UNKNOWN | -0.019593405337138714 | NA | REJECT |
| T0-v2 / k=1:E2-E0 | NA | NA | NA | PASS | UNKNOWN | -0.15727263887433812 | NA | REJECT |
| T0-v2 / k=1:E2-E1 | NA | NA | NA | PASS | UNKNOWN | NA | -0.15658583854659375 | REJECT |
| T0-v2 / k=2:E2-E0 | NA | NA | NA | PASS | UNKNOWN | -0.25169936052636155 | NA | REJECT |
| T0-v2 / k=2:E2-E1 | NA | NA | NA | PASS | UNKNOWN | NA | -0.25169936052636144 | REJECT |
| T2 conditional-VAE / k=1:E3-E0 | 1.0 | 0.17395187777594392 | 0.5573890189217146 | PASS | PASS | -0.02812315773954983 | NA | REJECT |
| T2 conditional-VAE / k=1:E3-E1 | 1.0 | 0.17395187777594392 | 0.5573890189217146 | PASS | PASS | NA | -0.030398009785759617 | REJECT |
| T2 conditional-VAE / k=2:E3-E0 | 1.0 | 0.17395187777594392 | 0.5573890189217146 | PASS | PASS | -0.10015929812411388 | NA | REJECT |
| T2 conditional-VAE / k=2:E3-E1 | 1.0 | 0.17395187777594392 | 0.5573890189217146 | PASS | PASS | NA | -0.08231064730495988 | REJECT |
| T3 fault-preserving augmentation / k=1:E4-E0 | 1.0 | 0.09935218151607667 | 0.7318281364499486 | PASS | FAIL | 0.002828773996422296 | NA | REJECT |
| T3 fault-preserving augmentation / k=1:E4-E1 | 1.0 | 0.09935218151607667 | 0.7318281364499486 | PASS | FAIL | NA | -0.0006856965829338257 | REJECT |
| T3 fault-preserving augmentation / k=2:E4-E0 | 1.0 | 0.09935218151607667 | 0.7318281364499486 | PASS | FAIL | -0.00018390936978700533 | NA | REJECT |
| T3 fault-preserving augmentation / k=2:E4-E1 | 1.0 | 0.09935218151607667 | 0.7318281364499486 | PASS | FAIL | NA | -0.0006748586857578065 | REJECT |

Association conclusion: the available sample is small and diagnostics are not identically measured across historical branches. C2ST has no useful cross-method variance because the available values are at or near 1.0, so a meaningful correlation coefficient is not claimed. The held-out evidence is independent of diagnostic tuning: T0/T0-v2/T2 have negative utility deltas in their frozen comparisons, while T3 is non-positive versus simple augmentation and is additionally rejected for fidelity/near-copy behavior. This supports the gate as a joint safety screen, not a single-metric utility predictor.

## 4. Threshold audit

| threshold/rule | source and rationale | timing relative to utility | absolute or dataset-relative |
|---|---|---|---|
| C2ST ROC-AUC ≤ 0.95 | Frozen T2/T3 protocol; discriminator separability rejection criterion | fixed before final utility evaluation; informed by development diagnostics, not final-test tuning | absolute metric, calibration dataset-dependent |
| PSD JS ≤ 0.25; PSD cosine ≥ 0.65 | Frozen T3 protocol; coarse spectral similarity guard | fixed before T3 final evaluation | absolute cutoffs, scale dataset-dependent |
| envelope-anchor drift ≤ 50 Hz | Frozen T3 protocol; prevents large fault-anchor movement | fixed before T3 final evaluation | absolute frequency cutoff |
| NN median ratio ≥ 0.25; no exact hash overlap | Frozen T2/T3 protocols; reject near-copy/memorization | fixed before final utility evaluation | absolute ratio/hash rule, calibrated on parent geometry |
| provenance and budget audits PASS | hard validity requirements from benchmark protocol | fixed before all frozen final evaluations | absolute boolean requirements |
| utility PR-AUC mean delta > 0 in prototype | retrospective `safety_gate.py` decision rule | defined after frozen utility artifacts existed; retrospective/prototype | absolute sign rule |
| RMS/kurtosis/crest/envelope distributions | diagnostics only; no historical hard PASS/FAIL cutoff | descriptive only | dataset-relative until SafetyGate-v1 |

The current common gate is explicitly retrospective/prototype. Fidelity cutoffs were frozen before each branch's final utility evaluation, but the common cross-branch interface and utility aggregation were written retrospectively. They were not tuned to force the four existing methods to fail.

## 5. SafetyGate-v1 decision

For future DENSO validation, SafetyGate-v1 must be frozen before any candidate utility result is inspected. It retains the absolute validity/hash rules and uses a train/validation measured-real reference to calibrate distributional diagnostics: candidate C2ST/JS/cosine/envelope/feature gaps must remain within the pre-registered reference quantiles plus fixed margins. Utility requires at least five paired seeds and a positive PR-AUC delta with the 95% CI lower bound above zero against both E0 and E1. A missing diagnostic remains UNKNOWN and is not PASS.

Decision for final submission: VALIDATION PASS for the gate contribution, with the limitation that this validates diagnostic behavior and transparent threshold provenance—not universal effectiveness of synthetic data and not transfer to DENSO field faults. The final slide should include `safety_gate_validation_figure.svg` and the held-out negative-result table.
