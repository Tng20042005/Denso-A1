# Tóm tắt điều hành

## Kết luận một câu

DENSO-A1 không chứng minh được một fault generator thành công; dự án tạo ra một **generator-agnostic Synthetic Fault Data Safety Gate** để ngăn dữ liệu sinh không đủ bằng chứng đi vào detector training.

## Điều đã được chứng minh trong phạm vi thử nghiệm

- Pipeline public-real, group/bearing-disjoint, budget-matched và đa seed đã chạy trên CWRU/Paderborn; các audit test isolation, leakage và budget đều PASS ở các benchmark được báo cáo.
- CWRU random-group bị ceiling effect: E0 PR-AUC đã khoảng `0.9988–1.0000`, nên không đủ sức phân biệt utility của T0 ở k≥1 (`reports/cwru/summary.json`).
- Trên Paderborn, T0 có PR-AUC delta âm nhưng CI còn cắt 0; T0-v2 và T2 có suy giảm rõ ở các comparison chính. T3 chỉ tăng rất nhỏ so với E0 tại k=1 (`+0.0028`) nhưng không hơn E1, không cải thiện tại k=2, đồng thời fail fidelity/novelty (`reports/*/summary.json`).
- Retrospective common gate reject T0, T0-v2, T2 và T3. Đây là kết luận về bốn candidate/protocol đã thử, không phải định luật rằng synthetic fault data luôn vô ích.
- SafetyGate diagnostics hoạt động hợp lý trên matched real-vs-real và đa số corruption ladder. Tuy nhiên gate chưa từng prospective-accept một candidate synthetic có utility dương; predictive acceptance vẫn chưa được chứng minh.

## Final proposed solution

Một candidate synthetic dataset chỉ được admit khi cả bốn lớp đều PASS:

1. **Provenance / Validity:** measured-real test isolation, không parent leakage, budget fair, traceability đầy đủ.
2. **Fidelity:** PSD, envelope spectrum, RMS/kurtosis/crest factor và C2ST so với measured-real reference.
3. **Novelty:** nearest-neighbor geometry, exact hash và near-copy/memorization.
4. **Utility:** paired evaluation trên held-out measured-real faults, so với E0 real-only và E1 simple augmentation, tối thiểu 5 paired seeds, PR-AUC/F1 và 95% CI.

`UNKNOWN` không được xem là PASS. Candidate-level output hiện tại là `ACCEPT` hoặc `REJECT`.

## Thông điệp presentation nên dùng

> Across the tested CWRU/Paderborn few-shot settings, four representative synthesis/augmentation strategies failed to simultaneously satisfy fidelity, novelty and held-out real-fault utility requirements. A generator-agnostic admission gate prevented unsupported synthetic-data claims and identifies when generated fault data should not be used.

## Không được tuyên bố

- SafetyGate làm detector chính xác hơn hoặc giảm downtime.
- Synthetic fault data nói chung là vô ích.
- Gate đã dự đoán được mọi candidate có utility hay đã prospective-accept candidate tốt.
- Kết quả public benchmark chuyển trực tiếp sang DENSO.
- Paderborn/CWRU là dữ liệu DENSO hoặc naturally occurring field faults.

## Readiness

Research/evidence package: **ready with explicit limitations**. Competition submission: **conditional**, còn cần Team Lead xác nhận format, deadline, số slide, thời lượng, rubric, link policy, repository/tag và quyền dùng hình/dataset trong submission.

