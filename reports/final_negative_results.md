# Final negative results — Synthetic Fault Data Safety Gate

## Decision

The raw-waveform generation/augmentation objective is closed for this cycle. T0 physics synthesis, T0-v2 calibrated physics synthesis, T2 conditional 1D VAE and T3 fault-preserving augmentation are all rejected by the generator-agnostic admission gate. No additional generator, GAN, diffusion model or parameter search is started.

## Retrospective evidence

| Branch | Validity | Fidelity | Novelty | Utility | Deployment decision |
|---|---|---|---|---|---|
| T0 | PASS | FAIL: C2ST ROC-AUC 1.0, PSD/envelope and higher-order-statistic mismatch | UNKNOWN: no frozen NN admission audit | Negative/near-zero held-out Paderborn deltas | REJECT |
| T0-v2 | PASS | FAIL/not independently passed; inherited diagnosed physics mismatch | UNKNOWN: no independent NN admission threshold | Negative E2−E0 PR-AUC at k=1,2 | REJECT |
| T2 conditional VAE | PASS | FAIL: C2ST ROC-AUC 1.0 | PASS: frozen memorization audit | Negative E3−E0 and E3−E1 PR-AUC at k=1,2 | REJECT |
| T3 fault-preserving | PASS | FAIL: validation C2ST≈0.998 | FAIL: near-copy train-parent NN ratio 0 | E4−E1 non-positive; k=2 E4−E0 non-positive | REJECT |

## Supported interpretation

Across the tested CWRU/Paderborn few-shot settings, four representative synthesis/augmentation strategies failed to simultaneously satisfy fidelity, novelty and held-out real-fault utility requirements. The safety gate prevented unsupported synthetic-data claims and identified when generated fault data should not be used.

This is not a universal impossibility claim. The evidence does not establish that every synthetic-fault method fails, nor does it establish transfer to DENSO or naturally occurring field faults. The next objective should change to measured-data diagnosis, representation learning, uncertainty or calibration rather than continued raw-data synthesis tuning.

## Traceability

- Common gate: `src/denso_a1/safety_gate.py`
- Machine-readable retrospective: `reports/safety_gate/retrospective.json`
- Comparison CSV: `reports/generator_comparison.csv`
- Detailed gate summary: `reports/safety_gate_summary.md`
- Slide table: `reports/final_results_table.md`
