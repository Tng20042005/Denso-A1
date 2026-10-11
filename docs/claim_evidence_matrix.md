# Claim–Evidence Matrix: Synthetic Fault Data Safety Gate

| ID | Claim | Evidence | Scope | Status |
| --- | --- | --- | --- | --- |
| SG-1 | Synthetic candidates require provenance, fidelity, novelty and held-out utility before admission | `src/denso_a1/safety_gate.py`, `docs/adr/010-synthetic-data-safety-gate.md` | generator-agnostic protocol | Supported |
| SG-2 | Public-real isolation, leakage, budget and provenance audits are explicit gates | `reports/safety_gate/retrospective.json`, each cited raw benchmark manifest | tested CWRU/Paderborn runs | Supported |
| SG-3 | T0 fails fidelity and lacks a demonstrated novelty gate | `reports/t0_failure_analysis.md`, `reports/paderborn/summary.json` | Paderborn diagnosis/benchmark | Supported; no DENSO claim |
| SG-4 | T0-v2 fails the safety gate despite validity/calibration audits | `reports/paderborn_v2/summary.json`, `reports/t0_failure_analysis.md` | frozen Paderborn holdout | Supported |
| SG-5 | T2 fails fidelity and held-out utility while memorization audit passes | `reports/t2_benchmark/t2_fidelity_report.md`, `reports/t2_benchmark/summary.json` | frozen Paderborn T2 holdout | Supported |
| SG-6 | T3 fails fidelity/novelty and does not improve over simple augmentation | `reports/t3_fidelity_report.md`, `reports/t3_benchmark_report.md` | new Paderborn T3 holdout | Supported |
| SG-7 | Four representative branches were rejected before deployment | `reports/generator_comparison.csv`, `reports/safety_gate_summary.md` | tested public-real settings | Supported |
| SG-10 | The gate is not merely an always-reject mechanism: matched measured-real controls have chance-level C2ST and high spectral similarity | `reports/safety_gate_validation.md`, `reports/safety_gate_validation_reference.json` | Paderborn measured-real reference only | Supported with dataset-shift caveat |
| SG-11 | Controlled corruption produces mostly coherent degradation in the gate diagnostics | `reports/safety_gate_corruption_ladder.csv`, `reports/safety_gate_validation.md` | diagnostic-only train-fault corruptions | Supported; mixed trends disclosed |
| SG-12 | Historical thresholds are transparent but not dataset-universal; SafetyGate-v1 is reference-relative and frozen before future utility | `docs/adr/011-safety-gate-v1-freeze.md`, `configs/safety_gate_v1.json` | future DENSO validation policy | Supported |
| SG-13 | Frozen gate diagnostics and held-out utility agree directionally for the available branches, but sample size and missing metrics preclude a strong correlation claim | `reports/safety_gate_utility_association.csv`, `reports/safety_gate_validation.md` | 18 frozen method/config rows | Supported; no significance overclaim |
| SG-8 | Synthetic fault data is universally ineffective | none | DENSO/general field faults | Not claimable |
| SG-9 | Results transfer to DENSO field faults | none; DENSO data not available | DENSO | Not claimable |
