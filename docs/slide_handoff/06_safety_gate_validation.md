# Validation của SafetyGate-v1

## Boundary

Validation này không tạo generator mới. Nó dùng Paderborn measured-real train/validation fault groups ở `N15_M07_F10`, 128 windows mỗi population. Final test không được load; corruption outputs không dùng để train detector hay claim utility.

Canonical protocol payload SHA256 được nhúng trong artifact:

`1d07f943790646b312be2f427a5cec24c07b25f0b5e6dd7c4dea65f6998fb5d5`

Đã đối chiếu với `reports/safety_gate_validation_protocol.json` và `reports/safety_gate_validation_reference.json`. Byte SHA của chính JSON khác vì file chứa thêm trường `protocol_sha256`; đây là expected self-hash distinction.

## 1. Matched real-vs-real control

| Metric | Value | Source |
|---|---:|---|
| C2ST ROC-AUC | 0.5085 | `reports/safety_gate_validation_reference.json`, `matched_train_vs_train` |
| PSD cosine | 0.9967 | `reports/safety_gate_validation_reference.json`, `matched_train_vs_train` |
| Spectral JS | 0.0013 | `reports/safety_gate_validation_reference.json`, `matched_train_vs_train` |
| Envelope cosine / JS | 0.9961 / 0.0011 | `reports/safety_gate_validation_reference.json`, `matched_train_vs_train` |
| NN median ratio | 1.3003 | `reports/safety_gate_validation_reference.json`, `matched_train_vs_train` |
| Exact hash overlap | 0 | `reports/safety_gate_validation_reference.json`, `matched_train_vs_train` |

**Ý nghĩa:** metric có non-rejection reference; matched measured-real halves gần chance-level theo C2ST và rất gần theo spectrum. **Giới hạn:** đây không phải synthetic candidate và không phải proof gate sẽ accept useful synthetic data. Anchor drift `69.34 Hz` còn vượt historical absolute `50 Hz`, cho thấy cutoff cũ không universal.

## 2. Train-vs-validation real domain shift

| Metric | Value | Source |
|---|---:|---|
| C2ST ROC-AUC | 0.9977 | `reports/safety_gate_validation_reference.json`, `train_vs_validation` |
| PSD cosine | 0.9169 | `reports/safety_gate_validation_reference.json`, `train_vs_validation` |
| Spectral JS | 0.0230 | `reports/safety_gate_validation_reference.json`, `train_vs_validation` |
| Envelope cosine / JS | 0.9577 / 0.0088 | `reports/safety_gate_validation_reference.json`, `train_vs_validation` |
| RMS/kurtosis/crest standardized gap | −0.9622 / −0.5843 / −0.5457 | `reports/safety_gate_validation_reference.json`, `train_vs_validation` |

**Ý nghĩa:** bearing/group shift thật có thể làm C2ST gần 1 dù PSD vẫn tương đối gần. Vì vậy universal C2ST≤0.95 sẽ reject cả real shifted population. Candidate phải so với reference phù hợp condition/group shift.

## 3. Controlled corruption ladder

- 5 corruption families: band-limited noise, frequency-anchor shift, spectral distortion, impulse sharpening, envelope distortion.
- 5 levels `{0,0.1,0.25,0.5,1.0}` → 25 configurations.
- Spectral JS tăng và PSD cosine giảm nhất quán ở tất cả family (`adjacent fraction=1.0`, |rho|=1.0).
- Frequency shift và impulse sharpening có C2ST trend nhất quán; noise/spectral distortion 0.75 adjacent fraction; envelope distortion C2ST chỉ 0.50, được ghi là mixed.
- Envelope-anchor drift nhất quán theo report, nhưng metric này noisy ở real reference; không được dùng một mình.

Nguồn: `reports/safety_gate_corruption_ladder.csv`, summary trong `reports/safety_gate_validation.md`.

**Ý nghĩa:** diagnostics phản ứng theo controlled degradation, đặc biệt spectral metrics. **Giới hạn:** corruption là diagnostic-only, không đại diện đầy đủ mọi generator failure và không chứng minh causal prediction của downstream utility.

## 4. Gate versus downstream utility

`reports/safety_gate_utility_association.csv` có 18 frozen method/config rows: 5 T0, 5 T0-v2, 4 T2, 4 T3. Các utility values có từ untouched measured-real holdout của từng branch; gate metrics không đồng nhất hoàn toàn giữa historical branches.

- T0/T0-v2/T2 có negative held-out deltas trong frozen comparison chính.
- T3 có k=1 positive nhỏ vs E0 nhưng không hơn E1, k=2 không dương, đồng thời fail fidelity/novelty.
- C2ST của available synthetic candidates đều gần/đúng 1, nên không có variance đủ để claim correlation mạnh.
- N=18 là config rows có phụ thuộc theo method/k/comparator, không phải 18 independent generators.

Kết luận được phép: rejection **đồng hướng** với no-benefit/harm evidence của bốn branch. Không được nói gate đã statistically predict utility.

## 5. Threshold provenance audit

| Rule | Timing/rationale | Loại |
|---|---|---|
| C2ST ≤0.95 | frozen trước final T2/T3 utility, informed by development diagnostics | historical absolute, dataset-dependent |
| JS ≤0.25; PSD cosine ≥0.65 | frozen trước T3 final | historical absolute |
| Anchor drift ≤50 Hz | frozen trước T3 final | historical absolute Hz |
| NN ratio ≥0.25; no exact hash | frozen trước T2/T3 final | hard prototype novelty rule |
| Validity/budget/provenance PASS | protocol invariant trước final runs | hard boolean |
| Utility mean delta >0 | common retrospective interface viết sau artifacts | retrospective/prototype |
| v1 utility lower CI >0 vs E0 và E1 | frozen cho future DENSO | prospective rule |

Không threshold nào được đổi để “làm bốn method fail” sau final test; nhưng common cross-branch gate được assembled retrospectively, nên phải gắn nhãn prototype.

## 6. SafetyGate-v1 freeze

Config: `configs/safety_gate_v1.json`; byte SHA256 `f93c0bac6cf1a5dd8fb77ec57f441edb992a3919b11edfa024e1d3b5b89cb435`.

- Ít nhất 5 measured-real reference replicates.
- Quantile range 0.05/0.95 và fixed margins: C2ST 0.05, JS/cosine/envelope cosine 0.05, envelope peak 15 Hz, feature gap 0.5.
- Candidate utility không được nhìn trước calibration/freeze.
- Missing diagnostic = UNKNOWN, không PASS.
- Acceptance yêu cầu mọi gate PASS; utility lower 95% CI >0 so với cả E0/E1.

## Readiness decision

Safety-gate contribution đạt yêu cầu để kể câu chuyện về **diagnostic behavior, transparent threshold provenance và disciplined rejection**. Chưa đạt bằng chứng cho “reliable prospective acceptance of beneficial synthetic data”; đó phải là future DENSO validation.
