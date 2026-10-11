# Final negative-result synthesis

The DENSO-A1 raw-waveform augmentation objective is closed after four negative branches:

- T0 physics synthesis: real-vs-generated C2ST ROC-AUC was 1.0 with large PSD/envelope and higher-order-statistic mismatches.
- T0-v2: the frozen Paderborn final holdout produced negative E2−E0 PR-AUC deltas at k=0,1,2.
- Conditional-VAE T2: C2ST ROC-AUC was 1.0 on train/validation populations and held-out E3−E0 PR-AUC was negative.
- T3 fault-preserving augmentation: the frozen operator policy did not satisfy the combined fidelity/utility gate on the new measured-real holdout.

All reported branches used leakage and budget controls; this is a negative scientific result, not evidence that more expressive generators should be searched. The recommended next step is to change the project objective toward measured-data diagnosis, representation learning, or uncertainty/calibration rather than continuing raw-data synthesis tuning.
