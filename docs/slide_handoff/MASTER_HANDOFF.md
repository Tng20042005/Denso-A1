# DENSO-A1 — Final Research & Solution Handoff

**Project:** Synthetic Fault Data Safety Gate  
**Audience:** presentation/slide team  
**Evidence freeze:** 2026-10-09 artifacts  
**Status:** research package ready; official submission readiness conditional on Team Lead confirmation

---

## 1. Executive Summary

DENSO-A1 bắt đầu với câu hỏi liệu synthetic fault waveforms có giúp fault detector trong chế độ cực few-shot hay không. Bốn nhánh đại diện đã được xây, freeze và đánh giá trung thực:

- T0 physics-informed synthesis;
- T0-v2 calibrated physics synthesis;
- T2 conditional 1D VAE;
- T3 fault-preserving transformations.

Không nhánh nào đồng thời đạt fidelity, novelty và held-out measured-real utility. T0/T0-v2/T2 cho negative hoặc unsupported utility trên Paderborn; T3 chỉ tăng rất nhỏ so với real-only ở k=1, không hơn simple augmentation, không cải thiện tại k=2 và có fidelity/near-copy failure.

Vì vậy contribution cuối không phải một successful generator. Nó là **generator-agnostic Synthetic Fault Data Safety Gate**: candidate chỉ được admit vào detector training nếu pass bốn lớp evidence — provenance/validity, fidelity, novelty và measured-real utility. Retrospective gate reject cả bốn frozen branches. SafetyGate-v1 sau đó được kiểm bằng real-vs-real references, 25 controlled-corruption configurations và 18 frozen utility-association rows, rồi freeze theo reference-relative policy cho future DENSO validation.

Supported conclusion:

> Across the tested CWRU/Paderborn few-shot settings, four representative synthesis/augmentation strategies failed to simultaneously satisfy fidelity, novelty and held-out real-fault utility requirements. A generator-agnostic admission gate prevented unsupported synthetic-data claims and identifies when generated fault data should not be used.

Không được suy diễn rằng synthetic data luôn vô ích, gate làm detector chính xác hơn, hoặc kết quả đã transfer sang DENSO.

---

## 2. Industrial Problem

### 2.1 Vì sao fault data hiếm

Real machine failures hiếm, không an toàn để chủ động tạo, tốn thời gian và thường chỉ xảy ra dưới một tổ hợp machine/load/speed/sensor cụ thể. Label có thể đến muộn từ maintenance log; nhiều window từ cùng một event không tạo thêm independent fault groups. Vì vậy dataset có thể rất nhiều samples nhưng vẫn chỉ có vài independent faults.

### 2.2 Cơ hội và rủi ro của synthetic data

Synthetic faults có thể bổ sung lớp hiếm hoặc coverage operating conditions. Nhưng nếu waveform có sai fault anchor, resonance, damping, SNR hoặc high-frequency artifacts, detector sẽ học shortcut. Nếu sample gần parent đến mức copy, reported accuracy có thể là memorization. Nếu test/parent leakage hoặc budget không fair, improvement không có ý nghĩa.

Research question cuối cùng là:

> Given a candidate synthetic fault dataset, can we determine whether it is safe and useful enough to admit into detector training?

---

## 3. Final Proposed Solution

Candidate được coi là optional training input. Nó chỉ được `ACCEPT` nếu:

1. experiment hợp lệ và provenance truy vết được;
2. candidate đủ fidelity so với measured-real reference;
3. candidate đủ novel, không duplicate/near-copy/memorize;
4. candidate tăng held-out measured-real utility so với cả real-only và simple augmentation.

Nếu bất kỳ gate nào FAIL, UNKNOWN hoặc NOT_APPLICABLE, implementation hiện tại trả `REJECT`. Không có state `REVIEW` trong source code.

Main architecture figure: `reports/safety_gate_architecture.svg`.

---

## 4. System Architecture

```text
Candidate signals + metadata + parent links
                    |
                    v
 [1 Provenance / Validity]
 public-real test | no parent leakage | fair budget | checksums
                    |
                    v
 [2 Fidelity]
 PSD/envelope | RMS/kurtosis/crest | C2ST | feature gaps
                    |
                    v
 [3 Novelty]
 exact hashes | nearest-neighbor ratio | memorization
                    |
                    v
 [4 Utility]
 untouched measured-real holdout | paired E−E0/E1 | ≥5 seeds
                    |
                    v
 ACCEPT iff every gate PASS; otherwise REJECT
```

