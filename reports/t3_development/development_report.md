# T3 pre-final development report

All candidates use only train/validation fault groups. The final holdout condition and bearing groups are excluded from this gate.

Selected policy: `time_scale` (time_scale). Development gate: FAIL; lowest-score policy retained for diagnostic final comparison.

| policy | operators | complexity | pass rate | mean C2ST | mean PSD JS | mean PSD cosine | mean anchor drift (Hz) | mean NN ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| amplitude | amplitude | 1 | 0.00 | 0.9979 | 0.0994 | 0.7318 | 3.61 | 1.466 |
| shift | shift | 1 | 0.00 | 0.9979 | 0.0994 | 0.7319 | 3.61 | 1.473 |
| noise | noise | 1 | 0.00 | 0.9979 | 0.0994 | 0.7318 | 3.96 | 1.462 |
| phase | phase | 1 | 0.00 | 0.9979 | 0.0994 | 0.7318 | 3.71 | 1.462 |
| spectral | spectral | 1 | 0.00 | 0.9979 | 0.0993 | 0.7322 | 4.30 | 1.463 |
| time_scale | time_scale | 1 | 0.00 | 0.9978 | 0.0994 | 0.7318 | 3.61 | 1.461 |
| envelope | envelope | 1 | 0.00 | 0.9980 | 0.0993 | 0.7321 | 4.44 | 1.464 |
| amplitude_shift | amplitude, shift | 2 | 0.00 | 0.9978 | 0.0994 | 0.7317 | 3.81 | 1.459 |
| amplitude_noise | amplitude, noise | 2 | 0.00 | 0.9980 | 0.0994 | 0.7319 | 4.10 | 1.462 |
| amplitude_phase | amplitude, phase | 2 | 0.00 | 0.9980 | 0.0994 | 0.7318 | 3.61 | 1.464 |
| amplitude_envelope | amplitude, envelope | 2 | 0.00 | 0.9978 | 0.0994 | 0.7319 | 4.44 | 1.470 |
| conservative_combo | amplitude, shift, noise, phase, spectral, envelope | 6 | 0.00 | 0.9979 | 0.0993 | 0.7320 | 4.10 | 1.479 |
