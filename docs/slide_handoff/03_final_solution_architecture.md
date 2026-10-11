# Kiến trúc giải pháp cuối

## Workflow

```text
Candidate synthetic dataset + metadata + parent links
                         |
                         v
1. Provenance / Validity Gate
                         |
                         v
2. Fidelity Gate
                         |
                         v
3. Novelty / Memorization Gate
                         |
                         v
4. Held-out Measured-real Utility Gate
                         |
                         v
Evidence report: ACCEPT only if all PASS; otherwise REJECT
```

Hình chính: `reports/safety_gate_architecture.svg`.

## Gate 1 — Provenance / Validity

- **Mục đích:** xác nhận experiment trả lời đúng câu hỏi trước khi đọc accuracy.
- **Input:** sample metadata, parent IDs/groups, split manifest, source type, budget, raw checksums.
- **Xử lý:** test phải measured `public_real`; train/val/test group overlap rỗng; generated parent chỉ từ train; E1/E2/E3/E4 cùng allowed real fault groups và generated budget; source/hash traceable.
- **Output:** PASS/FAIL/UNKNOWN.
- **Failure example:** generated sample có parent thuộc final test; comparator có thêm real fault group; test chứa generated sample.
- **Giới hạn:** PASS chỉ chứng minh protocol validity, không chứng minh waveform realistic hoặc useful.

## Gate 2 — Fidelity

- **Mục đích:** đo candidate có nằm gần distribution đo thật theo signal statistics liên quan hay không.
- **Input:** candidate signals và measured-real train/validation reference phù hợp condition.
- **Metrics:** PSD cosine/JS, envelope cosine/JS và anchor drift, RMS, kurtosis, crest factor, band energy, C2ST.
- **SafetyGate-v1:** threshold được fit một lần từ ít nhất 5 measured-real reference replicates bằng fixed quantiles/margins trong `configs/safety_gate_v1.json`, trước candidate utility.
- **Failure example:** T0 C2ST `1.0`, PSD cosine `0.5133`, envelope/high-frequency shortcut; T2 C2ST `1.0`.
- **Giới hạn:** C2ST cao có thể phản ánh condition/bearing shift thật; không dùng universal cutoff mù quáng.

## Gate 3 — Novelty / Memorization

- **Mục đích:** ngăn exact duplicate, near-copy hoặc model memorization.
- **Input:** candidate, training parents và real leave-one-out geometry.
- **Metrics:** exact signal hash overlap; generated-to-real nearest-neighbor distance; normalized NN ratio; parent trace.
- **SafetyGate-v1:** exact overlap không được phép; historical NN floor `0.25` vẫn là hard prototype rule và phải freeze trước utility.
- **Failure example:** T3 selected near-identity policy có train-parent NN ratio `0` và exact parent hashes.
- **Giới hạn:** xa parent không có nghĩa là realistic; novelty phải đi cùng fidelity.

## Gate 4 — Downstream Utility

- **Mục đích:** kiểm tra candidate có thật sự giúp detector trên lỗi đo thật chưa từng dùng để tune hay không.
- **Input:** frozen candidate, fixed evaluator/budget/split/seeds; held-out measured-real faults.
- **So sánh:** candidate − E0 real-only và candidate − E1 simple augmentation.
- **Metrics:** PR-AUC/F1, paired deltas và bootstrap 95% CI, ít nhất 5 paired seeds.
- **SafetyGate-v1 PASS:** mean PR-AUC delta >0 và lower 95% CI >0 đối với cả E0 lẫn E1; F1 phải report cùng 95% CI.
- **Failure example:** T2 E3−E0 `-0.0281`/`-0.1002`; T3 không hơn E1.
- **Giới hạn:** một evaluator và n=5 chỉ cung cấp evidence trong frozen protocol, không phải production guarantee.

## State thực tế trong implementation

`src/denso_a1/safety_gate.py` định nghĩa per-gate status: `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`. Candidate-level `admission` chỉ có:

- `ACCEPT`: cả bốn status đều đúng bằng `PASS`.
- `REJECT`: ít nhất một gate không phải PASS, bao gồm UNKNOWN/NOT_APPLICABLE.

Không có state `REVIEW`. Nếu presentation muốn nói “manual review”, phải ghi rõ đó là proposed operational workflow, không phải state hiện có.

## Retrospective và prospective khác nhau

- **Retrospective prototype:** gom bốn frozen branch sau khi utility đã tồn tại; historical thresholds không đồng nhất hoàn toàn; dùng để audit claim và rút ra negative result.
- **Prospective SafetyGate-v1:** reference data, quantile/margin, split, evaluator và utility rule phải freeze trước khi nhìn candidate final-test utility; sau đó mới có thể kiểm định acceptance/rejection trên DENSO.

## Decision table hiện tại

| Candidate | Validity | Fidelity | Novelty | Utility | Decision |
|---|---|---|---|---|---|
| T0 | PASS | FAIL | UNKNOWN | FAIL | REJECT |
| T0-v2 | PASS | FAIL/not independently passed | UNKNOWN | FAIL | REJECT |
| T2 conditional-VAE | PASS | FAIL | PASS | FAIL | REJECT |
| T3 fault-preserving | PASS | FAIL | FAIL | FAIL | REJECT |

Nguồn machine-readable: `reports/safety_gate/retrospective.json`.

