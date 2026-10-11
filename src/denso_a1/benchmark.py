from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from denso_a1.data.simulated import make_protocol_split, make_simulated_dataset
from denso_a1.eval.audits import budget_audit, leakage_audit
from denso_a1.eval.evaluator import evaluate
from denso_a1.generators.augment import t1_augment
from denso_a1.generators.physics import PhysicsConfig, T0Generator
from denso_a1.schema import SampleBatch


def _concat(*batches: SampleBatch) -> SampleBatch:
    signals = np.concatenate([batch.signals for batch in batches], axis=0)
    metadata = [item for batch in batches for item in batch.metadata]
    return SampleBatch(signals, metadata)


def _bootstrap_ci(values: np.ndarray, seed: int) -> tuple[float, float]:
    if len(values) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    samples = np.asarray([np.mean(rng.choice(values, size=len(values), replace=True)) for _ in range(2_000)])
    return float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def run_benchmark(out_dir: str | Path, *, seeds: int = 5, k_values: tuple[int, ...] = (0, 1, 2)) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    generator = T0Generator(PhysicsConfig())
    for run_seed in range(seeds):
        corpus = make_simulated_dataset(seed=100 + run_seed)
        for k in k_values:
            split = make_protocol_split(corpus, k=k, split_seed=run_seed, subset_seed=10_000 + run_seed)
            real_train = corpus.subset(split.train)
            val = corpus.subset(split.val)
            test = corpus.subset(split.test)
            audit = leakage_audit(real_train, val, test)
            if not audit["pass"]:
                raise RuntimeError(f"hard-stop leakage audit failed: {audit}")
            fault_parents = np.asarray([i for i in split.train if corpus.metadata[int(i)].label_binary == 1], dtype=int)
            normal_parents = np.asarray([i for i in split.train if corpus.metadata[int(i)].label_binary == 0], dtype=int)
            if k == 0:
                m = min(len(normal_parents), 8)
                one_class_rows = [("E0", evaluate(real_train, test, fs_hz=1_000, seed=run_seed, one_class=True))]
                t0 = generator.generate_from_parents(corpus, normal_parents[:m], seed=20_000 + run_seed, split_seed=run_seed)
                t0_train = _concat(real_train, t0)
                one_class_rows.append(("E2", evaluate(t0_train, test, fs_hz=1_000, seed=run_seed)))
                methods = one_class_rows
                budget = {"pass": True, "note": "k=0 protocol compares one-class to T0 pseudo-fault supervision"}
            else:
                m = len(fault_parents)
                t1 = t1_augment(corpus, fault_parents, seed=30_000 + run_seed)
                t0_parent_indices = np.resize(normal_parents, m)
                t0 = generator.generate_from_parents(corpus, t0_parent_indices, seed=20_000 + run_seed, split_seed=run_seed)
                e0 = evaluate(real_train, test, fs_hz=1_000, seed=run_seed)
                e1_train = _concat(real_train, t1)
                e2_train = _concat(real_train, t0)
                methods = [("E0", e0), ("E1", evaluate(e1_train, test, fs_hz=1_000, seed=run_seed)), ("E2", evaluate(e2_train, test, fs_hz=1_000, seed=run_seed))]
                budget = budget_audit(real_train, e1_train, expected_total=len(real_train.signals) + m)
                budget["t0_total"] = len(e2_train.signals)
                budget["budget_match_t0_t1"] = len(e2_train.signals) == len(e1_train.signals)
                if not budget["pass"] or not budget["budget_match_t0_t1"]:
                    raise RuntimeError(f"hard-stop budget audit failed: {budget}")
            for method, metrics in methods:
                rows.append(
                    {
                        "run_id": f"E{method[1:]}-k{k}-seed{run_seed}",
                        "method": method,
                        "k_fault_groups": k,
                        "split_seed": run_seed,
                        "subset_seed": 10_000 + run_seed,
                        "generator_seed": 20_000 + run_seed,
                        "model_seed": run_seed,
                        "selected_fault_groups": list(split.selected_fault_groups),
                        "train_group_count": len(split.train_groups),
                        "val_group_count": len(split.val_groups),
                        "test_group_count": len(split.test_groups),
                        "source_type": "simulated",
                        "metrics": metrics,
                        "leakage_audit": audit,
                        "budget_audit": budget,
                    }
                )
    raw_path = out / "raw_metrics.json"
    raw_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    summary = aggregate_results(rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"rows": rows, "summary": summary}


def aggregate_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(f"k={row['k_fault_groups']}:{row['method']}", []).append(row["metrics"]["pr_auc"])
    summary: dict[str, Any] = {"primary_metric": "pr_auc", "groups": {}}
    for key, values in sorted(grouped.items()):
        array = np.asarray(values)
        lo, hi = _bootstrap_ci(array, seed=42)
        summary["groups"][key] = {"n": len(values), "mean": float(array.mean()), "ci95": [lo, hi]}
    for k in sorted({row["k_fault_groups"] for row in rows}):
        baseline = np.asarray([row["metrics"]["pr_auc"] for row in rows if row["k_fault_groups"] == k and row["method"] == "E0"])
        t0 = np.asarray([row["metrics"]["pr_auc"] for row in rows if row["k_fault_groups"] == k and row["method"] == "E2"])
        if len(baseline) and len(t0):
            delta = t0 - baseline
            lo, hi = _bootstrap_ci(delta, seed=100 + k)
            summary.setdefault("paired_deltas", {})[f"k={k}:E2-E0"] = {
                "mean_delta": float(delta.mean()), "ci95": [lo, hi], "n": len(delta)
            }
    return summary
