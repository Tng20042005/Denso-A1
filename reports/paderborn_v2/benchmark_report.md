# Paderborn_Bearing_DataCenter_T0_v2 public-real benchmark report

Experiment: `Paderborn_T0_v2_E4_final_holdout` over `k={0,1,2}`; E0/E1/E2 are the paired arms within each supported k.

## Benchmark validity

Split mode: `bearing_and_condition_disjoint_holdout`. Seeds per reported group: 5.
Audits: public-real test `True`; leakage `True`; budget `True`; training-set difference `True`; calibration `True`.
Method coverage by k: `{'0': ['E0', 'E2'], '1': ['E0', 'E1', 'E2'], '2': ['E0', 'E1', 'E2']}`.

New Paderborn bearing- and condition-disjoint holdout; train/validation use N15_M07_F10 and final test uses untouched N09_M07_F10 measured vibration_1.

## Baseline difficulty

The table below shows the evaluator result before comparing T0 utility. E0 is not saturated at PR-AUC≈1.0 across all k values; this benchmark provides non-trivial room for paired comparison.

| Setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |
| --- | ---: | --- | --- |
| k=0:E0 | 5 | 0.5808 [0.5301, 0.6315] | 0.4739 [0.4102, 0.5289] |
| k=0:E2 | 5 | 0.5612 [0.5455, 0.5757] | 0.5708 [0.4035, 0.7473] |
| k=1:E0 | 5 | 0.7108 [0.6998, 0.7219] | 0.7995 [0.7995, 0.7995] |
| k=1:E1 | 5 | 0.7101 [0.7011, 0.7190] | 0.7995 [0.7995, 0.7995] |
| k=1:E2 | 5 | 0.5535 [0.5325, 0.5797] | 0.4596 [0.4007, 0.5207] |
| k=2:E0 | 5 | 1.0000 [1.0000, 1.0000] | 0.9355 [0.8850, 0.9860] |
| k=2:E1 | 5 | 1.0000 [1.0000, 1.0000] | 0.9842 [0.9525, 1.0000] |
| k=2:E2 | 5 | 0.7483 [0.7054, 0.8088] | 0.7085 [0.6926, 0.7247] |

## Paired utility of T0

Positive utility would require a reproducible positive paired delta on held-out measured faults. E2 is compared with E0 and E1 under the same split, subset and model seed.

| Comparison | n | PR-AUC mean delta [95% CI] | F1 mean delta [95% CI] |
| --- | ---: | --- | --- |
| k=0:E2-E0 | 5 | -0.0196 [-0.0838, 0.0398] | 0.0969 [-0.1153, 0.3091] |
| k=1:E2-E0 | 5 | -0.1573 [-0.1850, -0.1208] | -0.3399 [-0.3980, -0.2760] |
| k=1:E2-E1 | 5 | -0.1566 [-0.1840, -0.1216] | -0.3399 [-0.3980, -0.2760] |
| k=2:E2-E0 | 5 | -0.2517 [-0.2942, -0.1898] | -0.2270 [-0.2830, -0.1711] |
| k=2:E2-E1 | 5 | -0.2517 [-0.2942, -0.1898] | -0.2757 [-0.2989, -0.2491] |

## Negative results and interpretation

The result is not a T0 utility claim. If paired deltas are zero or their intervals include zero, T0 is not shown to improve this evaluator on this benchmark. A negative F1 delta is retained rather than hidden behind PR-AUC.

This is evidence on the Paderborn_Bearing_DataCenter_T0_v2 benchmark only. It does not establish transfer to DENSO or naturally occurring field faults. The split is frozen by raw recording group/condition, and generated samples are restricted to train parents.

## Traceability

- Raw per-run rows: `raw_metrics.json` (training sample/group IDs, class counts, source counts, hashes, prediction hashes)
- Per-run audit table: `run_audit.md`
- Frozen group manifests: `split_manifest.json`
- Dataset file checksums: `summary.json`
