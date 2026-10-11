# Toàn bộ kết quả thực nghiệm

## Quy ước đọc bảng

- `n=5` là năm paired seeds/runs trong mỗi arm×k cell.
- PR-AUC/F1 là mean của arm trên holdout tương ứng; delta là paired candidate − comparator.
- Không so absolute score giữa các protocol/holdout khác nhau.
- Raw `summary.json` là nguồn số ưu tiên. Các số dưới đây được chép từ raw artifact, làm tròn 4 chữ số.

## A. T0 — original physics synthesis

### CWRU random-group: ceiling diagnostic

| k | Arm | PR-AUC [95% CI] | F1 [95% CI] | E2−E0 PR-AUC / F1 | Source |
|---:|---|---|---|---|---|
| 0 | E0 | 0.9988 [0.9965,1.0000] | 0.8328 [0.7945,0.9082] | — | `reports/cwru/summary.json` |
| 0 | E2 | 1.0000 [1.0000,1.0000] | 0.6517 [0.4966,0.8457] | +0.0012 [0.0000,0.0035] / −0.1811 [−0.2985,−0.0619] | `reports/cwru/summary.json` |
| 1 | E0/E1/E2 | 1.0000 [≈1.0000,1.0000] | 0.5957 [0.4957,0.7940] | 0.0000 / 0.0000 | `reports/cwru/summary.json` |
| 2 | E0/E1/E2 | 1.0000 [1.0000,1.0000] | 0.5957 [0.4957,0.7940] | 0.0000 / 0.0000 | `reports/cwru/summary.json` |

Kết luận: validity PASS nhưng benchmark không phân giải utility ở k≥1. Training-set-difference audit xác nhận arms thực sự khác signal/sample hashes; metric giống nhau không phải do T0/T1 bị bỏ khỏi train.

### CWRU cross-load: harder nhưng vẫn gần ceiling ở k≥1

| k | E0 PR-AUC/F1 | E2 PR-AUC/F1 | E2−E0 PR-AUC [95% CI] | E2−E0 F1 [95% CI] | Source |
|---:|---|---|---|---|---|
| 0 | 0.9288 / 0.8354 | 0.9922 / 0.7458 | +0.0634 [0.0003,0.1419] | −0.0896 [−0.3211,0.1435] | `reports/cwru_cross_load/summary.json` |
| 1 | 0.9980 / 0.7535 | 1.0000 / 0.8375 | +0.0020 [0.0000,0.0060] | +0.0840 [0.0057,0.1856] | `reports/cwru_cross_load/summary.json` |
| 2 | 0.9980 / 0.8187 | 1.0000 / 0.8369 | +0.0020 [0.0000,0.0060] | +0.0182 [−0.0226,0.0772] | `reports/cwru_cross_load/summary.json` |

Đây là CWRU-only signal, không override external Paderborn negative evidence.

### External Paderborn T0

| k | Candidate/comparator | Candidate PR-AUC/F1 | Comparator PR-AUC/F1 | Paired PR-AUC delta [95% CI] | Paired F1 delta [95% CI] | Source |
|---:|---|---|---|---|---|---|
| 0 | E2−E0 | 0.7911 / 0.7813 | 0.8375 / 0.6647 | −0.0463 [−0.2453,0.1400] | +0.1167 [−0.0152,0.3029] | `reports/paderborn/summary.json` |
| 1 | E2−E0 | 0.7747 / 0.6495 | 0.8306 / 0.6930 | −0.0559 [−0.1882,0.0511] | −0.0435 [−0.1687,0.0817] | `reports/paderborn/summary.json` |
| 1 | E2−E1 | 0.7747 / 0.6495 | 0.8237 / 0.6933 | −0.0491 [−0.1886,0.0573] | −0.0437 [−0.1693,0.0818] | `reports/paderborn/summary.json` |
| 2 | E2−E0 | 0.7720 / 0.7229 | 0.8371 / 0.7451 | −0.0652 [−0.2046,0.0148] | −0.0222 [−0.1013,0.0285] | `reports/paderborn/summary.json` |
| 2 | E2−E1 | 0.7720 / 0.7229 | 0.8466 / 0.7544 | −0.0747 [−0.2094,0.0030] | −0.0315 [−0.1055,0.0107] | `reports/paderborn/summary.json` |

Không gọi các delta trên là statistically established harm vì CI cắt 0. Utility không được support vì không có reproducible positive delta.

### T0 fidelity

