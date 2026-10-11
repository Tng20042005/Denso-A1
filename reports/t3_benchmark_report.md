# T3 fault-preserving augmentation benchmark report

## Validity boundary

The new measured-real final holdout is `N15_M01_F10` on bearings `K001, KA15, KI16`. Training/validation use `N15_M07_F10, N15_M07_F04` with bearing-disjoint groups. No final-test data was used for operator selection, VAE fitting, calibration or threshold selection.

Protocol SHA256: `7fa7e9f66bab0965d7de086570ac18f16ddefd8c09ce53d7e943ea73bb5b2dab`.

Audit status: public-real=PASS, leakage=PASS, budget=PASS, provenance=PASS, fidelity=FAIL.

## Held-out metrics

| setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |
|---|---:|---|---|
| k=0:E0 | 5 | 0.8080 [0.7896, 0.8234] | 0.6638 [0.6480, 0.6796] |
| k=0:E2 | 5 | 0.7087 [0.6610, 0.7778] | 0.5418 [0.4996, 0.5833] |
| k=1:E0 | 5 | 0.9766 [0.9729, 0.9810] | 0.8334 [0.8296, 0.8372] |
| k=1:E1 | 5 | 0.9801 [0.9761, 0.9849] | 0.8325 [0.8292, 0.8356] |
| k=1:E2 | 5 | 0.8668 [0.8410, 0.8926] | 0.6989 [0.6244, 0.7734] |
| k=1:E3 | 5 | 0.9926 [0.9906, 0.9946] | 0.8490 [0.8440, 0.8531] |
| k=1:E4 | 5 | 0.9794 [0.9760, 0.9838] | 0.8327 [0.8301, 0.8363] |
| k=2:E0 | 5 | 0.9228 [0.9184, 0.9297] | 0.8673 [0.8573, 0.8797] |
| k=2:E1 | 5 | 0.9233 [0.9185, 0.9283] | 0.8660 [0.8593, 0.8741] |
| k=2:E2 | 5 | 0.8739 [0.8675, 0.8805] | 0.5927 [0.5927, 0.5927] |
| k=2:E3 | 5 | 0.9924 [0.9907, 0.9942] | 0.8745 [0.8547, 0.9013] |
| k=2:E4 | 5 | 0.9226 [0.9180, 0.9283] | 0.8653 [0.8573, 0.8750] |

## Paired E4 deltas

| comparison | n | PR-AUC delta [95% CI] |
|---|---:|---|
| k=1:E4-E0 | 5 | 0.0028 [0.0018, 0.0041] |
| k=1:E4-E1 | 5 | -0.0007 [-0.0016, 0.0002] |
| k=1:E4-E2 | 5 | 0.1126 [0.0878, 0.1374] |
| k=1:E4-E3 | 5 | -0.0132 [-0.0148, -0.0102] |
| k=2:E4-E0 | 5 | -0.0002 [-0.0105, 0.0080] |
| k=2:E4-E1 | 5 | -0.0007 [-0.0022, 0.0007] |
| k=2:E4-E2 | 5 | 0.0487 [0.0451, 0.0530] |
| k=2:E4-E3 | 5 | -0.0699 [-0.0736, -0.0661] |

## Decision

E4 PASS requires held-out improvement over E0/E1 and no severe fidelity failure. k=0 intentionally has no E4 result because no measured fault information is available; no synthetic T3 result is fabricated.

Decision: FAIL. T3 does not establish a safe, useful augmentation improvement. Stop raw-data augmentation research; do not try GAN, diffusion, or further generative architectures merely to search for a positive result.
