# T0 failure analysis

This is a diagnosis-only artifact. Existing Paderborn final-test groups were excluded from parent selection and calibration; no result here is used to tune the previous test.

Dataset: `Paderborn_Bearing_DataCenter`; condition: `N15_M07_F10`; measurement repetitions: `[1, 2, 3, 4, 5]`; seeds: `5`.
Current T0 configuration: `{'fs_hz': 64000.0, 'f_fault_hz': 120.0, 'f_res_hz': 6000.0, 'damping': 0.08, 'impulse_amplitude': 0.8, 'jitter_std': 0.025, 'modulation_depth': 0.25, 'snr_db': 14.0, 'severity': 1.0}`.

## Quantitative distribution gate

C2ST ROC-AUC=0.5 is indistinguishable distributions; higher values indicate that a classifier can separate measured damage from T0 output. Spectral JS is lower-is-better and cosine similarity is higher-is-better.

| Population | n | C2ST ROC-AUC mean [95% CI] | C2ST accuracy | Spectral JS | PSD cosine |
| --- | ---: | --- | --- | --- | --- |
| k=0:dev_fault | 5 | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.1860 [0.1280, 0.2421] | 0.5133 [0.4183, 0.6173] |
| k=1:train_fault | 5 | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.1759 [0.1026, 0.2522] | 0.5355 [0.3936, 0.6767] |
| k=1:dev_fault | 5 | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.1891 [0.1335, 0.2431] | 0.4995 [0.4025, 0.6010] |
| k=2:train_fault | 5 | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.1503 [0.1084, 0.1953] | 0.5738 [0.4907, 0.6551] |
| k=2:dev_fault | 5 | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.1904 [0.1331, 0.2443] | 0.4958 [0.3978, 0.5989] |

## Feature evidence

Values are means over signals; standardized gap is `(real−generated)/pooled_std`, so its sign indicates direction and magnitude indicates separation.

