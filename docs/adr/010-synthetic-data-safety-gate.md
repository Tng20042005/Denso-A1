# ADR-010: Generator-agnostic Synthetic Fault Data Safety Gate

## Status

Accepted. Raw-waveform generation and augmentation development is closed for this project cycle. T0, T0-v2, conditional-VAE T2 and T3 fault-preserving augmentation are frozen negative-result branches. No additional generator, GAN, diffusion model or parameter search is authorized.

## Decision

Synthetic fault data is an optional training input, not an outcome to be defended. A candidate dataset must pass all four gates before deployment:

1. provenance/validity: public-real test isolation, parent-group leakage, budget matching and traceability;
2. fidelity: PSD/envelope alignment, RMS/kurtosis/crest factor and real-vs-synthetic C2ST;
3. novelty: nearest-neighbor distance, duplicate/hash checks and memorization detection;
4. utility: paired evaluation on held-out measured-real faults against E0 real-only and E1 simple augmentation, with at least five paired seeds and PR-AUC/F1 uncertainty.

`UNKNOWN` is not accepted as `PASS`. The same interface is applied retrospectively to T0, T0-v2, T2 and T3 artifacts; the machine-readable implementation is `src/denso_a1/safety_gate.py` and its evidence output is `reports/safety_gate/retrospective.json`.

## Interpretation boundary

The retrospective result does not claim that synthetic fault data is universally ineffective. It supports the narrower statement that, across the tested CWRU/Paderborn few-shot settings, four representative synthesis/augmentation strategies failed to simultaneously satisfy fidelity, novelty and held-out real-fault utility requirements. The gate prevents unsupported synthetic-data claims and identifies when generated fault data should not be used.

All evidence remains bounded to the cited public datasets and protocols. It does not establish transfer to DENSO or naturally occurring field faults.

## Consequence

The submission/slide package should present the safety gate and its negative retrospective evidence as the contribution. The recommended next project objective is measured-data diagnosis, representation learning, uncertainty or calibration—not further raw-data synthesis tuning.
