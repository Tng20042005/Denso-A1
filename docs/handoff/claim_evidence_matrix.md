# Claim–Evidence Matrix (handoff alias)

The canonical current matrix is [`docs/claim_evidence_matrix.md`](../claim_evidence_matrix.md).
This handoff path is retained for older slide links and intentionally points to
the safety-gate claims rather than the closed generator hypothesis.

| ID | Claim | Evidence | Scope | Status |
| --- | --- | --- | --- | --- |
| SG-1 | Candidates require provenance, fidelity, novelty and held-out utility before admission | `src/denso_a1/safety_gate.py`, ADR-010 | generator-agnostic protocol | Supported |
| SG-2 | Four frozen branches were rejected before deployment | `reports/generator_comparison.csv`, `reports/safety_gate_summary.md` | tested CWRU/Paderborn settings | Supported |
| SG-3 | T0 and T0-v2 fail fidelity; their original novelty gate is UNKNOWN | `reports/t0_failure_analysis.md`, `reports/paderborn_v2/summary.json` | frozen public-real artifacts | Supported |
| SG-4 | T2 fails fidelity and held-out utility while its frozen memorization audit passes | `reports/t2_benchmark/t2_fidelity_report.md`, `reports/t2_benchmark/summary.json` | frozen Paderborn holdout | Supported |
| SG-5 | T3 fails fidelity/novelty and does not improve over simple augmentation | `reports/t3_fidelity_report.md`, `reports/t3_benchmark/summary.json` | new Paderborn holdout | Supported |
| SG-8 | Matched measured-real controls show the gate is not simply always-reject | `reports/safety_gate_validation.md`, `reports/safety_gate_validation_reference.json` | Paderborn measured-real reference | Supported with dataset-shift caveat |
| SG-9 | Controlled corruptions produce mostly coherent diagnostic degradation | `reports/safety_gate_corruption_ladder.csv` | diagnostic-only | Supported; mixed trends disclosed |
| SG-10 | SafetyGate-v1 is reference-relative and frozen before future utility | `docs/adr/011-safety-gate-v1-freeze.md`, `configs/safety_gate_v1.json` | future DENSO validation | Supported |
| SG-6 | Synthetic fault data is universally ineffective | none | general/DENSO field faults | Not claimable |
| SG-7 | Results transfer to DENSO field faults | none; DENSO data unavailable | DENSO | Not claimable |
