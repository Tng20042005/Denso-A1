# Paderborn T2 benchmark report

## Benchmark validity

The final test contains measured public-real vibration only, with bearings K004/KA16/KI04 under the new N15_M01_F10 condition. Training and validation use N15_M07_F10 and N15_M07_F04 with disjoint bearing groups. No final-test signals, labels, or metadata were used for VAE fitting, calibration, or threshold selection.

Protocol freeze SHA256: `64e6e406da77011eae9305037c2feea6ba04c42e0767021d25967f21ee5c52d8`.

Audit status: public-real=PASS, leakage=PASS, budget=PASS, training-difference=PASS, T2 calibration=PASS, memorization=PASS, fidelity=FAIL.

## Held-out metrics

| setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |
|---|---:|---|---|
| k=0:E0 | 5 | 0.8094 [0.7989, 0.8195] | 0.5824 [0.5666, 0.6101] |
| k=0:E2 | 5 | 0.9999 [0.9999, 1.0000] | 0.8850 [0.8636, 0.9063] |
| k=1:E0 | 5 | 0.9712 [0.9624, 0.9808] | 0.8525 [0.8388, 0.8613] |
| k=1:E1 | 5 | 0.9735 [0.9697, 0.9806] | 0.8571 [0.8569, 0.8575] |
| k=1:E2 | 5 | 0.9966 [0.9932, 0.9990] | 0.8573 [0.8569, 0.8577] |
| k=1:E3 | 5 | 0.9431 [0.9353, 0.9503] | 0.7977 [0.7874, 0.8088] |
| k=2:E0 | 5 | 0.8261 [0.8053, 0.8401] | 0.6269 [0.6211, 0.6332] |
| k=2:E1 | 5 | 0.8082 [0.7741, 0.8348] | 0.6260 [0.6162, 0.6359] |
| k=2:E2 | 5 | 0.8301 [0.8092, 0.8462] | 0.6003 [0.5802, 0.6290] |
| k=2:E3 | 5 | 0.7259 [0.7124, 0.7391] | 0.6097 [0.5804, 0.6280] |

## Paired deltas (relative to E0)

| comparison | n | PR-AUC delta [95% CI] |
|---|---:|---|
| k=1:E1-E0 | 5 | 0.0023 [-0.0021, 0.0076] |
| k=1:E2-E0 | 5 | 0.0254 [0.0159, 0.0349] |
| k=1:E3-E0 | 5 | -0.0281 [-0.0309, -0.0254] |
| k=1:E3-E1 | 5 | -0.0304 [-0.0353, -0.0255] |
| k=2:E1-E0 | 5 | -0.0178 [-0.0353, -0.0004] |
| k=2:E2-E0 | 5 | 0.0040 [-0.0241, 0.0338] |
| k=2:E3-E0 | 5 | -0.1002 [-0.1103, -0.0900] |
| k=2:E3-E1 | 5 | -0.0823 [-0.1001, -0.0620] |

## Interpretation and stop decision

E2 is the frozen T0-v2 negative baseline and is not tuned here. k=0 has E0 and E2 coverage only because there are no real fault groups available for E1/E3 under the pre-registered protocol. For k=1 and k=2, E3 uses exactly the same selected real fault groups and generated-sample budget as E1/E2.

T2 conditional-VAE results are diagnostic unless every fidelity, memorization, leakage and budget gate passes. If the fidelity gate is rejected, this branch is a negative result and no diffusion model is started in this evaluation cycle.
