from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from denso_a1.data.paderborn import (
    PaderbornDataset,
    load_paderborn,
    make_paderborn_bearing_split,
)
from denso_a1.data.preprocess import SignalPreprocessor
from denso_a1.data.public_split import public_real_test_audit
from denso_a1.eval.audits import budget_audit, leakage_audit
from denso_a1.generators.augment import t1_augment
from denso_a1.generators.physics import PhysicsConfig, T0Generator
from denso_a1.public_benchmark import (
    _choose_parents,
    _concat,
    _evaluate_arm,
    _training_difference_audit,
    aggregate_public_results,
)


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
    dataset: PaderbornDataset,
    prediction_trace: dict[str, object],
    training_trace: dict[str, Any],
    training_audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": f"PADERBORN-{method}-k{k}-seed{seed}",
        "experiment": "Paderborn_E4_k_sweep",
        "dataset": "Paderborn_Bearing_DataCenter",
        "method": method,
        "k_fault_groups": k,
        "split_mode": split.split_mode,
        "condition_id": dataset.condition_id,
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
        "fault_origin": "accelerated_degradation",
        "raw_file_checksums": {
            f"{item.bearing_id}/{Path(item.path).name}": item.sha256 for item in dataset.files
        },
        "metrics": metrics,
        "prediction_trace": prediction_trace,
        "training_trace": training_trace,
        "training_difference_audit": training_audit,
        "leakage_audit": leakage,
        "public_real_test_audit": public_test,
        "budget_audit": budget,
    }


def run_paderborn_benchmark(
    raw_root: str | Path,
    out_dir: str | Path,
    *,
    seeds: int = 5,
    k_values: tuple[int, ...] = (0, 1, 2),
    condition_id: str = "N15_M07_F10",
    window_size: int = 4096,
    measurement_indices: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dataset = load_paderborn(
        raw_root,
        condition_id=condition_id,
        window_size=window_size,
        measurement_indices=measurement_indices,
    )
    rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    generator = T0Generator(
        PhysicsConfig(fs_hz=64_000.0, f_fault_hz=120.0, f_res_hz=6_000.0, snr_db=14.0)
    )
    for seed in range(seeds):
        for k in k_values:
            split = make_paderborn_bearing_split(
                dataset.batch, k=k, split_seed=seed, subset_seed=10_000 + seed
            )
            raw_train = dataset.batch.subset(split.train)
            raw_test = dataset.batch.subset(split.test)
            public_test = public_real_test_audit(raw_test)
            if not public_test["pass"]:
                raise RuntimeError(f"hard-stop: invalid Paderborn public-real test: {public_test}")
            processed_corpus = SignalPreprocessor().fit(raw_train).transform(dataset.batch)
            train = processed_corpus.subset(split.train)
            val = processed_corpus.subset(split.val)
            test = processed_corpus.subset(split.test)
            leakage = leakage_audit(train, val, test)
            if not leakage["pass"]:
                raise RuntimeError(f"hard-stop: Paderborn leakage audit failed: {leakage}")
            manifests.append(
                {
                    "dataset": "Paderborn_Bearing_DataCenter",
                    "experiment": "Paderborn_E4_k_sweep",
                    "split_mode": split.split_mode,
                    "condition_id": condition_id,
                    "measurement_indices": list(measurement_indices),
                    "split_seed": seed,
                    "subset_seed": 10_000 + seed,
                    "k_fault_groups": k,
                    "train_group_ids": list(split.train_groups),
                    "val_group_ids": list(split.val_groups),
                    "test_group_ids": list(split.test_groups),
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
                e0, e0_prediction, e0_trace = _evaluate_arm(
                    train, test, seed=seed, fs_hz=64_000.0, one_class=True
                )
                t0_parents = _choose_parents(normal_parents, m, 20_000 + seed)
                t0 = generator.generate_from_parents(
                    processed_corpus, t0_parents, seed=20_000 + seed, split_seed=seed
                )
                e2_train = _concat(train, t0)
                e2, e2_prediction, e2_trace = _evaluate_arm(
                    e2_train, test, seed=seed, fs_hz=64_000.0
                )
                traces = {"E0": e0_trace, "E2": e2_trace}
                training_audit = _training_difference_audit(traces)
                if not training_audit["pass"]:
                    raise RuntimeError(f"hard-stop: Paderborn training audit failed: {training_audit}")
                row_args = [
                    ("E0", e0, e0_prediction, e0_trace, {"pass": True, "protocol": "one_class_k0"}),
                    ("E2", e2, e2_prediction, e2_trace, {"pass": True, "protocol": "t0_pseudo_fault_k0", "generated_count": m}),
                ]
            else:
                m = min(len(fault_parents), 32)
                t1_parents = _choose_parents(fault_parents, m, 30_000 + seed)
                t0_parents = _choose_parents(normal_parents, m, 20_000 + seed)
                t1 = t1_augment(processed_corpus, t1_parents, seed=30_000 + seed)
                t0 = generator.generate_from_parents(
                    processed_corpus, t0_parents, seed=20_000 + seed, split_seed=seed
                )
                e0, e0_prediction, e0_trace = _evaluate_arm(train, test, seed=seed, fs_hz=64_000.0)
                e1_train = _concat(train, t1)
                e2_train = _concat(train, t0)
                budget = budget_audit(train, e1_train, expected_total=len(train.signals) + m)
                budget["t0_total"] = len(e2_train.signals)
                budget["budget_match_t0_t1"] = len(e2_train.signals) == len(e1_train.signals)
                budget["pass"] = bool(budget["pass"] and budget["budget_match_t0_t1"])
                if not budget["pass"]:
                    raise RuntimeError(f"hard-stop: Paderborn budget audit failed: {budget}")
                e1, e1_prediction, e1_trace = _evaluate_arm(e1_train, test, seed=seed, fs_hz=64_000.0)
                e2, e2_prediction, e2_trace = _evaluate_arm(e2_train, test, seed=seed, fs_hz=64_000.0)
                traces = {"E0": e0_trace, "E1": e1_trace, "E2": e2_trace}
                training_audit = _training_difference_audit(traces)
                if not training_audit["pass"]:
                    raise RuntimeError(f"hard-stop: Paderborn training audit failed: {training_audit}")
                row_args = [
                    ("E0", e0, e0_prediction, e0_trace, {"pass": True, "protocol": "real_only"}),
                    ("E1", e1, e1_prediction, e1_trace, {**budget, "method": "E1"}),
                    ("E2", e2, e2_prediction, e2_trace, {**budget, "method": "E2"}),
                ]
            for method, metrics, prediction, trace, budget in row_args:
                rows.append(
                    _row(
                        method=method, k=k, seed=seed, split=split, metrics=metrics,
                        leakage=leakage, public_test=public_test, budget=budget,
                        dataset=dataset, prediction_trace=prediction, training_trace=trace,
                        training_audit=training_audit,
                    )
                )
    (out / "raw_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "split_manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    summary = aggregate_public_results(
        rows, dataset="Paderborn_Bearing_DataCenter", experiment="Paderborn_E4_k_sweep"
    )
    summary["condition_id"] = condition_id
    summary["measurement_indices"] = list(measurement_indices)
    summary["dataset_description"] = (
        "Official Paderborn vibration_1 recordings at fixed N15_M07_F10 condition; "
        f"healthy and accelerated-lifetime real-damage bearings; measurements {list(measurement_indices)}."
    )
    summary["license"] = "CC BY-NC 4.0; citation required; no commercial redistribution"
    summary["dataset_files"] = [item.__dict__ for item in dataset.files]
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"rows": rows, "summary": summary}
