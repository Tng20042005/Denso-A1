# ADR-010: T3 fault-preserving augmentation

## Status

Accepted for one frozen evaluation cycle. T0, T0-v2 and conditional-VAE T2 are closed negative-result branches. GAN and diffusion are explicitly out of scope.

## Hypothesis

In the extremely few-shot regime, constrained transformations of measured fault samples may preserve the real fault manifold better than generating raw waveforms from physics or a learned generative model.

## Protocol

T3 is evaluated only for `k>=1`; at `k=0` there is no measured fault information and no T3 result is fabricated. Candidate operators are evaluated individually and in conservative combinations using train/validation fault groups only: amplitude scaling, bounded temporal shift, measured-normal-floor band-limited noise, phase perturbation, bounded spectral-magnitude perturbation, condition-aware time scaling, and envelope-preserving perturbation.

The final comparison is budget-matched: E0 real-only, E1 existing generic augmentation, E2 frozen T0-v2, E3 frozen conditional VAE, and E4 the selected frozen T3 policy. All final arms use the same evaluator and at least five paired seeds. Selection uses PSD, envelope spectrum, kurtosis, crest factor, envelope/fault-frequency anchor drift, C2ST, and nearest-neighbor diagnostics on validation data only.

The new holdout is measured public-real Paderborn data under `N15_M01_F10` for bearings `K001`, `KA15`, and `KI16`. Training and validation use disjoint bearing groups under `N15_M07_F10` and `N15_M07_F04`. The holdout is excluded from selection, VAE fitting, calibration and threshold choices.

## Stop rule

E4 passes only if it improves held-out measured-real detection over E0/E1 without severe fidelity failure. If E4 fails or degrades utility, raw-data augmentation research stops. No additional generative architecture is tried to search for a positive result; the project objective should change toward diagnosis, representation learning, uncertainty or calibration.
