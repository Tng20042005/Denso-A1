from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from denso_a1.benchmark import _bootstrap_ci
from denso_a1.data.cwru import CWRUDataset, load_cwru, make_cwru_cross_load_split
from denso_a1.data.preprocess import SignalPreprocessor
from denso_a1.data.public_split import public_real_test_audit
from denso_a1.data.simulated import make_protocol_split
from denso_a1.eval.audits import budget_audit, leakage_audit
from denso_a1.eval.evaluator import evaluate_with_trace
from denso_a1.generators.augment import t1_augment
from denso_a1.generators.physics import PhysicsConfig, T0Generator
from denso_a1.schema import SampleBatch


def _concat(*batches: SampleBatch) -> SampleBatch:
    return SampleBatch(
        np.concatenate([batch.signals for batch in batches], axis=0),
        [item for batch in batches for item in batch.metadata],
    )


def _choose_parents(indices: np.ndarray, count: int, seed: int) -> np.ndarray:
    if len(indices) == 0:
        raise ValueError("cannot choose generated parents from an empty class")
    rng = np.random.default_rng(seed)
    if count <= len(indices):
        return rng.choice(indices, size=count, replace=False)
    return rng.choice(indices, size=count, replace=True)


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _hash_array(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def _training_trace(batch: SampleBatch) -> dict[str, Any]:
    sample_ids = [item.sample_id for item in batch.metadata]
    group_ids = sorted({item.group_id for item in batch.metadata})
    source_type_counts = Counter(item.source_type for item in batch.metadata)
    class_counts = Counter(str(item.label_binary) for item in batch.metadata)
    generated_ids = [item.sample_id for item in batch.metadata if item.source_type == "generated"]
    return {
        "total_samples": len(batch.metadata),
        "real_samples": sum(
            count for source, count in source_type_counts.items() if source != "generated"
        ),
        "generated_samples": len(generated_ids),
        "source_type_counts": dict(sorted(source_type_counts.items())),
        "class_counts": dict(sorted(class_counts.items())),
        "sample_ids": sample_ids,
        "group_ids": group_ids,
        "generated_sample_ids": generated_ids,
        "sample_id_hash": _hash_json(sample_ids),
        "group_id_hash": _hash_json(group_ids),
        "signal_hash": _hash_array(batch.signals.astype(np.float64, copy=False)),
        "generated_sample_id_hash": _hash_json(generated_ids),
    }


def _training_difference_audit(traces: dict[str, dict[str, Any]]) -> dict[str, Any]:
    comparisons: dict[str, dict[str, Any]] = {}
    baseline = traces.get("E0")
    if baseline is None:
        return {"pass": False, "reason": "missing E0 training trace", "comparisons": comparisons}
    for method in ("E1", "E2"):
        if method not in traces:
            continue
        candidate = traces[method]
        comparison = {
            "real_count_equal_to_e0": candidate["real_samples"] == baseline["real_samples"],
            "generated_count_positive": candidate["generated_samples"] > 0,
            "total_count_greater_than_e0": candidate["total_samples"] > baseline["total_samples"],
            "sample_id_hash_differs_from_e0": candidate["sample_id_hash"] != baseline["sample_id_hash"],
            "signal_hash_differs_from_e0": candidate["signal_hash"] != baseline["signal_hash"],
        }
        comparison["pass"] = all(comparison.values())
        comparisons[f"{method}-E0"] = comparison
    if "E1" in traces and "E2" in traces:
        e1 = traces["E1"]
        e2 = traces["E2"]
        comparison = {
            "total_count_equal": e1["total_samples"] == e2["total_samples"],
            "sample_id_hash_differs": e1["sample_id_hash"] != e2["sample_id_hash"],
            "signal_hash_differs": e1["signal_hash"] != e2["signal_hash"],
        }
        comparison["pass"] = all(comparison.values())
        comparisons["E1-E2"] = comparison
    return {
        "pass": bool(comparisons) and all(item["pass"] for item in comparisons.values()),
        "comparisons": comparisons,
    }


def _evaluate_arm(
    train: SampleBatch,
    test: SampleBatch,
    *,
    seed: int,
    fs_hz: float = 12_000.0,
    one_class: bool = False,
) -> tuple[dict[str, float], dict[str, object], dict[str, Any]]:
    metrics, prediction_trace = evaluate_with_trace(
        train, test, fs_hz=fs_hz, seed=seed, one_class=one_class
    )
    return metrics, prediction_trace, _training_trace(train)


def _row(
    *,
    method: str,
    k: int,
    seed: int,
    split: Any,
    metrics: dict[str, float],
    leakage: dict[str, Any],
    public_test: dict[str, Any],
    budget: dict[str, Any],
    files: tuple[Any, ...],
    prediction_trace: dict[str, object],
    training_trace: dict[str, Any],
    training_audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": f"CWRU-{method}-k{k}-seed{seed}",
        "experiment": "E4_k_sweep",
        "dataset": "CWRU_Bearing_Data_Center",
        "method": method,
        "k_fault_groups": k,
        "split_mode": split.split_mode,
        "heldout_load_hp": split.heldout_load_hp,
        "val_load_hp": split.val_load_hp,
        "split_seed": seed,
        "subset_seed": 10_000 + seed,
        "generator_seed": 20_000 + seed,
        "model_seed": seed,
        "selected_fault_groups": list(split.selected_fault_groups),
        "train_group_ids": list(split.train_groups),
        "val_group_ids": list(split.val_groups),
        "test_group_ids": list(split.test_groups),
        "train_group_count": len(split.train_groups),
        "val_group_count": len(split.val_groups),
        "test_group_count": len(split.test_groups),
        "source_type": "public_real",
        "fault_origin": "seeded_physical",
        "raw_file_checksums": {str(item.file_id): item.sha256 for item in files},
        "metrics": metrics,
        "prediction_trace": prediction_trace,
        "training_trace": training_trace,
        "training_difference_audit": training_audit,
        "leakage_audit": leakage,
        "public_real_test_audit": public_test,
        "budget_audit": budget,
    }


def run_cwru_benchmark(
    raw_root: str | Path,
    out_dir: str | Path,
    *,
    seeds: int = 5,
    k_values: tuple[int, ...] = (0, 1, 2),
    window_size: int = 4096,
    split_mode: str = "random_group",
) -> dict[str, Any]:
    """Run E0/E1/E2 and E4 with provenance and prediction audits."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dataset: CWRUDataset = load_cwru(raw_root, window_size=window_size)
    rows: list[dict[str, Any]] = []
    split_manifests: list[dict[str, Any]] = []
    generator = T0Generator(
        PhysicsConfig(fs_hz=12_000.0, f_fault_hz=120.0, f_res_hz=3_000.0, snr_db=14.0)
    )
    for seed in range(seeds):
        for k in k_values:
            if split_mode == "cross_load":
                split = make_cwru_cross_load_split(
                    dataset.batch, k=k, split_seed=seed, subset_seed=10_000 + seed
                )
            elif split_mode == "random_group":
                split = make_protocol_split(
                    dataset.batch, k=k, split_seed=seed, subset_seed=10_000 + seed
                )
            else:
                raise ValueError(f"unsupported split_mode={split_mode}")
            raw_train = dataset.batch.subset(split.train)
            raw_test = dataset.batch.subset(split.test)
            public_test = public_real_test_audit(raw_test)
            if not public_test["pass"]:
                raise RuntimeError(f"hard-stop: invalid public-real test: {public_test}")
            preprocessor = SignalPreprocessor()
            processed_corpus = preprocessor.fit(raw_train).transform(dataset.batch)
            train = processed_corpus.subset(split.train)
            val = processed_corpus.subset(split.val)
            test = processed_corpus.subset(split.test)
            leakage = leakage_audit(train, val, test)
            if not leakage["pass"]:
                raise RuntimeError(f"hard-stop: leakage audit failed: {leakage}")
            split_manifests.append(
                {
                    "dataset": "CWRU_Bearing_Data_Center",
                    "experiment": "E4_k_sweep",
                    "split_mode": split.split_mode,
                    "split_seed": seed,
                    "subset_seed": 10_000 + seed,
                    "k_fault_groups": k,
                    "train_group_ids": list(split.train_groups),
                    "val_group_ids": list(split.val_groups),
                    "test_group_ids": list(split.test_groups),
                    "heldout_load_hp": split.heldout_load_hp,
                    "val_load_hp": split.val_load_hp,
                    "test_source_types": public_test["source_types"],
                    "test_fault_groups": public_test["fault_groups"],
                }
            )
            fault_parents = np.asarray(
                [i for i in split.train if dataset.batch.metadata[int(i)].label_binary == 1], dtype=int
            )
            normal_parents = np.asarray(
                [i for i in split.train if dataset.batch.metadata[int(i)].label_binary == 0], dtype=int
            )
            if k == 0:
                m = min(len(normal_parents), 32)
                e0_metrics, e0_prediction, e0_trace = _evaluate_arm(
                    train, test, seed=seed, one_class=True
                )
                t0_parents = _choose_parents(normal_parents, m, 20_000 + seed)
                t0 = generator.generate_from_parents(
                    processed_corpus, t0_parents, seed=20_000 + seed, split_seed=seed
                )
                e2_train = _concat(train, t0)
                e2_metrics, e2_prediction, e2_trace = _evaluate_arm(e2_train, test, seed=seed)
                traces = {"E0": e0_trace, "E2": e2_trace}
                training_audit = _training_difference_audit(traces)
                if not training_audit["pass"]:
                    raise RuntimeError(f"hard-stop: training-set difference audit failed: {training_audit}")
                rows.extend(
                    [
                        _row(
                            method="E0", k=k, seed=seed, split=split, metrics=e0_metrics,
                            leakage=leakage, public_test=public_test,
                            budget={"pass": True, "protocol": "one_class_k0"}, files=dataset.files,
                            prediction_trace=e0_prediction, training_trace=e0_trace,
                            training_audit=training_audit,
                        ),
                        _row(
                            method="E2", k=k, seed=seed, split=split, metrics=e2_metrics,
                            leakage=leakage, public_test=public_test,
                            budget={"pass": True, "protocol": "t0_pseudo_fault_k0", "generated_count": m},
                            files=dataset.files, prediction_trace=e2_prediction,
                            training_trace=e2_trace, training_audit=training_audit,
                        ),
                    ]
                )
            else:
                m = min(len(fault_parents), 32)
                t1_parents = _choose_parents(fault_parents, m, 30_000 + seed)
                t0_parents = _choose_parents(normal_parents, m, 20_000 + seed)
                t1 = t1_augment(processed_corpus, t1_parents, seed=30_000 + seed)
                t0 = generator.generate_from_parents(
                    processed_corpus, t0_parents, seed=20_000 + seed, split_seed=seed
                )
                e0, e0_prediction, e0_trace = _evaluate_arm(train, test, seed=seed)
                e1_train = _concat(train, t1)
                e2_train = _concat(train, t0)
                budget = budget_audit(train, e1_train, expected_total=len(train.signals) + m)
                budget["t0_total"] = len(e2_train.signals)
                budget["budget_match_t0_t1"] = len(e2_train.signals) == len(e1_train.signals)
                budget["pass"] = bool(budget["pass"] and budget["budget_match_t0_t1"])
                if not budget["pass"]:
                    raise RuntimeError(f"hard-stop: budget audit failed: {budget}")
                e1, e1_prediction, e1_trace = _evaluate_arm(e1_train, test, seed=seed)
                e2, e2_prediction, e2_trace = _evaluate_arm(e2_train, test, seed=seed)
                traces = {"E0": e0_trace, "E1": e1_trace, "E2": e2_trace}
                training_audit = _training_difference_audit(traces)
                if not training_audit["pass"]:
                    raise RuntimeError(f"hard-stop: training-set difference audit failed: {training_audit}")
                rows.extend(
                    [
                        _row(
                            method="E0", k=k, seed=seed, split=split, metrics=e0,
                            leakage=leakage, public_test=public_test,
                            budget={"pass": True, "protocol": "real_only", "real_train_count": len(train.signals)},
                            files=dataset.files, prediction_trace=e0_prediction,
                            training_trace=e0_trace, training_audit=training_audit,
                        ),
                        _row(
                            method="E1", k=k, seed=seed, split=split, metrics=e1,
                            leakage=leakage, public_test=public_test,
                            budget={**budget, "method": "E1"}, files=dataset.files,
                            prediction_trace=e1_prediction, training_trace=e1_trace,
                            training_audit=training_audit,
                        ),
                        _row(
                            method="E2", k=k, seed=seed, split=split, metrics=e2,
                            leakage=leakage, public_test=public_test,
                            budget={**budget, "method": "E2"}, files=dataset.files,
                            prediction_trace=e2_prediction, training_trace=e2_trace,
                            training_audit=training_audit,
                        ),
                    ]
                )
    (out / "raw_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "split_manifest.json").write_text(json.dumps(split_manifests, indent=2), encoding="utf-8")
    summary = aggregate_public_results(rows)
    summary["dataset_files"] = [item.__dict__ for item in dataset.files]
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"rows": rows, "summary": summary}


def aggregate_public_results(
    rows: list[dict[str, Any]],
    *,
    dataset: str = "CWRU_Bearing_Data_Center",
    experiment: str = "E4_k_sweep",
) -> dict[str, Any]:
    metric_names = ("pr_auc", "f1")
    grouped: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        group = grouped.setdefault(f"k={row['k_fault_groups']}:{row['method']}", {})
        for metric in metric_names:
            group.setdefault(metric, []).append(row["metrics"][metric])
    summary: dict[str, Any] = {
        "dataset": dataset,
        "experiment": experiment,
        "split_mode": sorted({row.get("split_mode", "unknown") for row in rows}),
        "source_type": "public_real",
        "primary_metric": "pr_auc",
        "k_values": sorted({row["k_fault_groups"] for row in rows}),
        "groups": {},
        "all_public_real_test_audits_pass": all(row["public_real_test_audit"]["pass"] for row in rows),
        "all_leakage_audits_pass": all(row["leakage_audit"]["pass"] for row in rows),
        "all_budget_audits_pass": all(row["budget_audit"].get("pass", True) for row in rows),
        "all_training_difference_audits_pass": all(
            row.get("training_difference_audit", {"pass": True})["pass"] for row in rows
        ),
    }
    summary["method_coverage"] = {
        str(k): sorted({row["method"] for row in rows if row["k_fault_groups"] == k})
        for k in summary["k_values"]
    }
    for key, metric_values in sorted(grouped.items()):
        summary["groups"][key] = {"n": len(next(iter(metric_values.values()))), "metrics": {}}
        for metric, values in metric_values.items():
            array = np.asarray(values)
            lo, hi = _bootstrap_ci(array, seed=42)
            summary["groups"][key]["metrics"][metric] = {
                "mean": float(array.mean()), "ci95": [lo, hi]
            }
    for k in sorted({row["k_fault_groups"] for row in rows}):
        by_seed = {}
        for row in rows:
            if row["k_fault_groups"] == k:
                by_seed.setdefault(row["model_seed"], {})[row["method"]] = row["metrics"]
        for comparator in ("E0", "E1"):
            paired = [values for values in by_seed.values() if "E2" in values and comparator in values]
            if paired:
                result = {"n": len(paired), "metrics": {}}
                for metric in metric_names:
                    deltas = np.asarray(
                        [values["E2"][metric] - values[comparator][metric] for values in paired]
                    )
                    lo, hi = _bootstrap_ci(deltas, seed=100 + k)
                    result["metrics"][metric] = {
                        "mean_delta": float(deltas.mean()), "ci95": [lo, hi]
                    }
                summary.setdefault("paired_deltas", {})[f"k={k}:E2-{comparator}"] = result
    return summary
