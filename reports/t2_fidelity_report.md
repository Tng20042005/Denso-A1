# T2 conditional-VAE fidelity report

This report uses only training and validation fault groups. The final measured-real holdout is not used in fidelity analysis, tuning, or threshold selection.

## Gate

The frozen gate rejects exact signal-hash overlap, median generated-to-real nearest-neighbor ratio below 0.25, or C2ST ROC-AUC above 0.95. A rejected model is not eligible as a successful T2 augmentation arm.

| k | seed | partition | C2ST ROC-AUC | PSD JS | PSD cosine | kurtosis real/gen | crest real/gen | envelope peak real/gen (Hz) | NN ratio | gate |
|---:|---:|---|---:|---:|---:|---|---|---|---:|---|
| 1 | 0 | train_fault | 1.0000 | 0.1630 | 0.7621 | 5.478/4.430 | 5.445/4.123 | 78.1/696.8 | 0.734 | REJECT |
| 1 | 0 | validation_fault | 1.0000 | 0.1365 | 0.5696 | 4.010/4.430 | 5.294/4.123 | 128.9/696.8 | 0.666 | REJECT |
| 2 | 0 | train_fault | 1.0000 | 0.1492 | 0.7964 | 5.478/4.052 | 5.445/4.561 | 78.1/185.1 | 0.452 | REJECT |
| 2 | 0 | validation_fault | 1.0000 | 0.2011 | 0.2299 | 4.010/4.052 | 5.294/4.561 | 128.9/185.1 | 0.623 | REJECT |
| 1 | 1 | train_fault | 1.0000 | 0.1684 | 0.7255 | 5.478/4.668 | 5.445/4.618 | 78.1/360.4 | 0.721 | REJECT |
| 1 | 1 | validation_fault | 1.0000 | 0.1377 | 0.6203 | 4.010/4.668 | 5.294/4.618 | 128.9/360.4 | 0.654 | REJECT |
| 2 | 1 | train_fault | 1.0000 | 0.1977 | 0.6753 | 5.478/4.119 | 5.445/5.035 | 78.1/103.5 | 0.466 | REJECT |
| 2 | 1 | validation_fault | 1.0000 | 0.2198 | 0.1510 | 4.010/4.119 | 5.294/5.035 | 128.9/103.5 | 0.618 | REJECT |
| 1 | 2 | train_fault | 1.0000 | 0.1758 | 0.6939 | 5.478/4.436 | 5.445/4.307 | 78.1/439.5 | 0.749 | REJECT |
| 1 | 2 | validation_fault | 1.0000 | 0.1381 | 0.6298 | 4.010/4.436 | 5.294/4.307 | 128.9/439.5 | 0.616 | REJECT |
| 2 | 2 | train_fault | 1.0000 | 0.1579 | 0.7619 | 5.478/4.224 | 5.445/4.795 | 78.1/121.6 | 0.455 | REJECT |
| 2 | 2 | validation_fault | 1.0000 | 0.2082 | 0.2042 | 4.010/4.224 | 5.294/4.795 | 128.9/121.6 | 0.618 | REJECT |
| 1 | 3 | train_fault | 1.0000 | 0.1721 | 0.7051 | 5.478/4.648 | 5.445/4.439 | 78.1/275.9 | 0.716 | REJECT |
| 1 | 3 | validation_fault | 1.0000 | 0.1407 | 0.5599 | 4.010/4.648 | 5.294/4.439 | 128.9/275.9 | 0.639 | REJECT |
| 2 | 3 | train_fault | 1.0000 | 0.1763 | 0.7221 | 5.478/4.057 | 5.445/4.669 | 78.1/113.8 | 0.458 | REJECT |
| 2 | 3 | validation_fault | 1.0000 | 0.2164 | 0.1687 | 4.010/4.057 | 5.294/4.669 | 128.9/113.8 | 0.621 | REJECT |
| 1 | 4 | train_fault | 1.0000 | 0.1770 | 0.6996 | 5.478/4.418 | 5.445/4.452 | 78.1/261.7 | 0.726 | REJECT |
| 1 | 4 | validation_fault | 1.0000 | 0.1438 | 0.5831 | 4.010/4.418 | 5.294/4.452 | 128.9/261.7 | 0.659 | REJECT |
| 2 | 4 | train_fault | 1.0000 | 0.1590 | 0.7416 | 5.478/3.737 | 5.445/4.530 | 78.1/153.3 | 0.452 | REJECT |
| 2 | 4 | validation_fault | 1.0000 | 0.2401 | 0.1479 | 4.010/3.737 | 5.294/4.530 | 128.9/153.3 | 0.618 | REJECT |
