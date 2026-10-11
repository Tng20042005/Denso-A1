# Nội dung slide-by-slide

Đây là narrative gợi ý cho khoảng 12 slide, **không phải yêu cầu chính thức của cuộc thi**. Nếu official brief khác, Team Lead/Slide Owner phải map lại nhưng giữ claim boundary.

## Slide 1 — Industrial Problem: Fault data is scarce, mistakes are costly

**Main message:** Synthetic data có tiềm năng bổ sung fault scarcity, nhưng dữ liệu sinh sai có thể dạy detector shortcut nguy hiểm.

- Real fault events hiếm, tốn kém và condition-specific.
- Normal data dồi dào nhưng không đủ đại diện failure modes.
- Visual realism không tương đương detector utility.
- Cần quality admission trước khi dùng synthetic faults.

**Visual:** problem flow tự dựng bằng shape, không gắn metric. **Speaker note:** phân biệt public benchmark và DENSO. **Không claim:** đã giảm downtime/cost.

## Slide 2 — Research question: should this synthetic dataset enter training?

**Main message:** Câu hỏi cuối không phải “generator nào đẹp nhất?” mà là “candidate có đủ safe/useful evidence không?”.

- Valid provenance?
- Similar to measured faults?
- Novel, not memorized?
- Improves untouched real-fault detection?

**Visual:** 4-question checklist. **Không claim:** gate bảo đảm physical correctness.

## Slide 3 — Honest research journey

**Main message:** Sáu phase liên tiếp, mỗi pivot được quyết định bởi frozen evidence.

- T0 physics → mismatch.
- T0-v2 calibration → utility harm.
- T2 cVAE → fidelity + utility fail.
- T3 transforms → near-copy/no gain over E1.
- Common safety gate → retrospective rejection.
- SafetyGate-v1 → reference-relative freeze.

**Visual:** timeline tự dựng từ `02_complete_research_journey.md`. **Speaker note:** negative results là design input. **Không claim:** các branch dùng cùng final holdout.

## Slide 4 — Final proposed solution

**Main message:** Admit synthetic data only when all four independent evidence layers PASS.

- Candidate + metadata + parent links.
- Sequential validity, fidelity, novelty, utility.
- UNKNOWN không phải PASS.
- Candidate output thực tế: ACCEPT/REJECT.

**Visual/source:** `reports/safety_gate_architecture.svg`. **Không claim:** có REVIEW state trong code.

## Slide 5 — Gate 1 & 2: valid experiment, realistic distribution

**Main message:** Correct split và similar waveform trả lời hai câu hỏi khác nhau.

- Gate 1: real-only test, no parent leakage, fair budget, traceability.
- Gate 2: PSD/envelope, RMS/kurtosis/crest, C2ST.
- T0 example: C2ST 1.0, JS 0.186, cosine 0.513.
- PASS validity không cứu được FAIL fidelity.

**Visual:** left/right gate cards + T0 metrics; source `reports/t0_failure_analysis/failure_analysis.json`. **Không claim:** T0-v2 đã đo C2ST riêng.

## Slide 6 — Gate 3 & 4: novel data that helps real holdouts

**Main message:** Candidate phải vừa không copy vừa tạo positive paired utility trên measured-real holdout.

- Hash/NN detect exact/near copies.
- Compare vs E0 real-only và E1 simple augmentation.
- ≥5 paired seeds, PR-AUC/F1, 95% CI.
- T3 có +0.0028 vs E0 at k=1 nhưng không hơn E1 và near-copy FAIL.

**Visual:** novelty + utility decision card; source `reports/t3_benchmark/summary.json`, `reports/t3_benchmark/raw_metrics.json`. **Không claim:** positive k1-vs-E0 đủ để PASS.

## Slide 7 — Experimental design and datasets

**Main message:** Utility được đánh giá trên public measured-real, group-disjoint holdouts — không phải DENSO data.

- CWRU: 16 files, 762 windows, 12 kHz, seeded EDM, random/cross-load.
- Paderborn: 10 bearings, 64 kHz, accelerated damage, condition/bearing holdouts.
- `k=0/1/2` counts fault groups; generated budget 32.
- Same evaluator/budget within each paired protocol; branch holdouts differ.

**Visual:** compact dataset table from `04_datasets_and_methodology.md`. **Không claim:** naturally occurring field faults.

## Slide 8 — Frozen branch results

**Main message:** Bốn strategies đều không đồng thời đạt fidelity, novelty và held-out utility.

- T0: fidelity FAIL; utility unsupported/negative.
- T0-v2: k1 −0.1573, k2 −0.2517 vs E0.
- T2: k1 −0.0281, k2 −0.1002 vs E0.
- T3: +0.0028 at k1 vs E0; ≈0/negative elsewhere; fail fidelity/novelty.

**Visual/table:** final table in `05_all_experimental_results.md` or `reports/final_results_table.md`. **Không claim:** one common holdout or meta-analysis.

## Slide 9 — SafetyGate is not simply “always reject”

**Main message:** Diagnostics distinguish matched real populations and respond coherently to controlled degradation.

- Matched real: C2ST 0.5085, cosine 0.9967, JS 0.0013.
- Real train-vs-val: C2ST 0.9977 → natural shift matters.
- 25 corruption configurations; spectral metrics monotonic/consistent.
- 18 frozen utility-association rows; directional agreement, no significance claim.

**Visual/source:** `reports/safety_gate_validation_figure.svg`. **Không claim:** gate already accepts beneficial synthetic candidates.

## Slide 10 — Scientific contributions

**Main message:** Contribution là evidence discipline và reproducible admission workflow, không phải successful generator.

- Reproducible group-aware pipeline.
- Provenance/fidelity/novelty/utility integration.
- Negative evidence preserved.
- Reference-relative policy frozen for future validation.

**Visual:** contribution classification from `07_scientific_contributions.md`. **Không claim:** utility prediction proven.

## Slide 11 — DENSO integration roadmap

**Main message:** DENSO value chỉ có thể được xác nhận qua prospective, machine-specific calibration.

- Secure onboarding and grouping.
- Measured-real reference per machine/condition.
- Freeze DENSO-specific gate.
- Evaluate candidates on untouched real holdouts.
- Prospective acceptance study → controlled pilot.

**Visual:** 6-stage roadmap tự dựng từ `08_denso_industrial_roadmap.md`. **Không claim:** current production readiness.

## Slide 12 — Conclusion and limitations

**Main message:** The gate prevented unsupported use of four candidates; the next step is prospective DENSO validation, not another generator search.

- All four frozen branches REJECT.
- Narrow conclusion: tested few-shot settings only.
- Gate validation supports diagnostic behavior/transparency.
- Missing: DENSO data and accepted beneficial synthetic candidate.
- Future objective: measured-data diagnosis/calibration/uncertainty or prospective gate validation.

**Visual:** architecture + one-line conclusion. **Không claim:** universal ineffectiveness, downtime reduction, DENSO transfer.

