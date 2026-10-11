# Figure inventory

## Existing empirical/architecture figures

| File | Demonstrates | Protocol | Key interpretation | Limitation | Recommended slide |
|---|---|---|---|---|---|
| `reports/safety_gate_architecture.svg` | Four sequential gates and all-PASS admission | final common gate | Candidate must pass validity, fidelity, novelty, utility | Conceptual; reject arrow is schematic, not a full state-machine diagram | 4 |
| `reports/safety_gate_validation_figure.svg` | Left: C2ST response over corruption severity; right: frozen paired PR-AUC deltas vs E0 | Paderborn diagnostic-only validation + frozen branch utility | Diagnostics respond to degradation; branch utility mostly non-positive | Mixed holdouts on utility panel; labels must say branch-specific protocols; no prospective acceptance | 9 |
| `reports/demo/t0_diagnostic.png` | Example normal/generated waveform and spectral behavior from early demo | simulated/generated demo | T0 mechanism is parameterized and reproducible | Not public-real utility/fidelity evidence; do not imply real fault realism | appendix or journey slide only |

## Existing slide-ready table

| File | Use | Limitation |
|---|---|---|
| `reports/final_results_table.md` | Compact retrospective gate decision | Omits detailed CIs/source paths; use `05_all_experimental_results.md` for numbers |

## Visuals the slide team may compose without changing evidence

| Visual | Source material | Rules |
|---|---|---|
| Six-phase research timeline | `02_complete_research_journey.md` | Label every pivot as evidence-driven; do not align metrics as same holdout |
| Dataset/protocol card | `04_datasets_and_methodology.md` | Mark CWRU seeded, Paderborn accelerated damage, both non-DENSO |
| Paired-delta forest/table | `05_all_experimental_results.md` | One panel per protocol/branch or explicit facet labels; preserve CI and sign |
| T0 fidelity failure card | `reports/t0_failure_analysis.md` | Use C2ST/JS/cosine/envelope/kurtosis numbers; no T0-v2 attribution |
| DENSO 6-stage roadmap | `08_denso_industrial_roadmap.md` | Label future/proposed; no ROI numbers |

## Figures not suitable as primary evidence

- PDFs under `data/raw/paderborn/extracted/*` are dataset fact sheets/logs, not project result figures and may carry redistribution constraints.
- `graphify-out` visualizations describe repository structure, not research performance.
- `t0_diagnostic.png` must never be presented as measured DENSO fault data.

## Export guidance

- Keep SVG vector format where possible.
- Add source path and protocol caption below every empirical visual.
- Do not remove negative bars, confidence intervals or FAILED/UNKNOWN labels.
- Do not redraw axes to exaggerate small T3 k=1 improvement.