### Gate 1 — Provenance / Validity

Checks source type, immutable split groups, train-only parents, no group overlap, data budget and sample/signal/prediction hashes. PASS không nói candidate realistic; nó chỉ xác nhận experiment hợp lệ.

### Gate 2 — Fidelity

Measures PSD cosine/JS, envelope alignment/anchor drift, RMS, kurtosis, crest factor, band energy và real-vs-candidate C2ST. SafetyGate-v1 không dùng một universal C2ST cutoff; thresholds được derive từ condition-appropriate measured-real references bằng fixed quantiles/margins.

### Gate 3 — Novelty

Checks exact signal hashes và normalized generated-to-real nearest-neighbor distance. Fidelity và novelty bổ sung nhau: xa parent chưa chắc realistic; quá gần có thể là copy.

### Gate 4 — Utility

Uses an untouched measured-real fault holdout. SafetyGate-v1 yêu cầu ít nhất 5 paired seeds và PR-AUC improvement có lower 95% CI >0 so với cả E0 real-only và E1 simple augmentation; F1 phải được report với CI.

---

## 5. Core Technical Mechanism

### 5.1 Data/evaluation contract

- 4096-sample non-overlapping windows.
- Group split trước generation; preprocessing fit train-only.
- `k` là số real fault groups trong train, không phải number of windows.
- k=0 không được đọc real fault information; methods cần measured fault parent không có result ở k=0.
- k≥1 comparators dùng cùng selected fault groups.
- Generated arms thường thêm 32 samples trong frozen Paderborn protocols.
- Five paired seeds; raw rows store split/subset/generator/model seeds and hashes.

### 5.2 Evaluator

- k=0 E0: Isolation Forest, 100 estimators.
- Supervised arms: Random Forest, 120 trees, balanced class weights, min leaf 2.
- Features: RMS, standard deviation, crest factor, kurtosis, four Welch PSD band energies.
- Primary: PR-AUC. Secondary: F1, recall@10% FPR, ROC-AUC.
- 95% CIs: percentile bootstrap over five seed-level values.

Limitations: only one compact feature-based evaluator family; n=5 is small; F1 uses test-score median threshold in implementation and is not a production-frozen threshold.

### 5.3 Decision states

Per-gate states from `src/denso_a1/safety_gate.py`: `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`. Candidate admission: `ACCEPT` or `REJECT`. UNKNOWN never becomes PASS.

---

## 6. Research Evolution

### Phase 1 — T0 physics-informed synthesis

T0 overlays periodic impulses, jitter, damped resonance, amplitude modulation and controlled noise. CWRU established protocol validity but random-group saturated: E0 PR-AUC `0.9988–1.0000`. Cross-load made k=0 harder, yet k≥1 remained approximately saturated.

External Paderborn original T0 E2−E0 PR-AUC deltas were `−0.0463`, `−0.0559`, `−0.0652` for k=0/1/2, with CIs crossing zero. Failure analysis found C2ST `1.0`, spectral JS `0.185959`, PSD cosine `0.513255`, measured/generated envelope peaks `101.59/223.17 Hz`, and generated kurtosis/crest factor `19.75/9.00` versus measured `5.09/5.63`. T0 was reproducible but not fidelity-safe or utility-supported.

Sources: `reports/cwru/summary.json`, `reports/cwru_cross_load/summary.json`, `reports/paderborn/summary.json`, `reports/t0_failure_analysis/failure_analysis.json`.

### Phase 2 — T0-v2

Only three justified changes were allowed: physics-only defaults 100 Hz/5 kHz, Gaussian impulse smoothing width 8, and train-only anchor calibration for k≥1. Freeze hash: `5232deca09ddc0ab1f80ff280e5e03577c5ecee25745721a5fa72139fa3f19e9`.

On new Paderborn `N09_M07_F10` final holdout, E2−E0 PR-AUC was:

- k=0: `−0.0196 [−0.0838, 0.0398]`;
- k=1: `−0.1573 [−0.1850, −0.1208]`;
- k=2: `−0.2517 [−0.2942, −0.1898]`.

All validity/calibration audits passed. T0-v2 was closed. Important: there is no independent T0-v2 C2ST report; retrospective fidelity FAIL means the changed family never independently passed a fidelity gate.

