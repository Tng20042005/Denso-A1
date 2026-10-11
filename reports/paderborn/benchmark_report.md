# Paderborn_Bearing_DataCenter public-real benchmark report

Experiment: `Paderborn_E4_k_sweep` over `k={0,1,2}`; E0/E1/E2 are the paired arms within each supported k.

## Benchmark validity

Split mode: `bearing_disjoint`. Seeds per reported group: 5.
Audits: public-real test `True`; leakage `True`; budget `True`; training-set difference `True`.
Method coverage by k: `{'0': ['E0', 'E2'], '1': ['E0', 'E1', 'E2'], '2': ['E0', 'E1', 'E2']}`.

Official Paderborn vibration_1 recordings at fixed N15_M07_F10 condition; healthy and accelerated-lifetime real-damage bearings; measurements [1, 2, 3, 4, 5].

## Baseline difficulty

The table below shows the evaluator result before comparing T0 utility. E0 is not saturated at PR-AUC≈1.0 across all k values; this benchmark provides non-trivial room for paired comparison.

| Setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |
| --- | ---: | --- | --- |
| k=0:E0 | 5 | 0.8375 [0.6716, 0.9606] | 0.6647 [0.4953, 0.8135] |
| k=0:E2 | 5 | 0.7911 [0.6904, 0.9071] | 0.7813 [0.6851, 0.8487] |
| k=1:E0 | 5 | 0.8306 [0.6479, 0.9585] | 0.6930 [0.5131, 0.8415] |
| k=1:E1 | 5 | 0.8237 [0.6376, 0.9510] | 0.6933 [0.5147, 0.8420] |
| k=1:E2 | 5 | 0.7747 [0.6319, 0.8967] | 0.6495 [0.5471, 0.7549] |
| k=2:E0 | 5 | 0.8371 [0.6814, 0.9809] | 0.7451 [0.6109, 0.8574] |
| k=2:E1 | 5 | 0.8466 [0.6999, 0.9824] | 0.7544 [0.6292, 0.8569] |
| k=2:E2 | 5 | 0.7720 [0.6324, 0.9099] | 0.7229 [0.6262, 0.8201] |

## Paired utility of T0

Positive utility would require a reproducible positive paired delta on held-out measured faults. E2 is compared with E0 and E1 under the same split, subset and model seed.

| Comparison | n | PR-AUC mean delta [95% CI] | F1 mean delta [95% CI] |
| --- | ---: | --- | --- |
| k=0:E2-E0 | 5 | -0.0463 [-0.2453, 0.1400] | 0.1167 [-0.0152, 0.3029] |
| k=1:E2-E0 | 5 | -0.0559 [-0.1882, 0.0511] | -0.0435 [-0.1687, 0.0817] |
| k=1:E2-E1 | 5 | -0.0491 [-0.1886, 0.0573] | -0.0437 [-0.1693, 0.0818] |
| k=2:E2-E0 | 5 | -0.0652 [-0.2046, 0.0148] | -0.0222 [-0.1013, 0.0285] |
| k=2:E2-E1 | 5 | -0.0747 [-0.2094, 0.0030] | -0.0315 [-0.1055, 0.0107] |

## Negative results and interpretation

The result is not a T0 utility claim. If paired deltas are zero or their intervals include zero, T0 is not shown to improve this evaluator on this benchmark. A negative F1 delta is retained rather than hidden behind PR-AUC.

This is evidence on the Paderborn_Bearing_DataCenter benchmark only. It does not establish transfer to DENSO or naturally occurring field faults. The split is frozen by raw recording group/condition, and generated samples are restricted to train parents.

## Traceability

- Raw per-run rows: `raw_metrics.json` (training sample/group IDs, class counts, source counts, hashes, prediction hashes)
- Per-run audit table: `run_audit.md`
- Frozen group manifests: `split_manifest.json`
- Dataset file checksums: `summary.json`
