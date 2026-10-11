# ADR-002/004/005/006: CWRU public-real dataset and evaluation protocol

- Status: Accepted for G1/G3 public-real validation
- Date: 2026-10-07

## Decision

Use the official CWRU 12 kHz Drive-End subset as the primary public-real
dataset. Keep Paderborn as the external-validation backup. Use one Matlab source file as one immutable
`group_id`; create non-overlapping 4096-sample windows; fit preprocessing on
train only; select `k` by fault groups; and keep the test set measured and
`public_real` only.

The frozen file registry is implemented in
`src/denso_a1/data/cwru.py`. The group split is produced by
`make_protocol_split`; the public-test invariant is enforced by
`public_real_test_audit`.

## Protocol

- Primary metric: PR-AUC.
- Secondary metrics: F1 and recall at fixed 10% FPR.
- Methods: E0 real-only, E1 simple augmentation, E2 T0 augmentation.
- `k`: `{0, 1, 2}` fault groups in train; same split/subset seed across methods.
- Synthetic budget: E1 and E2 receive equal additional training examples for
  `k > 0`.
- Seeds: split, subset, generator and model seeds are stored separately.
- Minimum: 5 paired seeds.
- Test group list is stored in `reports/cwru/split_manifest.json`.

The Paderborn external validation is frozen separately at condition
`N15_M07_F10`, channel `vibration_1`, 64 kHz, measurement repetitions 1–5,
and bearing-disjoint grouping. Its artifacts are stored in
`reports/paderborn/`; the raw data remains outside Git because the source is
CC BY-NC 4.0.

## License and handling

CWRU's official pages document the data and attribution requirements but do not
state a standard SPDX license. Raw files remain outside Git, are not
redistributed, and every run records the official source URL and SHA-256.
Before external/commercial redistribution, obtain written permission from the
data owner.

## Exit criteria

G1 is satisfied for this public-real run when the survey, registry, checksums,
group manifest and train-only preprocessor are present. G3 additionally
requires all E0/E1/E2/E4 rows, paired uncertainty, public-real-test audit,
leakage audit, budget audit, and training-set difference audit to pass.
Submission/slide validation remains blocked until the CWRU and external
Paderborn results establish whether T0 has paired utility or produces a
reproducible negative result.