Source: `reports/paderborn_v2/summary.json`.

### Phase 3 — T2 conditional 1D VAE

The VAE learned from allowed Paderborn training fault groups and operating metadata only. Final holdout was `N15_M01_F10`, bearings `K004, KA16, KI04`. Freeze hash: `64e6e406da77011eae9305037c2feea6ba04c42e0767021d25967f21ee5c52d8`.

T2 passed memorization audit (minimum NN ratio `0.4520`) but failed fidelity: C2ST `1.0`, mean JS `0.173952`, mean cosine `0.557389`. E3−E0 PR-AUC:

- k=1: `−0.0281 [−0.0309, −0.0254]`;
- k=2: `−0.1002 [−0.1103, −0.0900]`.

No diffusion/GAN was started.

Sources: `reports/t2_benchmark/summary.json`, `reports/t2_benchmark/raw_metrics.json`.

### Phase 4 — T3 fault-preserving augmentation

T3 tested conservative transforms of measured fault parents. All 12 development policies failed the pre-final gate; lowest-score `time_scale` was retained for diagnostic final comparison. Final holdout: `N15_M01_F10`, bearings `K001, KA15, KI16`. Freeze hash: `7fa7e9f66bab0965d7de086570ac18f16ddefd8c09ce53d7e943ea73bb5b2dab`.

E4−E0 PR-AUC:

- k=1: `+0.0028 [0.0018, 0.0041]`;
- k=2: `−0.0002 [−0.0105, 0.0080]`.

E4−E1 was non-positive at both k. Validation C2ST maximum was `1.0`; train-parent NN ratio `0` and exact overlap created novelty failure. No T3 result exists at k=0 by design.

Sources: `reports/t3_development/raw_development.json`, `reports/t3_benchmark/summary.json`, `reports/t3_benchmark/raw_metrics.json`.

### Phase 5 — Common retrospective Safety Gate

The same four-stage interface was applied to frozen artifacts:

| Branch | Validity | Fidelity | Novelty | Utility | Decision |
|---|---|---|---|---|---|
| T0 | PASS | FAIL | UNKNOWN | FAIL | REJECT |
| T0-v2 | PASS | FAIL/not independently passed | UNKNOWN | FAIL | REJECT |
| T2 | PASS | FAIL | PASS | FAIL | REJECT |
| T3 | PASS | FAIL | FAIL | FAIL | REJECT |

Source: `reports/safety_gate/retrospective.json`.

### Phase 6 — SafetyGate-v1 validation/freeze

Matched measured-real halves produced C2ST `0.5085`, PSD cosine `0.9967`, JS `0.0013`; bearing-disjoint train-vs-validation real data produced C2ST `0.9977`, showing group shift can itself be highly separable. A 25-row corruption ladder showed consistent spectral degradation for five corruption families; C2ST was mixed for envelope distortion. Eighteen frozen method/config rows supported directional agreement with downstream no-benefit/harm but were too few/dependent for a correlation claim.

Canonical validation protocol payload hash:

`1d07f943790646b312be2f427a5cec24c07b25f0b5e6dd7c4dea65f6998fb5d5`

SafetyGate-v1 config byte SHA:

`f93c0bac6cf1a5dd8fb77ec57f441edb992a3919b11edfa024e1d3b5b89cb435`

Validation supports diagnostic behavior and transparent thresholds. It does not prove prospective acceptance accuracy.

---

## 7. Experimental Datasets

### CWRU

- Official 12 kHz Drive-End subset, DE acceleration.
- 16 Matlab recordings: 4 normal, 12 seeded 0.007-inch inner/ball/outer faults.
- 3,162,347 raw samples; 762 non-overlapping 4096-sample windows.
- File-level group; random-group and cross-load protocols.
- Faults are seeded physical EDM faults, not field-natural or DENSO.
- Official source page has no standard SPDX license in project survey; raw redistribution is avoided.

### Paderborn

- `vibration_1`, 64 kHz; 4 healthy + 6 accelerated-damage bearings used.
- Measurement repetitions 1–5; bearing as group.
- Original T0 artifact: 50 files/3,101 windows.
- T0-v2 artifact: 50 files/3,102 windows across train/final conditions.
- T2/T3 artifacts: 85 files; 5,292/5,299 windows respectively.
- CC BY-NC 4.0; citation required; no commercial redistribution.

