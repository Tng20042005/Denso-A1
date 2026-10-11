# Datasets và methodology

## CWRU Bearing Data Center

| Thuộc tính | Giá trị đã dùng |
|---|---|
| Official name | CWRU Bearing Data Center, 12 kHz Drive-End subset |
| Source | Các URL official trong `docs/dataset_survey.md` |
| Sensor/channel | Drive-end acceleration (`DE`) |
| Sampling | 12,000 Hz |
| Conditions | Motor load 0/1/2/3 hp, RPM lưu trong file/fallback theo load |
| Faults | Inner race, ball, outer race; seeded EDM fault 0.007 inch; không phải field-natural |
| Registry actually used | 16 Matlab recordings: 4 normal + 12 fault; 3,162,347 raw samples; 762 non-overlapping 4096-sample windows theo file metadata |
| Group | Một raw Matlab file = một immutable group |
| Splits | Random-group và harder cross-load; mọi window của một file cùng partition |
| Runs | 40 rows/protocol = 8 supported arm×k cells × 5 paired seeds |
| License | Official pages không nêu SPDX; raw files không redistribute; cần permission trước external/commercial redistribution |

**Ceiling effect.** Random-group E0 PR-AUC đã `0.9988` ở k=0 và `1.0000` ở k=1/2. Cross-load làm k=0 khó hơn (`0.9288`) nhưng k≥1 E0 vẫn `0.9980`. Vì vậy CWRU hữu ích để kiểm protocol nhưng yếu cho việc phân biệt augmentation utility ở k≥1.

Nguồn size/checksum: `reports/cwru/summary.json`; source registry: `src/denso_a1/data/cwru.py`.

## Paderborn Bearing DataCenter

| Thuộc tính | Giá trị đã dùng |
|---|---|
| Official name | Paderborn University Bearing DataCenter |
| Source | URL official trong `docs/dataset_survey.md` |
| Sensor/channel | `vibration_1` acceleration |
| Sampling | 64,000 Hz |
| Conditions in code | `N15_M07_F10`, `N15_M07_F04`, `N15_M01_F10`, `N09_M07_F10` |
| Bearings | 4 healthy (`K001–K004`) + 6 real accelerated-damage (`KA04/15/16`, `KI04/14/16`) |
| Fault origin | Accelerated degradation / real measured damage; không phải DENSO field-natural fault |
| Repetitions | Measurement indices 1–5; mỗi file khoảng 256k samples; 4096-sample non-overlap windows |
| Group | Bearing ID; tất cả condition/repetition windows của bearing tuân theo split group |
| License | CC BY-NC 4.0, citation required, không commercial redistribution |

Các protocol Paderborn dùng những holdout khác nhau:

| Branch | Train/validation condition | Final/utility condition & bearings | Files/windows in artifact |
|---|---|---|---|
| Original T0 | `N15_M07_F10` | cùng condition, bearing-disjoint thay đổi theo seed | 50 files, 3,101 windows |
| T0-v2 | `N15_M07_F10` | `N09_M07_F10`: `K003, KI14, KI16` | 50 files, 3,102 windows |
| T2 | `N15_M07_F10`, `N15_M07_F04` | `N15_M01_F10`: `K004, KA16, KI04` | 85 files, 5,292 windows |
| T3 | `N15_M07_F10`, `N15_M07_F04` | `N15_M01_F10`: `K001, KA15, KI16` | 85 files, 5,299 windows |

Các window totals trên được tính trực tiếp từ `dataset_files[].n_raw_samples // 4096` trong từng `summary.json`; không phải một pool chung. Không được so absolute PR-AUC giữa các hàng như cùng test set.

## Vì sao Paderborn là external validation

Paderborn có bearing-level grouping, nhiều operating conditions, accelerated-damage recordings và license rõ hơn CWRU. Nó tạo distribution shift và không bị saturation đồng đều, nên phù hợp để kiểm tra claim sau ceiling effect của CWRU.

## Experimental contract

- Split/group freeze trước generation; generated sample không được có val/test parent.
- Preprocessor là global mean/std fit train-only (`SignalPreprocessor`).
- `k=0`: không có real fault group trong train; one-class E0 và physics-only pseudo-fault arm. E1/T2/T3 không được fabricate nếu cần measured fault parent.
- `k=1,2`: số **fault groups** được phép vào train; mọi comparator dùng cùng selected fault groups.
- Generated budget thông thường là 32 samples; E1/E2/E3/E4 budget-matched trong protocol tương ứng.
- Evaluator: Isolation Forest 100 trees cho one-class; Random Forest 120 trees, balanced class weights, min leaf 2 cho supervised. Feature vector gồm RMS, std, crest factor, kurtosis và bốn Welch PSD band energies.
- Primary metric: PR-AUC; secondary: F1, recall@10% FPR, ROC-AUC. F1 dùng threshold bằng median score trên test trong implementation; đây là limitation, không phải deployment threshold.
- Uncertainty: percentile bootstrap 95% CI trên 5 paired-seed values; với n=5, CI chỉ là uncertainty summary nhỏ, không phải bằng chứng population-wide mạnh.

## Leakage và fairness controls

Mỗi raw row lưu train sample IDs, group IDs, class/source counts, sample/signal hash, prediction hash, split/subset/generator/model seed, public-real test audit, group-overlap audit, budget audit và training-difference audit. T0-v2/T2/T3 thêm calibration/provenance/fidelity/memorization artifacts phù hợp.

## Vì sao cần k=0/1/2

- k=0: kiểm tra zero-fault supervision từ normal-only; không được dùng thông tin real fault.
- k=1: cực few-shot, một fault-bearing group.
- k=2: xem thêm một group có làm synthetic candidate hữu ích hơn hay chỉ khuếch đại mismatch.

