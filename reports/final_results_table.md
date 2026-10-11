# Final results table — slide-ready

| Branch | Provenance | Fidelity | Novelty | Held-out utility | Admission |
|---|---|---|---|---|---|
| T0 physics | PASS | FAIL — C2ST 1.0; PSD/envelope mismatch | UNKNOWN | negative/near-zero Paderborn deltas | REJECT |
| T0-v2 calibrated physics | PASS | FAIL / not independently passed | UNKNOWN | E2−E0 PR-AUC negative for k=1,2 | REJECT |
| T2 conditional VAE | PASS | FAIL — C2ST 1.0 | PASS — memorization audit | E3−E0 PR-AUC negative for k=1,2 | REJECT |
| T3 fault-preserving | PASS | FAIL — validation C2ST≈0.998 | FAIL — near-copy NN ratio 0 | E4−E1 non-positive; k=2 E4−E0 non-positive | REJECT |

Interpretation: this is a safety-gate contribution, not a universal claim that synthetic fault data cannot work. Scope is the tested CWRU/Paderborn few-shot settings; transfer to DENSO remains untested.
