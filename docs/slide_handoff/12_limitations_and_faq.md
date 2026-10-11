# Limitations, discrepancies và FAQ

## Scientific limitations

1. Không có DENSO factory data; transfer chưa test.
2. CWRU là seeded EDM faults; Paderborn là accelerated damage, không phải naturally occurring field failures.
3. Chỉ một compact feature-based evaluator family; kết luận có thể phụ thuộc representation/model.
4. Năm paired seeds là tối thiểu; bootstrap CI trên n=5 có độ phân giải thấp.
5. F1 threshold dùng median test score trong code, không phải validation-frozen production threshold.
6. Branch T0/T0-v2/T2/T3 dùng final holdout khác nhau; không có cross-branch head-to-head trên cùng untouched test.
7. Common gate retrospective được viết sau branch outcomes; only SafetyGate-v1 là policy cho future prospective freeze.
8. T0/T0-v2 thiếu independent novelty admission evidence; T0-v2 còn thiếu independent post-change fidelity gate.
9. Corruption ladder là controlled sanity check, không bao quát mọi lỗi của generator.
10. Chưa có beneficial synthetic candidate được gate prospective-accept.

## Document/artifact discrepancies

- Hai ADR có số `010`; dùng full filename để tránh nhầm.
- `docs/handoff/slide_notes.md` là pre-public-real note đã stale; không dùng làm status hiện tại.
- T3 C2ST `≈0.998` là development mean; `1.0` là validation maximum trong retrospective.
- Original T0 Paderborn deltas âm nhưng CI cắt 0; không gọi statistically significant degradation.
- T0-v2 fidelity FAIL trong retrospective nghĩa “không independently passed”, không phải một measured T0-v2 C2ST result.
- Embedded protocol hash khác file-byte hash do self-hash field; authoritative freeze identifier là embedded canonical payload hash.

## FAQ phản biện

### Nếu tất cả candidate đều reject, gate có phải always-reject không?

Không thể kết luận always-reject: matched real-vs-real cho C2ST 0.5085 và spectral similarity rất cao, chứng minh diagnostics có non-rejection reference. Nhưng gate cũng chưa prospective-accept beneficial synthetic candidate; câu trả lời trung thực là “not shown to always reject, acceptance performance not yet established”.

### Vì sao train-vs-validation real C2ST lại 0.9977?

Vì C2ST nhạy với bearing/group domain shift. Đây chính là lý do SafetyGate-v1 dùng reference-relative calibration thay vì universal 0.95.

### T3 có +0.0028, sao vẫn fail?

Success rule yêu cầu hơn cả E0 và E1, không fidelity/novelty failure. T3 k=1 không hơn E1; k=2 không hơn E0/E1; candidate có exact parent overlap/NN=0 và validation separability cao.

### Vì sao T2 bị reject dù không memorize?

Novelty PASS không đủ. T2 C2ST=1.0, spectral mismatch và negative held-out utility; admission là conjunctive.

### T0 cross-load có positive result không?

CWRU cross-load cho positive PR-AUC delta, đặc biệt k=0. Nhưng k≥1 gần ceiling và external Paderborn không xác nhận. Đây là dataset/protocol-specific signal, không phải robust utility claim.

### SafetyGate-v1 threshold đã được validate trên DENSO chưa?

Chưa. Config đã freeze để dùng đúng quy trình trong future validation; DENSO references/holdout chưa tồn tại.

### Có nên thử diffusion/GAN?

Không trong project cycle này. ADR và stop rule đóng generator development; next evidence step là prospective gate/DENSO data, không search architecture để tìm positive result.

### Gate có đảm bảo physical plausibility không?

Không. Nó kiểm một tập signal/provenance/utility criteria. Domain expert review và machine-specific constraints vẫn cần thiết.

