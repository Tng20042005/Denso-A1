# Hành trình nghiên cứu đầy đủ

## Phase 1 — T0 physics-informed fault injection

**Mục tiêu/hypothesis.** Tạo mechanism-like waveform từ normal signal bằng periodic impulses, jitter, damped resonance, amplitude modulation và controlled noise; kỳ vọng cải thiện detector khi fault groups khan hiếm.

**Thiết kế.** E0 real-only, E1 simple augmentation, E2 T0; `k={0,1,2}`; 5 paired seeds; 4096-sample non-overlapping windows; same evaluator/budget; test measured public-real only. CWRU dùng random-group rồi cross-load; Paderborn dùng bearing-disjoint tại `N15_M07_F10`.

**Kết quả.** CWRU random-group gần bão hòa; cross-load có k=0 PR-AUC delta `+0.0634 [0.0003, 0.1419]` nhưng k≥1 chỉ khoảng `+0.0020` và baseline gần 1.0. External Paderborn cho E2−E0 PR-AUC `-0.0463`, `-0.0559`, `-0.0652` ở k=0/1/2, các CI đều cắt 0. Failure analysis: C2ST `1.0000`; JS `0.1860`; PSD cosine `0.5133`; generated kurtosis/crest factor khoảng `19.8/9.0` so với real `5.1/5.6`; envelope peak generated `223 Hz` so với real khoảng `102 Hz`; excess high-frequency energy khoảng 8–10 dB.

**Điều hoạt động.** Reproducibility, provenance, data split, budget/training-set-difference audits và mechanism/property guards.

**Điều thất bại.** Distribution fidelity và robust held-out utility. CWRU không đủ phân giải method ở k≥1; Paderborn không ủng hộ utility.

**Quyết định.** Chỉ cho phép một lần sửa tối thiểu có căn cứ; không tune theo old test. Nguồn: `reports/cwru/summary.json`, `reports/cwru_cross_load/summary.json`, `reports/paderborn/summary.json`, `reports/t0_failure_analysis/failure_analysis.json`.

## Phase 2 — T0-v2 calibrated physics synthesis

**Mục tiêu/hypothesis.** Sửa ba mismatch đã chẩn đoán mà không mở parameter search: defaults 100 Hz/5 kHz, Gaussian impulse smoothing width 8, và k≥1 calibration của `f_fault`/`f_res` chỉ từ selected train fault groups; k=0 physics-only.

**Thiết kế.** Freeze hash `5232deca...f19e9`; train/val ở `N15_M07_F10`; final test bearing/condition-disjoint ở `N09_M07_F10`, bearings `K003, KI14, KI16`; 5 paired seeds; E0/E1/E2.

**Kết quả chính.** E2−E0 PR-AUC: k=0 `-0.0196 [-0.0838, 0.0398]`; k=1 `-0.1573 [-0.1850, -0.1208]`; k=2 `-0.2517 [-0.2942, -0.1898]`. F1 cũng giảm mạnh tại k=1/2. Tất cả validity/calibration audit PASS.

**Điều hoạt động.** Pre-final freeze, train-only calibration, untouched condition-disjoint final holdout.

**Điều thất bại.** Utility. T0-v2 không có independent frozen fidelity/NN gate đủ để chứng minh đã sửa mismatch; retrospective giữ fidelity FAIL/not independently passed và novelty UNKNOWN.

**Quyết định.** Đóng nhánh T0/T0-v2; pivot một lần sang learned synthesis. Nguồn: `reports/paderborn_v2/summary.json`, `reports/paderborn_v2/protocol_freeze.json`, ADR-008.

## Phase 3 — T2 conditional 1D VAE

**Mục tiêu/hypothesis.** Learned conditional model có thể học fault distribution tốt hơn hand-designed physics trong k≥1.

**Thiết kế.** Lightweight 1D VAE, conditioned on speed/torque/radial force, train chỉ từ allowed train fault groups ở `N15_M07_F10` và `N15_M07_F04`; final holdout `N15_M01_F10`, bearings `K004, KA16, KI04`; 32 generated samples/arm; E0/E1/E2/E3; không có E3 ở k=0. Freeze hash `64e6e406...c52d8`.

**Kết quả.** C2ST `1.0` ở mọi train/validation case; aggregate PSD JS `0.1740`, cosine `0.5574`; memorization audit PASS, minimum NN ratio `0.4520`. E3−E0 PR-AUC k=1 `-0.0281 [-0.0309, -0.0254]`, k=2 `-0.1002 [-0.1103, -0.0900]`; E3−E1 cũng âm.