| Population | Feature | Real mean | Generated mean | Standardized gap |
| --- | --- | --- | --- | --- |
| k=0:dev_fault | rms | 1.4302 [0.8154, 2.2018] | 1.3088 [1.2937, 1.3239] | -0.1596 [-1.4353, 1.0416] |
| k=0:dev_fault | kurtosis | 5.0892 [4.1878, 5.9905] | 19.7542 [18.0921, 21.5029] | -1.7272 [-1.7705, -1.6981] |
| k=0:dev_fault | crest_factor | 5.6257 [5.3677, 5.8724] | 8.9981 [8.8732, 9.1707] | -1.6949 [-1.7440, -1.6413] |
| k=0:dev_fault | resonance_peak_hz | 4544.7266 [3615.6250, 5721.1426] | 4105.8105 [3635.6213, 4935.1074] | -0.0126 [-0.7553, 0.6253] |
| k=0:dev_fault | resonance_halfpower_bw_hz | 66.6992 [56.9824, 80.3711] | 48.3398 [43.9453, 54.8340] | 0.3318 [0.1585, 0.4938] |
| k=0:dev_fault | envelope_peak_hz | 101.5869 [83.6426, 119.5312] | 223.1689 [202.6367, 247.7539] | -0.8956 [-1.0956, -0.6956] |
| k=0:dev_fault | envelope_peak_ratio | 4.8880 [3.2861, 6.5553] | 3.2227 [3.1422, 3.2932] | 0.8233 [-0.0032, 1.6499] |
| k=0:dev_fault | hf_to_faultband_db | -13.9741 [-18.6717, -9.2764] | -3.5755 [-4.5351, -2.8419] | -1.6800 [-1.9298, -1.3826] |
| k=1:train_fault | rms | 1.0526 [0.7953, 1.3098] | 1.2596 [1.1340, 1.3852] | -0.5242 [-1.7903, 0.7852] |
| k=1:train_fault | kurtosis | 5.0710 [4.0300, 6.1120] | 22.7603 [17.4753, 29.0316] | -1.7708 [-1.8481, -1.6934] |
| k=1:train_fault | crest_factor | 5.6022 [5.3515, 5.8530] | 9.2901 [8.7213, 9.8793] | -1.7571 [-1.7825, -1.7280] |
| k=1:train_fault | resonance_peak_hz | 5154.5410 [4085.5957, 6239.4043] | 4255.6152 [3593.9453, 5154.4922] | 0.3659 [0.1321, 0.6029] |
| k=1:train_fault | resonance_halfpower_bw_hz | 67.9199 [55.1758, 80.9570] | 52.8809 [44.8242, 64.9902] | 0.2650 [0.1700, 0.3874] |
| k=1:train_fault | envelope_peak_hz | 105.6396 [82.8125, 128.4668] | 230.9814 [203.4668, 255.3503] | -0.9402 [-1.2321, -0.6231] |
| k=1:train_fault | envelope_peak_ratio | 4.7098 [3.1787, 6.2439] | 3.2424 [3.1523, 3.3153] | 0.7430 [-0.0357, 1.5217] |
| k=1:train_fault | hf_to_faultband_db | -12.7680 [-17.3068, -8.2431] | -4.0816 [-5.3148, -2.8485] | -1.6825 [-1.8254, -1.5590] |
| k=1:dev_fault | rms | 1.3390 [0.7142, 2.1608] | 1.2596 [1.1340, 1.3852] | -0.3992 [-1.5156, 0.7697] |
| k=1:dev_fault | kurtosis | 5.0892 [4.1878, 5.9905] | 22.7603 [17.4753, 29.0316] | -1.7511 [-1.7889, -1.7276] |
| k=1:dev_fault | crest_factor | 5.6257 [5.3677, 5.8724] | 9.2901 [8.7213, 9.8793] | -1.7287 [-1.8197, -1.6435] |
| k=1:dev_fault | resonance_peak_hz | 4544.7266 [3615.6250, 5721.1426] | 4255.6152 [3593.9453, 5154.4922] | -0.1151 [-0.9306, 0.6344] |
| k=1:dev_fault | resonance_halfpower_bw_hz | 66.6992 [56.9824, 80.3711] | 52.8809 [44.8242, 64.9902] | 0.2521 [-0.0055, 0.4693] |
| k=1:dev_fault | envelope_peak_hz | 101.5869 [83.6426, 119.5312] | 230.9814 [203.4668, 255.3503] | -0.9625 [-1.2013, -0.7180] |
| k=1:dev_fault | envelope_peak_ratio | 4.8880 [3.2861, 6.5553] | 3.2424 [3.1523, 3.3153] | 0.7940 [-0.0551, 1.6430] |
| k=1:dev_fault | hf_to_faultband_db | -13.9741 [-18.6717, -9.2764] | -4.0816 [-5.3148, -2.8485] | -1.5905 [-1.9236, -1.0978] |
| k=2:train_fault | rms | 1.0644 [0.9413, 1.1874] | 1.2022 [1.0972, 1.3072] | -0.4121 [-1.1586, 0.3343] |
| k=2:train_fault | kurtosis | 5.0444 [4.5831, 5.5633] | 24.7168 [20.2783, 29.1553] | -1.7577 [-1.8324, -1.6912] |
| k=2:train_fault | crest_factor | 5.6592 [5.5474, 5.8212] | 9.5022 [8.9986, 10.0059] | -1.7506 [-1.8177, -1.6874] |
| k=2:train_fault | resonance_peak_hz | 4671.8262 [4069.1406, 5391.6016] | 4230.3223 [3649.1211, 5101.4648] | 0.1808 [-0.1322, 0.4478] |
| k=2:train_fault | resonance_halfpower_bw_hz | 63.0371 [57.7637, 70.2637] | 52.6855 [44.6289, 65.6250] | 0.2262 [0.1028, 0.3389] |
| k=2:train_fault | envelope_peak_hz | 94.5801 [90.5273, 98.2031] | 234.9365 [208.5205, 255.6641] | -1.0636 [-1.2194, -0.9078] |
| k=2:train_fault | envelope_peak_ratio | 4.6267 [3.8402, 5.4132] | 3.2719 [3.2374, 3.3104] | 0.8533 [0.5194, 1.1652] |
| k=2:train_fault | hf_to_faultband_db | -12.3052 [-15.6197, -8.9907] | -4.3379 [-5.7515, -2.9325] | -1.4889 [-1.5856, -1.4208] |
| k=2:dev_fault | rms | 1.1457 [0.7222, 1.5860] | 1.2022 [1.0972, 1.3072] | -0.3449 [-1.5106, 0.8208] |
| k=2:dev_fault | kurtosis | 5.0892 [4.1878, 5.9905] | 24.7168 [20.2783, 29.1553] | -1.7605 [-1.8080, -1.7165] |
| k=2:dev_fault | crest_factor | 5.6257 [5.3677, 5.8724] | 9.5022 [8.9986, 10.0059] | -1.7642 [-1.8089, -1.7099] |
| k=2:dev_fault | resonance_peak_hz | 4544.7266 [3615.6250, 5721.1426] | 4230.3223 [3649.1211, 5101.4648] | -0.0967 [-0.8877, 0.6099] |
| k=2:dev_fault | resonance_halfpower_bw_hz | 66.6992 [56.9824, 80.3711] | 52.6855 [44.6289, 65.6250] | 0.2619 [0.0096, 0.4645] |
| k=2:dev_fault | envelope_peak_hz | 101.5869 [83.6426, 119.5312] | 234.9365 [208.5205, 255.6641] | -1.0064 [-1.2325, -0.7737] |
| k=2:dev_fault | envelope_peak_ratio | 4.8880 [3.2861, 6.5553] | 3.2719 [3.2374, 3.3104] | 0.8081 [-0.0277, 1.6438] |
| k=2:dev_fault | hf_to_faultband_db | -13.9741 [-18.6717, -9.2764] | -4.3379 [-5.7515, -2.9325] | -1.5874 [-1.9220, -1.1066] |

