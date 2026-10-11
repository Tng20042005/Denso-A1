# Submission readiness

## Assessment

| Area | Status | Evidence/action |
|---|---|---|
| Research narrative | READY | negative journey và final safety-gate contribution nhất quán |
| Numerical traceability | READY | master table trỏ raw JSON/CSV; key values verified |
| Architecture visual | READY | `reports/safety_gate_architecture.svg` |
| Validation visual | READY | `reports/safety_gate_validation_figure.svg` |
| Claim boundaries | READY | slide-specific claim matrix và FAQ |
| DENSO transfer evidence | NOT AVAILABLE | phải trình bày future roadmap, không result |
| Prospective gate acceptance | NOT AVAILABLE | chưa có beneficial candidate prospective test |
| Official competition compliance | NEEDS TEAM LEAD | official brief chưa có trong repo |
| Clean reproducible release/tag | NEEDS TEAM LEAD | toàn repository hiện xuất hiện untracked trong git status; cần owner xác định release strategy |

## Team Lead/Slide Owner phải xác nhận

1. Deadline, số slide, thời lượng, ngôn ngữ và format nộp.
2. Rubric: prototype/GitHub/demo/hardware/evaluator có bắt buộc không.
3. Giới hạn link/citation và ba nguồn nền nào được phép dùng.
4. Repository/tag/commit chính thức dùng cho submission; quyền public source code.
5. Quyền dùng/redistribute screenshot/derived figures từ CWRU/Paderborn; Paderborn là CC BY-NC 4.0, CWRU không có SPDX rõ trong source page.
6. Có cho phép trình bày negative-result/safety contribution theo rubric hay cần framing khác nhưng vẫn trung thực.
7. DENSO brand, NDA, data-security language và người phê duyệt industrial roadmap.
8. Có cần live demo; nếu có, ai chịu trách nhiệm và môi trường nào được support.
9. Citation/authorship/contact metadata cuối cùng.

## Checklist trước xuất slide

- [ ] Mọi metric trên slide xuất hiện trong `05_all_experimental_results.md` và raw source tương ứng.
- [ ] Mỗi chart ghi dataset, holdout, k, n=5 và comparator.
- [ ] Không gộp branch holdouts như một common test.
- [ ] CWRU ghi “seeded physical”; Paderborn ghi “accelerated damage”; không ghi DENSO.
- [ ] Negative/UNKNOWN labels còn nguyên.
- [ ] Validation figure caption nói corruption diagnostic-only.
- [ ] Embedded protocol hash được ghi đúng, không nhầm file-byte SHA.
- [ ] Không dùng stale `docs/handoff/slide_notes.md` làm current status.
- [ ] Không nói ACCEPT/REVIEW nếu code chỉ tạo ACCEPT/REJECT.
- [ ] Team Lead ký xác nhận official competition requirements.

## Final decision

**Research handoff: READY. Submission package: CONDITIONALLY READY.** Có đủ evidence và narrative để slide team soạn bài; chưa thể gọi “submission-ready” theo nghĩa thủ tục cho đến khi các mục official brief/release/license ở trên được xác nhận.

