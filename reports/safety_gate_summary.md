# Synthetic Fault Data Safety Gate

The gate is generator-agnostic: synthetic fault data is admitted only when provenance/validity, fidelity, novelty and held-out measured-real utility all PASS. UNKNOWN is not treated as PASS.

## Retrospective decision table

| method | provenance | fidelity | novelty | utility | admission | downstream agreement |
|---|---|---|---|---|---|---|
| T0 | PASS | FAIL | UNKNOWN | FAIL | **REJECT** | AGREES: no positive held-out utility; negative/near-zero paired deltas |
| T0-v2 | PASS | FAIL | UNKNOWN | FAIL | **REJECT** | AGREES: negative E2 utility on the final frozen Paderborn holdout |
| T2 conditional-VAE | PASS | FAIL | PASS | FAIL | **REJECT** | AGREES: C2ST rejection coincided with negative held-out E3 utility |
| T3 fault-preserving augmentation | PASS | FAIL | FAIL | FAIL | **REJECT** | AGREES: no improvement over simple augmentation and fidelity/near-copy rejection |

## Interpretation

These results do not show that synthetic fault data is universally ineffective. They show that, across the tested CWRU/Paderborn few-shot settings, four representative synthesis/augmentation strategies failed to simultaneously satisfy fidelity, novelty and held-out real-fault utility requirements. The gate prevents unsupported synthetic-data claims and identifies when generated fault data should not be used.

Validity and transfer limits are separate from fidelity: all four branches had strong public-real/leakage/budget controls where recorded, but their evidence remains bounded to the cited public benchmarks and does not establish transfer to DENSO or naturally occurring field faults.

See `reports/generator_comparison.csv` and `retrospective.json` for machine-readable evidence paths and per-gate reasons.
