# CWRU_Bearing_Data_Center public-real benchmark report

Experiment: `E4_k_sweep` over `k={0,1,2}`; E0/E1/E2 are the paired arms within each supported k.

## Benchmark validity

Split mode: `cross_load`. Seeds per reported group: 5.
Audits: public-real test `True`; leakage `True`; budget `True`; training-set difference `True`.
Method coverage by k: `{'0': ['E0', 'E2'], '1': ['E0', 'E1', 'E2'], '2': ['E0', 'E1', 'E2']}`.

This report uses measured CWRU vibration recordings downloaded from the official Bearing Data Center. Faults are seeded physical faults; they are not DENSO data and not field-observed faults.

## Baseline difficulty

The table below shows the evaluator result before comparing T0 utility. E0 is not saturated at PR-AUC≈1.0 across all k values; this benchmark provides non-trivial room for paired comparison.

| Setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |
| --- | ---: | --- | --- |
| k=0:E0 | 5 | 0.9288 [0.8419, 0.9997] | 0.8354 [0.7506, 0.9181] |
| k=0:E2 | 5 | 0.9922 [0.9838, 1.0000] | 0.7458 [0.5964, 0.8958] |
| k=1:E0 | 5 | 0.9980 [0.9940, 1.0000] | 0.7535 [0.5964, 0.9123] |
| k=1:E1 | 5 | 0.9980 [0.9940, 1.0000] | 0.7412 [0.5964, 0.8955] |
| k=1:E2 | 5 | 1.0000 [1.0000, 1.0000] | 0.8375 [0.7027, 0.9723] |
| k=2:E0 | 5 | 0.9980 [0.9940, 1.0000] | 0.8187 [0.6610, 0.9764] |
| k=2:E1 | 5 | 0.9980 [0.9940, 1.0000] | 0.8105 [0.6563, 0.9647] |
| k=2:E2 | 5 | 1.0000 [1.0000, 1.0000] | 0.8369 [0.7008, 0.9613] |

## Paired utility of T0

Positive utility would require a reproducible positive paired delta on held-out measured faults. E2 is compared with E0 and E1 under the same split, subset and model seed.

| Comparison | n | PR-AUC mean delta [95% CI] | F1 mean delta [95% CI] |
| --- | ---: | --- | --- |
| k=0:E2-E0 | 5 | 0.0634 [0.0003, 0.1419] | -0.0896 [-0.3211, 0.1435] |
| k=1:E2-E0 | 5 | 0.0020 [0.0000, 0.0060] | 0.0840 [0.0057, 0.1856] |
| k=1:E2-E1 | 5 | 0.0020 [0.0000, 0.0060] | 0.0963 [0.0203, 0.1856] |
| k=2:E2-E0 | 5 | 0.0020 [0.0000, 0.0060] | 0.0182 [-0.0226, 0.0772] |
| k=2:E2-E1 | 5 | 0.0020 [0.0000, 0.0060] | 0.0264 [-0.0179, 0.0807] |

## Negative results and interpretation

The result is not a T0 utility claim. If paired deltas are zero or their intervals include zero, T0 is not shown to improve this evaluator on this benchmark. A negative F1 delta is retained rather than hidden behind PR-AUC.

This is evidence on the CWRU_Bearing_Data_Center benchmark only. It does not establish transfer to DENSO or naturally occurring field faults. The split is frozen by raw recording group/condition, and generated samples are restricted to train parents.

## Traceability

- Raw per-run rows: `raw_metrics.json` (training sample/group IDs, class counts, source counts, hashes, prediction hashes)
- Per-run audit table: `run_audit.md`
- Frozen group manifests: `split_manifest.json`
- Dataset file checksums: `summary.json`
