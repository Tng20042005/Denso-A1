# DENSO-A1 — bộ bàn giao cho nhóm slide

Bộ tài liệu này là nguồn bàn giao cuối cùng cho câu chuyện **Synthetic Fault Data Safety Gate**. Nội dung được khóa từ các raw artifact hiện có; không có thí nghiệm mới, không sửa kết quả đã freeze và không giả định đây là dữ liệu nhà máy DENSO.

## Cách đọc nhanh

1. Đọc `MASTER_HANDOFF.md` để có câu chuyện độc lập, đủ dùng cho presentation.
2. Dùng `09_slide_by_slide_content.md` để soạn 10–12 slide khái niệm.
3. Lấy hình từ `10_figures_inventory.md`; lấy số từ `05_all_experimental_results.md`.
4. Kiểm từng claim trong `11_claim_evidence_matrix.md` trước khi đưa lên slide.
5. Chốt các mục còn thiếu trong `13_submission_readiness.md` với Team Lead/Slide Owner.

## Danh mục

| Tệp | Mục đích |
|---|---|
| `00_executive_summary.md` | Kết luận và thông điệp cần giữ |
| `01_problem_and_motivation.md` | Bài toán công nghiệp, động lực và câu hỏi nghiên cứu |
| `02_complete_research_journey.md` | Toàn bộ hành trình T0 → T0-v2 → T2 → T3 → SafetyGate-v1 |
| `03_final_solution_architecture.md` | Kiến trúc bốn gate và state thực tế trong code |
| `04_datasets_and_methodology.md` | CWRU, Paderborn, split, evaluator, metric, audit |
| `05_all_experimental_results.md` | Bảng kết quả hợp nhất, kèm nguồn chính xác |
| `06_safety_gate_validation.md` | Real-vs-real, corruption ladder, utility association, threshold audit |
| `07_scientific_contributions.md` | Đóng góp theo mức evidence |
| `08_denso_industrial_roadmap.md` | Lộ trình tích hợp DENSO mang tính đề xuất |
| `09_slide_by_slide_content.md` | Nội dung 12 slide gợi ý, không phải yêu cầu chính thức |
| `10_figures_inventory.md` | Inventory hình và cách dùng |
| `11_claim_evidence_matrix.md` | Claim–evidence matrix dành riêng cho slide |
| `12_limitations_and_faq.md` | Giới hạn, discrepancy và câu hỏi phản biện |
| `13_submission_readiness.md` | Readiness, checklist và xác nhận còn thiếu |

## Quy tắc nguồn

- Raw JSON/CSV là nguồn số liệu ưu tiên; Markdown report là lớp diễn giải.
- Không so trực tiếp số tuyệt đối giữa các holdout khác nhau.
- `k` là số **fault-bearing/fault-recording groups** được phép vào train, không phải số window.
- `public_real` nghĩa là tín hiệu đo công khai; không đồng nghĩa với DENSO hoặc field-natural fault.
- Trạng thái candidate ở implementation hiện tại chỉ là `ACCEPT`/`REJECT`; từng gate có `PASS`/`FAIL`/`UNKNOWN`/`NOT_APPLICABLE`. Không có state `REVIEW`.

