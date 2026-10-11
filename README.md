# DENSO A1 — Synthetic Fault Data Safety Gate

This repository started as the execution prototype described in
[`FinalPlan_DENSO_A1.md`](.md/FinalPlan_DENSO_A1.md). It implements the Must
scope: a reproducible T0 physics-informed injector, T1 signal augmentation,
group-level splits, provenance metadata, leakage/budget audits, a small
evaluator, and a smoke benchmark.

The current project status is different: raw-waveform generation and
augmentation development is closed after negative T0, T0-v2, T2 and T3
branches. The active contribution is a generator-agnostic **Synthetic Fault
Data Safety Gate** that admits a candidate only when provenance/validity,
fidelity, novelty and held-out measured-real utility all pass.

## Final results snapshot

The four frozen generation/augmentation branches are closed as negative-result
branches. The final contribution is the admission gate, not a successful fault
generator.

| Branch | Key held-out finding | Admission |
| --- | --- | --- |
| T0 physics synthesis | Paderborn fidelity failed (C2ST ROC-AUC 1.0; PSD cosine 0.5133) and utility was not supported | REJECT |
| T0-v2 calibrated physics | E2−E0 PR-AUC: −0.1573 at k=1 and −0.2517 at k=2 | REJECT |
| T2 conditional 1D VAE | E3−E0 PR-AUC: −0.0281 at k=1 and −0.1002 at k=2 | REJECT |
| T3 fault-preserving augmentation | +0.0028 versus E0 at k=1, but not better than E1; fidelity/near-copy audit failed | REJECT |

The gate itself passed a diagnostic validation: a matched measured-real control
had C2ST 0.5085, PSD cosine 0.9967 and spectral JS 0.0013. This does not
establish transfer to DENSO or prove prospective acceptance accuracy. The
complete slide/research handoff is in
[`docs/slide_handoff/MASTER_HANDOFF.md`](docs/slide_handoff/MASTER_HANDOFF.md).

## Honest scope boundary

The core prototype was first validated on simulated signals. Public-real
validation now uses the official CWRU 12 kHz Drive-End recordings; these are
seeded physical faults, not DENSO data or naturally occurring field faults.
CWRU's official pages do not state a standard SPDX license, so raw files remain
local and are not redistributed. Paderborn is the licensed CC BY-NC 4.0
external-validation backup; its result is kept separate from the CWRU claim.

## Quickstart

```bash
conda activate denso-a1-20261007
make setup
make test
make demo
make bench
```

Outputs include raw manifests, audit JSON, signal/PSD figures, and a benchmark
summary with paired deltas. For the long-running workflow, the commands are
run from a fresh tmux session with the dedicated conda environment
`denso-a1-20261007`.

## CLI

```bash
denso-a1 demo --out reports/demo
denso-a1 benchmark --out reports/benchmark --seeds 5
denso-a1 report --benchmark reports/benchmark
denso-a1 public-benchmark --raw-root data/raw/cwru --out reports/cwru --seeds 5
denso-a1 paderborn-benchmark --raw-root data/raw/paderborn/extracted --out reports/paderborn --seeds 5
denso-a1 public-report --benchmark reports/cwru
denso-a1 safety-gate --repo .
```

## Implemented protocol

- T0: impulse train + damped resonance + amplitude modulation + controlled
  noise, with Nyquist and SNR guards.
- T1: budget-matched jitter/scaling/time-shift augmentation.
- `k` counts fault groups, never windows.
- Each generated sample stores parent IDs/groups and train-only provenance.
- Test groups are immutable within each benchmark run.
- Primary metrics are PR-AUC and F1; bootstrap 95% CIs and paired deltas are
  reported across seeds.

## Public-real validation

The current primary dataset is the official CWRU 12 kHz Drive-End subset.
Raw files are downloaded into the git-ignored `data/raw/cwru/` directory. The
loader freezes one Matlab recording as one group, fits preprocessing on train,
and audits that test contains only measured `public_real` samples. See
[`docs/dataset_survey.md`](docs/dataset_survey.md) and
[`docs/adr/002-dataset-and-protocol.md`](docs/adr/002-dataset-and-protocol.md).

The public-real result is the E4 `k`-sweep over `k={0,1,2}` with five paired
seeds. See [`reports/cwru/benchmark_report.md`](reports/cwru/benchmark_report.md),
the harder CWRU cross-load report
[`reports/cwru_cross_load/benchmark_report.md`](reports/cwru_cross_load/benchmark_report.md),
and the external Paderborn report
[`reports/paderborn/benchmark_report.md`](reports/paderborn/benchmark_report.md).
Per-run provenance and prediction hashes are in each report's `run_audit.md`.
The T0 failure gate and frozen-v2 negative result are recorded in
[`reports/t0_failure_analysis.md`](reports/t0_failure_analysis.md) and
[`reports/paderborn_v2/benchmark_report.md`](reports/paderborn_v2/benchmark_report.md).
See also
[`docs/method.md`](docs/method.md), [`docs/data_onboarding.md`](docs/data_onboarding.md),
and [`docs/claim_evidence_matrix.md`](docs/claim_evidence_matrix.md).

## Safety-gate retrospective

The common interface is [`src/denso_a1/safety_gate.py`](src/denso_a1/safety_gate.py).
Run `denso-a1 safety-gate --repo .` to regenerate the machine-readable
retrospective and [`reports/generator_comparison.csv`](reports/generator_comparison.csv).
The final decision table is in
[`reports/safety_gate_summary.md`](reports/safety_gate_summary.md), with the
architecture figure in [`reports/safety_gate_architecture.svg`](reports/safety_gate_architecture.svg)
and the slide-ready table in [`reports/final_results_table.md`](reports/final_results_table.md).

All four frozen branches are rejected before deployment. This does not claim
that synthetic fault data is universally ineffective; it records only that the
tested CWRU/Paderborn few-shot settings did not satisfy all safety and utility
requirements. Transfer to DENSO and naturally occurring field faults is not
established.

The gate validation and future freeze are documented in
[`reports/safety_gate_validation.md`](reports/safety_gate_validation.md),
[`reports/safety_gate_validation_figure.svg`](reports/safety_gate_validation_figure.svg),
and [`docs/adr/011-safety-gate-v1-freeze.md`](docs/adr/011-safety-gate-v1-freeze.md).
The validation uses measured-real references and diagnostic-only corruptions;
neither is presented as a synthetic candidate or utility result.
