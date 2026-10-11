# Claim–Evidence Matrix cho slide

| ID | Candidate claim | Evidence | Scope | Status/wording |
|---|---|---|---|---|
| SH-01 | Pipeline prevents obvious train/test parent leakage and audits budgets/provenance | `reports/*/raw_metrics.json`, split manifests, run audits | reported CWRU/Paderborn runs | SUPPORTED |
| SH-02 | CWRU random split is saturated for this evaluator | `reports/cwru/summary.json` | CWRU subset/protocol | SUPPORTED: E0 PR-AUC 0.9988–1.0 |
| SH-03 | Original T0 differs strongly from measured Paderborn faults | `reports/t0_failure_analysis/failure_analysis.json` | N15_M07_F10 train/dev | SUPPORTED: C2ST 1.0, JS 0.186, cosine 0.513 |
| SH-04 | Original Paderborn T0 does not establish positive utility | `reports/paderborn/summary.json` | original bearing-disjoint protocol | SUPPORTED; do not call significant harm because CI crosses 0 |
| SH-05 | Frozen T0-v2 degrades PR-AUC at k=1/2 | `reports/paderborn_v2/summary.json` | N09 holdout | SUPPORTED; CI below 0 |
| SH-06 | T0-v2 independently failed C2ST=1.0 | none | T0-v2 fidelity | UNSUPPORTED; only “not independently passed/inherited concern” |
| SH-07 | Conditional VAE passes memorization audit but fails fidelity and utility | `reports/t2_benchmark/raw_metrics.json`, `summary.json` | T2 holdout | SUPPORTED |
| SH-08 | T3 improves over real-only at k=1 | `reports/t3_benchmark/summary.json` | T3 holdout, only E4−E0 | SUPPORTED narrowly: +0.0028 CI>0 |
| SH-09 | T3 is successful | same + fidelity raw | joint criterion | NOT SUPPORTED: not >E1, k2 ≈0, fidelity/novelty fail |
| SH-10 | Common gate rejected four frozen branches | `reports/safety_gate/retrospective.json` | retrospective interface | SUPPORTED |
| SH-11 | Gate is not empirically forced to reject every population | `reports/safety_gate_validation_reference.json` | matched measured-real diagnostic reference | SUPPORTED with caveat: real data is not a candidate |
| SH-12 | Diagnostics respond coherently to corruption | `reports/safety_gate_corruption_ladder.csv` | 25 diagnostic configurations | SUPPORTED as mostly coherent; mixed C2ST disclosed |
| SH-13 | Gate predicts downstream utility | `reports/safety_gate_utility_association.csv` | 18 dependent rows | UNSUPPORTED; directional association only |
| SH-14 | SafetyGate-v1 is reference-relative and frozen | `configs/safety_gate_v1.json`, ADR-011 | future validation policy | SUPPORTED as policy, not outcome |
| SH-15 | SafetyGate improves fault detection | none | detector accuracy | UNSUPPORTED |
| SH-16 | Synthetic fault data is universally ineffective | none | all generators/domains | UNSUPPORTED |
| SH-17 | Results transfer to DENSO field data | none; no DENSO data | DENSO | UNSUPPORTED |
| SH-18 | SafetyGate could support synthetic-data QA at DENSO | `docs/data_onboarding.md`, roadmap | future proposal | PROPOSED, not demonstrated |

## Mandatory claim boundary

Use “measured public-real” for CWRU/Paderborn; use “DENSO” only in future roadmap. Any statement containing “improves”, “reduces”, “predicts” or “production-ready” requires evidence absent from current artifacts.

