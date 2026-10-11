# Đóng góp khoa học được evidence hỗ trợ

| Contribution | Classification | Evidence và ranh giới |
|---|---|---|
| Reproducible public-real few-shot evaluation pipeline | IMPLEMENTED AND VALIDATED | CWRU/Paderborn loaders, frozen manifests, raw hashes, ≥5 paired seeds, audit PASS |
| Provenance-aware validity checks | IMPLEMENTED AND VALIDATED | public-real test isolation, group leakage, parent restriction, budget and training-difference audits |
| Fidelity diagnostic suite | IMPLEMENTED AND VALIDATED AS DIAGNOSTICS | PSD/envelope, RMS/kurtosis/crest, C2ST; behavior checked bằng real references + corruptions |
| Novelty/memorization checks | IMPLEMENTED AND VALIDATED ON T2/T3 | exact hash + NN ratios; T0/T0-v2 remain UNKNOWN |
| Held-out measured-real utility gate | IMPLEMENTED AND VALIDATED AS AN EVALUATION PROCEDURE | branch-specific Paderborn holdouts; n=5; no claim of production accuracy |
| Four-stage generator-agnostic common admission interface | IMPLEMENTED BUT ONLY RETROSPECTIVELY EVALUATED | assembled after branch utility artifacts; all four historical candidates REJECT |
| Evidence on limits of T0/T0-v2/T2/T3 | IMPLEMENTED AND VALIDATED WITHIN TESTED SETTINGS | negative/no-benefit evidence, fidelity failures and limitations explicitly preserved |
| Reference-relative SafetyGate-v1 calibration policy | PROPOSED FOR FUTURE VALIDATION | frozen config and rationale exist; no DENSO candidate prospective run yet |
| Reliable prospective prediction of generator utility | UNSUPPORTED | 18 dependent config rows, incomplete metrics, no accepted beneficial candidate |
| Improved detector accuracy/reduced downtime for DENSO | UNSUPPORTED | no DENSO data/KPI/production trial |
| Synthetic fault data universally ineffective | UNSUPPORTED | evidence covers four strategies and specific public benchmark protocols only |

## Novelty của contribution cuối

Điểm mạnh không nằm ở một metric riêng. Contribution là kết hợp bốn loại evidence vốn dễ bị tách rời:

1. đúng nguồn và đúng split;
2. đủ gần real signal distribution;
3. không copy/memorize;
4. có utility trên untouched measured-real faults.

Một candidate đẹp về waveform nhưng fail utility vẫn bị reject; candidate tăng score nhưng dùng test parent cũng bị reject; candidate gần parent đến mức copy cũng bị reject. Logic conjunctive này là thông điệp khoa học chính.

## Claim wording khuyến nghị

“We implement and retrospectively evaluate a four-stage synthetic-fault admission gate, then freeze a reference-relative SafetyGate-v1 policy for prospective validation.”

Không đổi thành “the gate predicts generator quality” hoặc “the gate improves detection”.