| Metric | Value | Source |
|---|---:|---|
| C2ST ROC-AUC | 1.0000 [1.0000,1.0000] | `reports/t0_failure_analysis/failure_analysis.json`, key `summary.groups.k=0:dev_fault` |
| Spectral JS | 0.185959 [0.127955,0.242062] | `reports/t0_failure_analysis/failure_analysis.json`, key `summary.groups.k=0:dev_fault` |
| PSD cosine | 0.513255 [0.418315,0.617341] | `reports/t0_failure_analysis/failure_analysis.json`, key `summary.groups.k=0:dev_fault` |
| Real/generated envelope peak | 101.59 / 223.17 Hz | `reports/t0_failure_analysis/failure_analysis.json`, key `summary.groups.k=0:dev_fault` |
| Real/generated kurtosis | 5.089 / 19.754 | `reports/t0_failure_analysis/failure_analysis.json`, key `summary.groups.k=0:dev_fault` |
| Real/generated crest factor | 5.626 / 8.998 | `reports/t0_failure_analysis/failure_analysis.json`, key `summary.groups.k=0:dev_fault` |

Audit: provenance/validity PASS; fidelity FAIL; novelty UNKNOWN; utility FAIL; decision REJECT (`reports/safety_gate/retrospective.json`).

## B. T0-v2 — calibrated physics

Protocol: Paderborn train/val `N15_M07_F10`; final `N09_M07_F10`; 40 rows; 5 paired seeds; freeze `5232deca09ddc0ab1f80ff280e5e03577c5ecee25745721a5fa72139fa3f19e9`.

| k | Candidate/comparator | Candidate PR-AUC/F1 | Comparator PR-AUC/F1 | Paired PR-AUC delta [95% CI] | Paired F1 delta [95% CI] | Source |
|---:|---|---|---|---|---|---|
| 0 | E2−E0 | 0.5612 / 0.5708 | 0.5808 / 0.4739 | −0.0196 [−0.0838,0.0398] | +0.0969 [−0.1153,0.3091] | `reports/paderborn_v2/summary.json` |
| 1 | E2−E0 | 0.5535 / 0.4596 | 0.7108 / 0.7995 | −0.1573 [−0.1850,−0.1208] | −0.3399 [−0.3980,−0.2760] | `reports/paderborn_v2/summary.json` |
| 1 | E2−E1 | 0.5535 / 0.4596 | 0.7101 / 0.7995 | −0.1566 [−0.1840,−0.1216] | −0.3399 [−0.3980,−0.2760] | `reports/paderborn_v2/summary.json` |
| 2 | E2−E0 | 0.7483 / 0.7085 | 1.0000 / 0.9355 | −0.2517 [−0.2942,−0.1898] | −0.2270 [−0.2830,−0.1711] | `reports/paderborn_v2/summary.json` |
| 2 | E2−E1 | 0.7483 / 0.7085 | 1.0000 / 0.9842 | −0.2517 [−0.2942,−0.1898] | −0.2757 [−0.2989,−0.2491] | `reports/paderborn_v2/summary.json` |

Audit: public-real/leakage/budget/training-difference/calibration PASS; independent T0-v2 fidelity proof absent; novelty UNKNOWN; utility FAIL; REJECT.

## C. T2 — conditional 1D VAE

Protocol: Paderborn final `N15_M01_F10`, bearings `K004, KA16, KI04`; 50 raw run rows; 5 paired seeds; E3 chỉ k=1/2; freeze `64e6e406da77011eae9305037c2feea6ba04c42e0767021d25967f21ee5c52d8`.

| k | Candidate/comparator | Candidate PR-AUC/F1 | Comparator PR-AUC/F1 | Paired PR-AUC delta [95% CI] | Source |
|---:|---|---|---|---|---|
| 1 | E3−E0 | 0.9431 [0.9353,0.9503] / 0.7977 [0.7874,0.8088] | 0.9712 / 0.8525 | −0.0281 [−0.0309,−0.0254] | `reports/t2_benchmark/summary.json` |
| 1 | E3−E1 | same E3 | 0.9735 / 0.8571 | −0.0304 [−0.0353,−0.0255] | `reports/t2_benchmark/summary.json` |
| 2 | E3−E0 | 0.7259 [0.7124,0.7391] / 0.6097 [0.5804,0.6280] | 0.8261 / 0.6269 | −0.1002 [−0.1103,−0.0900] | `reports/t2_benchmark/summary.json` |
| 2 | E3−E1 | same E3 | 0.8082 / 0.6260 | −0.0823 [−0.1001,−0.0620] | `reports/t2_benchmark/summary.json` |

Raw summary không lưu paired F1 deltas cho T2; chỉ arm-level F1 CI và paired PR-AUC delta. Không được tự suy paired F1 CI.

