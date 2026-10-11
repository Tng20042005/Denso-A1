# DENSO A1 benchmark report

## Scope

This run uses only `simulated` signals. It is mechanism/pipeline evidence, not a DENSO or public-real utility claim.

Primary metric: `pr_auc`. All paired deltas use the same split/subset/model seed per run.

## Aggregate results

| Setup | n | mean PR-AUC | bootstrap 95% CI |
| --- | ---: | ---: | --- |
| k=0:E0 | 5 | 0.9668 | [0.9003, 1.0000] |
| k=0:E2 | 5 | 0.6375 | [0.5750, 0.7000] |
| k=1:E0 | 5 | 1.0000 | [1.0000, 1.0000] |
| k=1:E1 | 5 | 1.0000 | [1.0000, 1.0000] |
| k=1:E2 | 5 | 1.0000 | [1.0000, 1.0000] |
| k=2:E0 | 5 | 1.0000 | [1.0000, 1.0000] |
| k=2:E1 | 5 | 1.0000 | [1.0000, 1.0000] |
| k=2:E2 | 5 | 1.0000 | [1.0000, 1.0000] |

## Paired T0 deltas

| Comparison | n | mean delta | bootstrap 95% CI |
| --- | ---: | ---: | --- |
| k=0:E2-E0 | 5 | -0.3293 | [-0.3875, -0.2711] |
| k=1:E2-E0 | 5 | 0.0000 | [0.0000, 0.0000] |
| k=2:E2-E0 | 5 | 0.0000 | [0.0000, 0.0000] |

## Interpretation

The result is diagnostic for the simulated mechanism. Before any utility claim, replace the corpus with a licensed public-real dataset or DENSO data, freeze the real test groups, and rerun the same protocol.

## Traceability

- Raw run records: `raw_metrics.json`
- Summary: `summary.json`
- Code commit and environment lock must be added when this is promoted to a submission run.
