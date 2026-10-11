# ADR-009: Pivot to conditional learned synthesis (T2)

## Status

Accepted for one frozen evaluation cycle. T0/T0-v2 remains a closed negative-result baseline; no further T0 tuning is permitted.

## Decision

Evaluate a lightweight conditional 1-D VAE before considering diffusion. The VAE is fitted only on real fault windows from the selected training bearing groups. It is conditioned on measured Paderborn operating metadata (`speed_rpm`, `torque_nm`, and `radial_force_n`) and uses the train-only signal normalization already used by the benchmark.

The two training conditions are `N15_M07_F10` and `N15_M07_F04`. Validation uses disjoint bearings under those conditions. The new final holdout is bearing-disjoint and condition-disjoint: `K004`, `KA16`, and `KI04` under `N15_M01_F10`. The holdout is measured `public_real` data and is never used for VAE fitting, calibration, gate selection, or parameter search.

The frozen comparison is:

- E0: measured real training data only;
- E1: simple budget-matched augmentation;
- E2: frozen T0-v2 negative baseline;
- E3: conditional VAE synthesis.

For `k={1,2}`, all generated arms add 32 samples and use exactly the same selected real fault groups. `k=0` reports E0 and E2 only because no real fault group is available for E1/E3; this coverage limitation is explicit rather than filled with synthetic fault parents.

## Fidelity and rejection gate

Before interpreting utility, E3 is compared with train and validation fault populations using RMS, kurtosis, crest factor, PSD, envelope spectrum, band energies, spectral JS/cosine distance, C2ST ROC-AUC, and nearest-neighbor memorization. The frozen rejection rule is exact signal-hash overlap, C2ST ROC-AUC above 0.95, or a median generated-to-real nearest-neighbor distance ratio below 0.25 relative to real leave-one-out neighbors. A rejected VAE is not treated as a successful augmentation method.

Spectral and envelope-aware reconstruction terms are included because the completed T0 failure audit found quantitative PSD and envelope mismatches, not because of final-test results. The VAE configuration, split, seeds, budget, audit rules, and hash are frozen in `reports/t2_protocol_freeze.json` before final evaluation.

## Consequences

This ADR permits a negative T2 result. If the VAE fails fidelity or held-out utility, the branch stops and diffusion is not evaluated in this cycle. Any future diffusion study requires a new ADR, a new untouched holdout or external dataset, and a new pre-registered freeze.