Fidelity/novelty: C2ST max `1.0`; mean PSD JS `0.173952`; mean cosine `0.557389`; min NN ratio `0.452015`; exact-copy/memorization audit PASS. Nguồn aggregate: `reports/safety_gate/retrospective.json`; row-level: `reports/t2_benchmark/raw_metrics.json`.

Audit: validity PASS; fidelity FAIL; novelty PASS; utility FAIL; REJECT.

## D. T3 — fault-preserving augmentation

Protocol: Paderborn final `N15_M01_F10`, bearings `K001, KA15, KI16`; 60 raw rows; 5 paired seeds; E4 chỉ k=1/2; selected `time_scale`; freeze `7fa7e9f66bab0965d7de086570ac18f16ddefd8c09ce53d7e943ea73bb5b2dab`.

| k | Candidate/comparator | Candidate PR-AUC/F1 | Comparator PR-AUC/F1 | Paired PR-AUC delta [95% CI] | Source |
|---:|---|---|---|---|---|
| 1 | E4−E0 | 0.9794 [0.9760,0.9838] / 0.8327 [0.8301,0.8363] | 0.9766 / 0.8334 | +0.0028 [0.0018,0.0041] | `reports/t3_benchmark/summary.json` |
| 1 | E4−E1 | same E4 | 0.9801 / 0.8325 | −0.0007 [−0.0016,0.0002] | `reports/t3_benchmark/summary.json` |
| 2 | E4−E0 | 0.9226 [0.9180,0.9283] / 0.8653 [0.8573,0.8750] | 0.9228 / 0.8673 | −0.0002 [−0.0105,0.0080] | `reports/t3_benchmark/summary.json` |
| 2 | E4−E1 | same E4 | 0.9233 / 0.8660 | −0.0007 [−0.0022,0.0007] | `reports/t3_benchmark/summary.json` |

Raw summary không lưu paired F1 deltas cho T3. Fidelity: validation C2ST max `1.0`; mean JS `0.099352`; mean cosine `0.731828`; mean anchor drift `3.613 Hz`. Novelty: validation min NN ratio `1.304`, nhưng train-parent NN ratio `0` và exact hash overlap làm novelty FAIL. Nguồn: `reports/t3_benchmark/raw_metrics.json`, `reports/safety_gate/retrospective.json`.

Audit: validity/provenance PASS; fidelity FAIL; novelty FAIL; utility FAIL theo joint rule; REJECT.

## E. Slide-ready final table

| Branch | Validity | Fidelity | Novelty | Held-out utility evidence | Admission |
|---|---|---|---|---|---|
| T0 physics | PASS | FAIL: C2ST 1.0; JS 0.186; cosine 0.513 | UNKNOWN | Paderborn deltas âm/near-zero, CI cắt 0 | REJECT |
| T0-v2 | PASS | FAIL/not independently passed | UNKNOWN | k1 −0.1573; k2 −0.2517 vs E0 | REJECT |
| T2 cVAE | PASS | FAIL: C2ST 1.0 | PASS | k1 −0.0281; k2 −0.1002 vs E0 | REJECT |
| T3 transforms | PASS | FAIL: validation C2ST max 1.0 | FAIL: parent exact/NN=0 | +0.0028 at k1 vs E0, but not vs E1; k2 ≈0 | REJECT |

## F. Discrepancies phải công khai

1. Có hai file mang số ADR-010: một cho T3 và một cho Safety Gate. Đây là naming conflict, không phải hai phiên bản cùng decision.
2. `docs/handoff/slide_notes.md` là artifact cũ nói bước tiếp theo mới là public-real validation; trạng thái đó đã bị supersede bởi README/FinalPlan addendum/ADR-010/011.
3. README vẫn gọi CWRU là “current primary dataset”, đúng theo ADR-002 lịch sử; final contribution lại dựa phần lớn vào external Paderborn vì CWRU ceiling. Hai câu không mâu thuẫn nếu ghi rõ chronology.
4. T3 report dùng `≈0.998` khi nói development mean C2ST; retrospective dùng validation maximum `1.0`. Đây là khác aggregation, không phải raw conflict.
5. T0-v2 bị common gate gán fidelity FAIL dựa trên “không independently passed/inherited family mismatch”; không có T0-v2 C2ST artifact riêng. Không được trình bày như đã đo C2ST=1.0 cho chính T0-v2.
6. Validation protocol embedded hash là canonical payload SHA; byte-level SHA của JSON đã thêm hash là `51746d...c2961f`. Cần gọi đúng loại hash.
