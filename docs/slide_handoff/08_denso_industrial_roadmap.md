# Lộ trình tích hợp công nghiệp cho DENSO

Mọi lợi ích dưới đây là **potential**, chưa được experimentally established trên DENSO.

## Stage 1 — Receive and inspect DENSO datasets

- **Input:** raw vibration/current/acoustic/temperature data, sensor map, timestamps, maintenance/fault labels, operating metadata, NDA/retention rules.
- **Resources:** data engineer, domain expert, secure storage, access-control owner.
- **Tasks:** schema profile; missingness/saturation/dead-channel audit; immutable `raw_record_id`/`group_id`; label provenance; security review.
- **Deliverable:** DENSO data card, access policy, checksum registry, candidate grouping hierarchy.
- **Validation:** every file traceable; ambiguous label/group explicitly flagged.
- **Risk:** leakage via same machine/run/window; maintenance labels không đồng nghĩa fault onset.

## Stage 2 — Establish machine-specific measured-real references

- **Input:** train/validation measured normal/fault groups and operating conditions.
- **Tasks:** define machine/condition-disjoint partitions; extract real-vs-real diagnostic distributions; quantify natural shift.
- **Deliverable:** per-machine/per-condition reference artifact, versioned split manifest.
- **Validation:** ≥5 reference replicates where feasible; final test untouched.
- **Risk:** quá ít independent fault groups để estimate quantiles ổn định.

## Stage 3 — Calibrate SafetyGate-v1

- **Input:** Stage-2 references, frozen v1 policy.
- **Tasks:** calculate q05/q95 + fixed margins; freeze channel/window/preprocessing/evaluator/thresholds; record hash.
- **Deliverable:** `SafetyGate-DENSO-<machine>-v1` config và ADR.
- **Validation:** matched real control sensible; controlled diagnostic degradation coherent.
- **Risk:** condition pooling che mismatch; reusing Paderborn thresholds mù quáng.

## Stage 4 — Evaluate candidate synthetic data

- **Input:** candidate signals + complete parent/source provenance.
- **Tasks:** run validity, fidelity, novelty; train budget-matched E0/E1/Esynthetic; evaluate untouched measured-real holdout.
- **Deliverable:** signed/versioned admission report, raw run audit, ACCEPT/REJECT.
- **Validation:** all required fields present; ≥5 paired seeds; CI rule vs E0/E1; no test tuning.
- **Risk:** repeated candidate submission becomes hidden search on final holdout; cần governance/new holdout policy.

## Stage 5 — Prospective acceptance/rejection validation

- **Input:** multiple candidates whose outcomes are unknown at gate-freeze time.
- **Tasks:** freeze diagnostics first; predict admit/reject; reveal independent utility later; measure false-accept/false-reject and calibration stability.
- **Deliverable:** prospective validation study and threshold revision policy.
- **Validation:** beneficial candidates can be accepted, harmful candidates rejected, with predeclared error criteria.
- **Risk:** small number of truly independent generators; utility drift by evaluator/machine.

## Stage 6 — Pilot integration

- **Input:** prospectively validated policy, MLOps/training workflow.
- **Tasks:** API/CLI integration; artifact registry; approval workflow; monitoring; rollback; periodic reference refresh.
- **Deliverable:** controlled pilot where synthetic data is optional and gated.
- **Validation:** audit completeness, reproducibility, no security violation, no degradation on measured-real monitoring set.
- **Risk:** policy drift, data governance, operator misunderstanding of ACCEPT as production certification.

## Potential business value, not current evidence

- Giảm rủi ro đưa shortcut/near-copy data vào training.
- Tạo common QA language giữa data, ML và domain teams.
- Cung cấp reproducible evidence report cho go/no-go decision.
- Ưu tiên nguồn lực: dừng sớm candidate fail gate thay vì tiếp tục expensive training.

Không định lượng downtime/cost saving cho đến khi Stage 5–6 có KPI thực.