Different branches use different holdouts; do not combine absolute scores as one benchmark.

---

## 8. Consolidated Results

### Master result table

| Method/protocol | k | Candidate arm PR-AUC / F1 | Paired PR-AUC delta vs E0 [95% CI] | Fidelity/novelty | Final |
|---|---:|---|---|---|---|
| T0, Paderborn original | 0 | 0.7911 / 0.7813 | −0.0463 [−0.2453,0.1400] | C2ST 1.0; novelty UNKNOWN | REJECT |
| T0, Paderborn original | 1 | 0.7747 / 0.6495 | −0.0559 [−0.1882,0.0511] | same | REJECT |
| T0, Paderborn original | 2 | 0.7720 / 0.7229 | −0.0652 [−0.2046,0.0148] | same | REJECT |
| T0-v2, N09 holdout | 0 | 0.5612 / 0.5708 | −0.0196 [−0.0838,0.0398] | not independently passed / UNKNOWN | REJECT |
| T0-v2, N09 holdout | 1 | 0.5535 / 0.4596 | −0.1573 [−0.1850,−0.1208] | same | REJECT |
| T0-v2, N09 holdout | 2 | 0.7483 / 0.7085 | −0.2517 [−0.2942,−0.1898] | same | REJECT |
| T2 cVAE, N15_M01 holdout | 1 | 0.9431 / 0.7977 | −0.0281 [−0.0309,−0.0254] | fidelity FAIL; novelty PASS | REJECT |
| T2 cVAE, N15_M01 holdout | 2 | 0.7259 / 0.6097 | −0.1002 [−0.1103,−0.0900] | same | REJECT |
| T3, distinct N15_M01 holdout | 1 | 0.9794 / 0.8327 | +0.0028 [0.0018,0.0041] | fidelity + novelty FAIL | REJECT |
| T3, distinct N15_M01 holdout | 2 | 0.9226 / 0.8653 | −0.0002 [−0.0105,0.0080] | same | REJECT |

T3 is also non-positive versus E1 at k=1/2. T2/T3 summaries do not contain paired F1 deltas; arm-level F1 CIs are reported in supporting table and must not be converted into paired CIs.

Precise source for every value: `05_all_experimental_results.md`.

---

## 9. SafetyGate Validation

### Real-vs-real reference

| Statistic | Matched train halves | Train vs bearing-disjoint validation |
|---|---:|---:|
| C2ST ROC-AUC | 0.5085 | 0.9977 |
| PSD cosine | 0.9967 | 0.9169 |
| Spectral JS | 0.0013 | 0.0230 |
| Envelope cosine | 0.9961 | 0.9577 |

The contrast demonstrates why a universal C2ST threshold is inappropriate. A real domain shift can be easy to classify.

### Corruption ladder

Five families × five severity levels = 25 rows. PSD JS/cosine trends were fully consistent across families; C2ST/envelope-anchor trends were mostly consistent, with mixed envelope-distortion C2ST retained in the report.

### Utility association

Eighteen frozen config rows show rejection agrees directionally with no-benefit/harm evidence. They do not support statistical prediction because rows are dependent, branch metrics differ and candidate C2ST is nearly constant at one.

### SafetyGate-v1

Uses q05/q95 real-reference calibration plus fixed margins and freezes all settings before candidate utility. Exact hashes and validity remain hard requirements. Utility requires positive CI lower bounds against both E0/E1.

Validation figure: `reports/safety_gate_validation_figure.svg`.

---

## 10. Scientific Contributions

### Implemented and validated

- Group-aware, provenance-rich public-real benchmark pipeline.
- Leakage, budget, training-difference and test-isolation audits.
- Fidelity diagnostic suite with real controls/corruption response.
- Novelty checks on T2/T3.
- Held-out measured-real utility evaluation procedure.
- Honest negative evidence for four representative strategies.

### Implemented but retrospective

- Cross-branch four-stage common admission interface and four REJECT decisions.

### Proposed/frozen for future validation

- Reference-relative SafetyGate-v1 for DENSO machine/condition data.

### Unsupported

- Reliable prospective utility prediction.
- Improved DENSO detector accuracy, downtime or cost.
- Universal ineffectiveness of synthetic faults.

---

## 11. Practical Value for DENSO

Potentially, SafetyGate can serve as pre-training QA: verify provenance, expose distribution mismatch, detect duplicates/memorization, require measured-real utility and generate an auditable go/no-go report. It can also prevent resource waste by rejecting unsafe candidates before broad detector training.