**Điều hoạt động.** Leakage/budget/calibration/NN audit; conditional training boundary; no exact-copy failure.

**Điều thất bại.** Real-vs-generated separability, spectral/envelope fidelity và downstream utility.

**Quyết định.** Đóng VAE; không diffusion/GAN. Nguồn: `reports/t2_benchmark/summary.json`, `reports/t2_benchmark/raw_metrics.json`, `reports/t2_benchmark/t2_fidelity_report.md`, ADR-009.

## Phase 4 — T3 fault-preserving augmentation

**Mục tiêu/hypothesis.** Conservative transforms của measured faults có thể giữ real manifold tốt hơn raw waveform generation.

**Thiết kế.** Chỉ k≥1. Candidate operators: amplitude, temporal shift, measured-normal-floor noise, bounded phase/spectral perturbation, condition-aware time scaling, envelope-preserving perturbation. Selection chỉ trên train/validation. Tất cả 12 policy thử đều fail development gate; `time_scale` có score thấp nhất được giữ để diagnostic final comparison. New holdout `N15_M01_F10`, bearings `K001, KA15, KI16`; E0–E4; freeze hash `7fa7e9f6...b2dab`.

**Kết quả.** Validation C2ST tối đa `1.0`; PSD JS trung bình `0.09935`, cosine `0.73183`; train-parent exact overlap và NN ratio `0` tạo novelty failure. E4−E0: k=1 `+0.0028 [0.0018, 0.0041]`, k=2 `-0.0002 [-0.0105, 0.0080]`; E4−E1 âm/CI cắt 0 ở cả hai k. Không có E4 k=0.

**Điều hoạt động.** Provenance parent-level, conservative selection boundary và correct refusal to fabricate k=0.

**Điều thất bại.** Không đồng thời đạt fidelity, novelty và utility hơn E0/E1.

**Quyết định.** Dừng raw-data augmentation/generation; không thử thêm architecture. Nguồn: `reports/t3_development/raw_development.json`, `reports/t3_benchmark/summary.json`, `reports/t3_benchmark/raw_metrics.json`, ADR T3.

## Phase 5 — Generator-agnostic Safety Gate

**Mục tiêu.** Chuyển synthetic data từ “output phải bảo vệ” thành “optional input phải đủ evidence”.

**Cơ chế.** Common interface gồm provenance/validity, fidelity, novelty và utility. Missing evidence là UNKNOWN; candidate chỉ ACCEPT khi mọi gate PASS.

**Retrospective outcome.** T0: PASS/FAIL/UNKNOWN/FAIL; T0-v2: PASS/FAIL/UNKNOWN/FAIL; T2: PASS/FAIL/PASS/FAIL; T3: PASS/FAIL/FAIL/FAIL. Cả bốn REJECT. Nguồn: `reports/safety_gate/retrospective.json`.

**Giới hạn.** Common cross-branch interface được viết sau các frozen utility artifacts; nó là retrospective/prototype, không phải proof về prospective predictive performance.

## Phase 6 — SafetyGate-v1 validation và freeze

**Mục tiêu.** Kiểm tra gate không chỉ “always reject” và làm rõ threshold provenance.

**Thiết kế.** Paderborn train/validation faults only; matched real-vs-real; bearing-disjoint real-vs-real; 5 corruption families × 5 severity = 25 rows; join 18 frozen candidate/config rows. Không load final test, không dùng corruptions để train detector.

**Kết quả.** Matched real-vs-real: C2ST `0.5085`, PSD cosine `0.9967`, JS `0.0013`. Train-vs-validation: C2ST `0.9977`, cosine `0.9169`, JS `0.0230`, chứng minh natural group shift có thể làm C2ST cao. Spectral JS/cosine biến đổi nhất quán theo severity ở cả 5 corruption family; C2ST của envelope distortion mixed.

**Freeze.** SafetyGate-v1 chuyển fidelity sang dataset/reference-relative calibration; utility yêu cầu ≥5 paired seeds và lower 95% CI >0 so với cả E0/E1. Protocol canonical payload hash: `1d07f943790646b312be2f427a5cec24c07b25f0b5e6dd7c4dea65f6998fb5d5`.

**Kết luận.** Validation PASS cho diagnostic behavior/threshold transparency; chưa chứng minh reliable acceptance của beneficial synthetic candidate. Nguồn: `reports/safety_gate_validation_reference.json`, hai CSV validation, ADR-011, `configs/safety_gate_v1.json`.