## Diagnosis

- Fault-frequency mismatch: measured envelope peaks are approximately 95–106 Hz, while the current T0 output peaks at approximately 223–235 Hz; the current 120 Hz anchor is therefore not reproducing the observed envelope structure.
- Resonance/damping mismatch: measured resonance peaks are approximately 4.5–5.2 kHz with half-power bandwidth about 63–68 Hz; current T0 peaks are approximately 4.1–4.3 kHz with bandwidth about 48–53 Hz.
- Impulsiveness shortcut: current T0 kurtosis and crest factor are about 19.8–24.7 and 9.0–9.5, versus measured damage about 5.0–5.7 and 5.6–5.7. This is a large, consistent mismatch in both train and dev comparisons.
- Spectral/amplitude mismatch: current T0 has lower 2–5 kHz energy and higher 10–32 kHz energy; RMS differences are smaller and inconsistent across seeds, so amplitude alone is not the primary failure.
- SNR/noise proxy: 20–32 kHz energy relative to 0–5 kHz is about −14 to −12 dB for measured damage but −4 to −3.6 dB for T0, a roughly 8–10 dB excess high-frequency component in generated signals.
- Operating condition: this diagnosis is fixed at N15_M07_F10, so condition heterogeneity is not the explanation for the within-condition C2ST failure. Severity heterogeneity remains visible in real RMS/envelope distributions but is secondary to the impulsiveness and spectral mismatch.
- Synthetic shortcut: C2ST ROC-AUC is 1.0000 for every train/dev population, consistent with the feature-level separations rather than a subtle evaluator artifact.

## Frozen T0-v2 design

The minimum justified changes are: (1) physics-only defaults set a 100 Hz fault-frequency prior from the 1500 RPM operating point and a generic 5 kHz structural resonance prior; (2) Gaussian impulse smoothing with width 8 samples reduces the isolated-spike/high-frequency shortcut; and (3) k≥1 calibrates only f_fault and f_res from selected training fault groups. Damping, amplitude, modulation, SNR, and severity remain fixed to avoid an unconstrained search. k=0 never reads real fault signals.

No parameter is selected from the old Paderborn test metrics. The final holdout protocol is frozen separately before evaluation; calibration is restricted to its new training fault groups and excludes validation and final-test groups.

Full per-seed evidence, train/validation/test group IDs, and all feature values are in `failure_analysis.json`.