These benefits are not yet measured at DENSO. They require secure DENSO data onboarding, domain expert review, machine-specific references and prospective validation.

---

## 12. Deployment Roadmap

1. **Onboard securely:** schema, sensors, labels, groups, NDA and checksums.
2. **Build measured-real references:** machine/condition-disjoint train/val; quantify natural shift.
3. **Calibrate/freeze:** DENSO-specific SafetyGate-v1 thresholds, evaluator, budget and hash.
4. **Evaluate candidates:** frozen four-gate run on untouched measured-real holdout.
5. **Prospective study:** predict accept/reject before revealing utility; measure false accepts/rejects.
6. **Controlled pilot:** integrate artifact registry, approvals, monitoring and rollback into training workflow.

Full inputs/resources/deliverables/risks: `08_denso_industrial_roadmap.md`.

---

## 13. Limitations and Known Discrepancies

- No DENSO data or naturally occurring field fault study.
- CWRU ceiling effect; Paderborn accelerated damage only.
- One evaluator family; n=5 paired seeds.
- F1 test-median threshold limitation.
- Distinct branch holdouts; no common cross-branch final test.
- No prospective accepted beneficial synthetic candidate.
- T0/T0-v2 novelty UNKNOWN; T0-v2 fidelity not independently measured after changes.
- Duplicate ADR number `010`; use filenames.
- Old `docs/handoff/slide_notes.md` is stale and superseded.
- T3 `≈0.998` and `1.0` C2ST refer to mean development versus maximum validation aggregation.
- Embedded validation protocol hash is a canonical payload hash; full JSON file SHA differs after embedding the hash.

---

## 14. Suggested Slide Narrative

1. Industrial problem: scarce faults and synthetic-data risk.
2. Research question: should a candidate enter training?
3. Honest six-phase journey.
4. Final four-gate solution.
5. Validity + fidelity mechanism.
6. Novelty + utility mechanism.
7. CWRU/Paderborn protocol and boundaries.
8. Frozen generator results.
9. Real-reference/corruption validation.
10. Evidence-backed scientific contributions.
11. DENSO prospective integration roadmap.
12. Conclusion, limitations and next evidence step.

Detailed talking points, speaker notes and forbidden claims: `09_slide_by_slide_content.md`.

---

## 15. Key Figures and Tables

1. `reports/safety_gate_architecture.svg` — final architecture.
2. `reports/safety_gate_validation_figure.svg` — corruption response + frozen utility evidence.
3. Final results table in `05_all_experimental_results.md` — gate decisions and key deltas.
4. `reports/demo/t0_diagnostic.png` — early mechanism demo only, not public-real evidence.
5. DENSO roadmap should be drawn from `08_denso_industrial_roadmap.md` and labeled proposed.

Do not modify empirical meaning, omit negative bars or combine holdouts without facets.

---

## 16. Source References

### Governing decisions

- `.md/FinalPlan_DENSO_A1.md` — historical plan plus current superseding addendum.
- `docs/adr/010-synthetic-data-safety-gate.md` — final project pivot.
- `docs/adr/011-safety-gate-v1-freeze.md` — future calibration/freeze policy.
- `configs/safety_gate_v1.json` — machine-readable v1 policy.

### Raw experiment sources

- CWRU: `reports/cwru/summary.json`, `reports/cwru_cross_load/summary.json`.
- Original Paderborn T0: `reports/paderborn/summary.json`.
- T0 failure: `reports/t0_failure_analysis/failure_analysis.json`.
- T0-v2: `reports/paderborn_v2/summary.json`.
- T2: `reports/t2_benchmark/summary.json`, `raw_metrics.json`.
- T3: `reports/t3_benchmark/summary.json`, `raw_metrics.json`.
- Common gate: `reports/safety_gate/retrospective.json`, `reports/generator_comparison.csv`.
- Validation: `reports/safety_gate_validation_reference.json`, `reports/safety_gate_corruption_ladder.csv`, `reports/safety_gate_utility_association.csv`, `reports/safety_gate_validation_protocol.json`.

### Submission control

Before final submission, Team Lead must confirm official deadline, slide count/time, format/rubric, link/citation rules, repository tag/publication rights and dataset figure redistribution. Until then, the evidence package is ready but administrative submission readiness remains conditional.

