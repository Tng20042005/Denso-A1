# T2 per-run audit

The benchmark completed 50 raw rows: 5 seeds × (E0/E2 at k=0 and E0/E1/E2/E3 at k=1,2).

Each row in `raw_metrics.json` includes training real/generated counts, class counts, sample IDs, group IDs, sample/group/signal hashes and prediction hashes. All public-real, leakage, budget, training-difference, T2 source-group and nearest-neighbor memorization audits pass.

The fidelity gate is intentionally reported as FAIL because C2ST ROC-AUC is 1.0 for every train/validation comparison. This is a model rejection, not a hidden pass or a reason to tune on the final test.

The final test is measured public-real data from the new N15_M01_F10 condition and bearing-disjoint K004/KA16/KI04 groups. No final-test data was used by the VAE.
