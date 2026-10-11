# ADR-011: SafetyGate-v1 calibration and freeze

## Status

Accepted and frozen for future DENSO validation. This ADR does not reopen T0,
T0-v2, T2 or T3 and does not authorize a new generator.

## Context

The retrospective gate is not an unconditional “always reject” mechanism, but
its historical absolute thresholds are not dataset-universal. A matched
measured-real train-vs-train control produced C2ST ROC-AUC `0.5085`, PSD cosine
`0.9967` and spectral JS `0.0013`. A bearing/group-disjoint measured-real
train-vs-validation reference produced C2ST `0.9977` while retaining PSD cosine
`0.9169` and JS `0.0230`. The difference is real population shift, not a
synthetic candidate.

The controlled corruption ladder also showed coherent degradation: spectral JS
and cosine responded consistently for all five corruption families; C2ST and
envelope-anchor trends were mostly consistent, with mixed cases reported rather
than hidden.

## Decision

Freeze the policy in [`configs/safety_gate_v1.json`](../../configs/safety_gate_v1.json):

- Config SHA256: `f93c0bac6cf1a5dd8fb77ec57f441edb992a3919b11edfa024e1d3b5b89cb435`.
- The Paderborn validation protocol used for this freeze is recorded in
  `reports/safety_gate_validation_protocol.json` with its own SHA256.

1. Keep provenance, public-real isolation, budget, parent-group leakage and
   exact-hash rules as hard validity requirements.
2. Calibrate fidelity cutoffs once from at least five measured-real
   train/validation reference replicates. Use fixed quantiles and fixed margins
   specified in the config; never inspect candidate final-test utility before
   freezing them.
3. Require complete fidelity and novelty diagnostics. Missing values are
   `UNKNOWN`, never `PASS`.
4. Require at least five paired seeds and positive PR-AUC improvement with the
   95% CI lower bound above zero against both real-only and simple augmentation.
5. Keep the final-test population measured-real and untouched by calibration,
   threshold selection and candidate tuning.

## Threshold provenance

The old `0.95` C2ST, `0.25` JS, `0.65` cosine, `50 Hz` anchor and `0.25` NN
rules were frozen before the respective historical final evaluations, but the
common cross-branch retrospective interface was assembled afterward. They are
therefore documented as prototype/retrospective evidence, not silently promoted
to universal thresholds. SafetyGate-v1 uses the pre-registered reference-relative
rules above for future validation.

## Consequences

The gate has an empirical non-rejection reference and a controlled-degradation
test, so it is not justified as a mechanism that rejects every input. The
four historical branches remain rejected because their frozen fidelity,
novelty and held-out utility evidence is unchanged. This freeze supports a
submission claim about admission safety and evidence discipline, not a claim
that synthetic fault data is universally ineffective or that results transfer
to DENSO field faults.
