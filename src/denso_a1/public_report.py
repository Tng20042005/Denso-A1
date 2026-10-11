from __future__ import annotations

import json
from pathlib import Path


def _metric_cell(value: dict[str, float], key: str) -> str:
    return f"{value[key]:.4f} [{value['ci95'][0]:.4f}, {value['ci95'][1]:.4f}]"


def _json_cell(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _write_run_audit(directory: Path, rows: list[dict[str, object]]) -> Path:
    lines = [
        "# Per-run training and prediction audit",
        "",
        "This audit is generated from `raw_metrics.json`. The raw JSON retains the full training sample IDs; this table provides the per-run counts, group IDs, hashes, and prediction hashes used by the hard gates.",
        "",
        "| Run | Train real | Train generated | Class counts | Train groups | Sample-ID hash | Signal hash | Prediction hash | Difference audit | Leakage | Public-real test | Budget |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        training = row["training_trace"]
        prediction = row["prediction_trace"]
        lines.append(
            "| {run} | {real} | {generated} | `{classes}` | `{groups}` | `{sample}` | `{signal}` | `{prediction}` | {difference} | {leakage} | {public} | {budget} |".format(
                run=row["run_id"],
                real=training["real_samples"],
                generated=training["generated_samples"],
                classes=_json_cell(training["class_counts"]),
                groups="; ".join(training["group_ids"]),
                sample=training["sample_id_hash"],
                signal=training["signal_hash"],
                prediction=prediction["prediction_hash"],
                difference=row["training_difference_audit"]["pass"],
                leakage=row["leakage_audit"]["pass"],
                public=row["public_real_test_audit"]["pass"],
                budget=row["budget_audit"]["pass"],
            )
        )
    path = directory / "run_audit.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_public_benchmark_report(benchmark_dir: str | Path) -> Path:
    directory = Path(benchmark_dir)
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    rows = json.loads((directory / "raw_metrics.json").read_text(encoding="utf-8"))
    split_mode = ", ".join(summary.get("split_mode", ["unknown"]))
    dataset = summary.get("dataset", "public-real dataset")
    experiment = summary.get("experiment", "E4_k_sweep")
    baseline_pr_auc = [
        value["metrics"]["pr_auc"]["mean"]
        for key, value in summary["groups"].items()
        if key.endswith(":E0")
    ]
    difficulty_note = (
        "PR-AUC near 1.0 across E0 indicates that this benchmark may be too easy for ranking methods, even when F1 is lower."
        if baseline_pr_auc and min(baseline_pr_auc) >= 0.99
        else "E0 is not saturated at PR-AUC≈1.0 across all k values; this benchmark provides non-trivial room for paired comparison."
    )
    lines = [
        f"# {dataset} public-real benchmark report",
        "",
        f"Experiment: `{experiment}` over `k={{0,1,2}}`; E0/E1/E2 are the paired arms within each supported k.",
        "",
        "## Benchmark validity",
        "",
        f"Split mode: `{split_mode}`. Seeds per reported group: 5.",
        "Audits: public-real test `{}`; leakage `{}`; budget `{}`; training-set difference `{}`{}.".format(
            summary["all_public_real_test_audits_pass"],
            summary["all_leakage_audits_pass"],
            summary["all_budget_audits_pass"],
            summary.get("all_training_difference_audits_pass", "not recorded"),
            f"; calibration `{summary['all_calibration_audits_pass']}`"
            if "all_calibration_audits_pass" in summary
            else "",
        ),
        f"Method coverage by k: `{summary.get('method_coverage', {})}`.",
        "",
        summary.get(
            "dataset_description",
            "This report uses measured CWRU vibration recordings downloaded from the official Bearing Data Center. Faults are seeded physical faults; they are not DENSO data and not field-observed faults.",
        ),
        "",
        "## Baseline difficulty",
        "",
        "The table below shows the evaluator result before comparing T0 utility. " + difficulty_note,
        "",
        "| Setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |",
        "| --- | ---: | --- | --- |",
    ]
    for key, value in summary["groups"].items():
        pr_auc = value["metrics"]["pr_auc"]
        f1 = value["metrics"]["f1"]
        lines.append(
            f"| {key} | {value['n']} | {_metric_cell(pr_auc, 'mean')} | {_metric_cell(f1, 'mean')} |"
        )
    lines.extend(
        [
            "",
            "## Paired utility of T0",
            "",
            "Positive utility would require a reproducible positive paired delta on held-out measured faults. E2 is compared with E0 and E1 under the same split, subset and model seed.",
            "",
            "| Comparison | n | PR-AUC mean delta [95% CI] | F1 mean delta [95% CI] |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for key, value in summary.get("paired_deltas", {}).items():
        pr_auc = value["metrics"]["pr_auc"]
        f1 = value["metrics"]["f1"]
        lines.append(
            f"| {key} | {value['n']} | {_metric_cell(pr_auc, 'mean_delta')} | {_metric_cell(f1, 'mean_delta')} |"
        )
    lines.extend(
        [
            "",
            "## Negative results and interpretation",
            "",
            "The result is not a T0 utility claim. If paired deltas are zero or their intervals include zero, T0 is not shown to improve this evaluator on this benchmark. A negative F1 delta is retained rather than hidden behind PR-AUC.",
            "",
            f"This is evidence on the {dataset} benchmark only. It does not establish transfer to DENSO or naturally occurring field faults. The split is frozen by raw recording group/condition, and generated samples are restricted to train parents.",
            "",
            "## Traceability",
            "",
            "- Raw per-run rows: `raw_metrics.json` (training sample/group IDs, class counts, source counts, hashes, prediction hashes)",
            "- Per-run audit table: `run_audit.md`",
            "- Frozen group manifests: `split_manifest.json`",
            "- Dataset file checksums: `summary.json`",
        ]
    )
    report = directory / "benchmark_report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_run_audit(directory, rows)
    return report
