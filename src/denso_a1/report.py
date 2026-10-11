from __future__ import annotations

import json
from pathlib import Path


def write_benchmark_report(benchmark_dir: str | Path) -> Path:
    directory = Path(benchmark_dir)
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    lines = [
        "# DENSO A1 benchmark report",
        "",
        "## Scope",
        "",
        "This run uses only `simulated` signals. It is mechanism/pipeline evidence, not a DENSO or public-real utility claim.",
        "",
        f"Primary metric: `{summary['primary_metric']}`. All paired deltas use the same split/subset/model seed per run.",
        "",
        "## Aggregate results",
        "",
        "| Setup | n | mean PR-AUC | bootstrap 95% CI |",
        "| --- | ---: | ---: | --- |",
    ]
    for key, value in summary["groups"].items():
        lines.append(f"| {key} | {value['n']} | {value['mean']:.4f} | [{value['ci95'][0]:.4f}, {value['ci95'][1]:.4f}] |")
    lines.extend(["", "## Paired T0 deltas", "", "| Comparison | n | mean delta | bootstrap 95% CI |", "| --- | ---: | ---: | --- |"])
    for key, value in summary.get("paired_deltas", {}).items():
        lines.append(f"| {key} | {value['n']} | {value['mean_delta']:.4f} | [{value['ci95'][0]:.4f}, {value['ci95'][1]:.4f}] |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The result is diagnostic for the simulated mechanism. Before any utility claim, replace the corpus with a licensed public-real dataset or DENSO data, freeze the real test groups, and rerun the same protocol.",
            "",
            "## Traceability",
            "",
            "- Raw run records: `raw_metrics.json`",
            "- Summary: `summary.json`",
            "- Code commit and environment lock must be added when this is promoted to a submission run.",
        ]
    )
    report = directory / "benchmark_report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
