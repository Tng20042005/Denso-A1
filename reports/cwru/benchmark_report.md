# CWRU_Bearing_Data_Center public-real benchmark report

Experiment: `E4_k_sweep` over `k={0,1,2}`; E0/E1/E2 are the paired arms within each supported k.

## Benchmark validity

Split mode: `random_group`. Seeds per reported group: 5.
Audits: public-real test `True`; leakage `True`; budget `True`; training-set difference `True`.
Method coverage by k: `{'0': ['E0', 'E2'], '1': ['E0', 'E1', 'E2'], '2': ['E0', 'E1', 'E2']}`.

This report uses measured CWRU vibration recordings downloaded from the official Bearing Data Center. Faults are seeded physical faults; they are not DENSO data and not field-observed faults.

## Baseline difficulty

The table below shows the evaluator result before comparing T0 utility. PR-AUC near 1.0 across E0 indicates that this benchmark may be too easy for ranking methods, even when F1 is lower.

| Setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |
| --- | ---: | --- | --- |
| k=0:E0 | 5 | 0.9988 [0.9965, 1.0000] | 0.8328 [0.7945, 0.9082] |
| k=0:E2 | 5 | 1.0000 [1.0000, 1.0000] | 0.6517 [0.4966, 0.8457] |
| k=1:E0 | 5 | 1.0000 [1.0000, 1.0000] | 0.5957 [0.4957, 0.7940] |
| k=1:E1 | 5 | 1.0000 [1.0000, 1.0000] | 0.5957 [0.4957, 0.7940] |
| k=1:E2 | 5 | 1.0000 [1.0000, 1.0000] | 0.5957 [0.4957, 0.7940] |
| k=2:E0 | 5 | 1.0000 [1.0000, 1.0000] | 0.5957 [0.4957, 0.7940] |
| k=2:E1 | 5 | 1.0000 [1.0000, 1.0000] | 0.5957 [0.4957, 0.7940] |
| k=2:E2 | 5 | 1.0000 [1.0000, 1.0000] | 0.5957 [0.4957, 0.7940] |

## Paired utility of T0

Positive utility would require a reproducible positive paired delta on held-out measured faults. E2 is compared with E0 and E1 under the same split, subset and model seed.

| Comparison | n | PR-AUC mean delta [95% CI] | F1 mean delta [95% CI] |
| --- | ---: | --- | --- |
| k=0:E2-E0 | 5 | 0.0012 [0.0000, 0.0035] | -0.1811 [-0.2985, -0.0619] |
| k=1:E2-E0 | 5 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| k=1:E2-E1 | 5 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| k=2:E2-E0 | 5 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| k=2:E2-E1 | 5 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

## Negative results and interpretation

The result is not a T0 utility claim. If paired deltas are zero or their intervals include zero, T0 is not shown to improve this evaluator on this benchmark. A negative F1 delta is retained rather than hidden behind PR-AUC.

This is evidence on the CWRU_Bearing_Data_Center benchmark only. It does not establish transfer to DENSO or naturally occurring field faults. The split is frozen by raw recording group/condition, and generated samples are restricted to train parents.

## Traceability

- Raw per-run rows: `raw_metrics.json` (training sample/group IDs, class counts, source counts, hashes, prediction hashes)
- Per-run audit table: `run_audit.md`
- Frozen group manifests: `split_manifest.json`
- Dataset file checksums: `summary.json`
