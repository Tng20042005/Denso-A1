from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from denso_a1.data.paderborn import load_paderborn
from denso_a1.data.preprocess import SignalPreprocessor
from denso_a1.data.public_split import public_real_test_audit
from denso_a1.data.simulated import ProtocolSplit
from denso_a1.eval.audits import budget_audit, leakage_audit
from denso_a1.generators.augment import t1_augment
from denso_a1.generators.physics import (
    T0V2Config,
    T0V2Generator,
    calibrate_t0v2_from_training_faults,
)
from denso_a1.public_benchmark import (
    _choose_parents,
    _concat,
    _evaluate_arm,
    _training_difference_audit,
    aggregate_public_results,
)
from denso_a1.schema import SampleBatch

TRAIN_CONDITION = "N15_M07_F10"
TEST_CONDITION = "N09_M07_F10"
TRAIN_HEALTHY = ("K001", "K002")
VAL_BEARINGS = ("K004", "KA16", "KI04")
TRAIN_FAULTS = ("KA04", "KA15")
TEST_BEARINGS = ("K003", "KI14", "KI16")


def _freeze_payload(measurements: tuple[int, ...]) -> dict[str, Any]:
    return {
        "protocol": "Paderborn_T0_v2_final_holdout_v1",
        "dataset": "Paderborn_Bearing_DataCenter",
        "train_condition": TRAIN_CONDITION,
        "test_condition": TEST_CONDITION,
        "train_healthy_bearings": list(TRAIN_HEALTHY),
        "train_fault_bearings_by_k": {"0": [], "1": ["KA04"], "2": ["KA04", "KA15"]},
        "validation_bearings": list(VAL_BEARINGS),
        "test_bearings": list(TEST_BEARINGS),
        "measurement_indices": list(measurements),
        "window_size": 4096,
        "step": 4096,
        "fs_hz": 64_000.0,
        "methods": {"E0": "real_only", "E1": "T1_budget_matched", "E2": "T0_v2"},
        "seeds": {"split": 0, "reported_model_seeds": [0, 1, 2, 3, 4]},
        "budget": {"generated_per_seed": 32, "match_E1_E2": True},
        "calibration": {
            "k0": "fixed physics-only T0V2Config; no real fault information",
            "k_ge_1": "median envelope fault-frequency and PSD resonance anchors from selected train fault groups only",
            "forbidden": ["validation faults", "final-test faults", "old Paderborn test metrics"],
        },
        "final_holdout_rule": "test is bearing-disjoint and condition-disjoint from train and validation; test is measured public_real only",
        "t2": "deferred",
    }


def write_t0_v2_protocol_freeze(path: str | Path, *, measurements: tuple[int, ...] = (1, 2, 3, 4, 5)) -> Path:
    target = Path(path)
    payload = _freeze_payload(measurements)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_final_corpus(raw_root: str | Path, measurements: tuple[int, ...]) -> tuple[SampleBatch, tuple[Any, ...]]:
    train_val = TRAIN_HEALTHY + TRAIN_FAULTS + VAL_BEARINGS
    train_dataset = load_paderborn(
        raw_root,
        bearing_ids=train_val,
        condition_id=TRAIN_CONDITION,
        measurement_indices=measurements,
    )
    test_dataset = load_paderborn(
        raw_root,
        bearing_ids=TEST_BEARINGS,
        condition_id=TEST_CONDITION,
        measurement_indices=measurements,
    )
    batch = SampleBatch(
        np.concatenate([train_dataset.batch.signals, test_dataset.batch.signals], axis=0),
        train_dataset.batch.metadata + test_dataset.batch.metadata,
    )
    return batch, train_dataset.files + test_dataset.files


def _final_split(batch: SampleBatch, k: int) -> ProtocolSplit:
    selected_faults = TRAIN_FAULTS[:k]
    train_groups = {f"paderborn-bearing-{bearing}" for bearing in TRAIN_HEALTHY + selected_faults}
    val_groups = {f"paderborn-bearing-{bearing}" for bearing in VAL_BEARINGS}
    test_groups = {f"paderborn-bearing-{bearing}" for bearing in TEST_BEARINGS}
    train = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in train_groups], dtype=int)
    val = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in val_groups], dtype=int)
    test = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in test_groups], dtype=int)
    if not train.size or not val.size or not test.size:
        raise ValueError("frozen T0-v2 split produced an empty partition")
    if {batch.metadata[int(i)].condition_id for i in test} != {TEST_CONDITION}:
        raise RuntimeError("final test condition is not frozen to the new holdout condition")
    if {batch.metadata[int(i)].condition_id for i in np.concatenate([train, val])} != {TRAIN_CONDITION}:
        raise RuntimeError("train/validation condition is not frozen to the calibration condition")
    return ProtocolSplit(
        train=train,
        val=val,
        test=test,
        selected_fault_groups=tuple(f"paderborn-bearing-{bearing}" for bearing in selected_faults),
        train_groups=tuple(sorted(train_groups)),
        val_groups=tuple(sorted(val_groups)),
        test_groups=tuple(sorted(test_groups)),
        split_mode="bearing_and_condition_disjoint_holdout",
    )


def _row(
    *,
    method: str,
    k: int,
    seed: int,
    split: ProtocolSplit,
    metrics: dict[str, float],
    leakage: dict[str, Any],
    public_test: dict[str, Any],
    budget: dict[str, Any],
    files: tuple[Any, ...],
    prediction_trace: dict[str, object],
    training_trace: dict[str, Any],
    training_audit: dict[str, Any],
    calibration_audit: dict[str, Any],
    v2_config: T0V2Config | None,
) -> dict[str, Any]:
    return {
        "run_id": f"PADERBORN-V2-{method}-k{k}-seed{seed}",
        "experiment": "Paderborn_T0_v2_E4_final_holdout",
        "dataset": "Paderborn_Bearing_DataCenter",
        "method": method,
        "k_fault_groups": k,
        "split_mode": split.split_mode,
        "train_condition": TRAIN_CONDITION,
        "test_condition": TEST_CONDITION,
        "split_seed": 0,
        "subset_seed": 10_000 + seed,
        "generator_seed": 20_000 + seed,
        "model_seed": seed,
        "selected_fault_groups": list(split.selected_fault_groups),
        "train_group_ids": list(split.train_groups),
        "val_group_ids": list(split.val_groups),
        "test_group_ids": list(split.test_groups),
        "source_type": "public_real",
        "fault_origin": "accelerated_degradation",
        "raw_file_checksums": {f"{item.bearing_id}/{Path(item.path).name}": item.sha256 for item in files},
        "metrics": metrics,
        "prediction_trace": prediction_trace,
        "training_trace": training_trace,
        "training_difference_audit": training_audit,
        "calibration_audit": calibration_audit,
        "leakage_audit": leakage,
        "public_real_test_audit": public_test,
        "budget_audit": budget,
        "t0_v2_config": v2_config.__dict__ if v2_config else None,
    }


def run_paderborn_v2_benchmark(
    raw_root: str | Path,
    out_dir: str | Path,
    *,
    freeze_path: str | Path,
    seeds: int = 5,
    measurements: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> dict[str, Any]:
    freeze = json.loads(Path(freeze_path).read_text(encoding="utf-8"))
    expected = _freeze_payload(measurements)
    if freeze != expected:
        raise RuntimeError("protocol freeze does not match the requested final benchmark")
    freeze_hash = _digest_file(Path(freeze_path))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    batch, files = _load_final_corpus(raw_root, measurements)
    rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    base_v2 = T0V2Config()
    for seed in range(seeds):
        for k in (0, 1, 2):
            split = _final_split(batch, k)
            raw_train = batch.subset(split.train)
            raw_test = batch.subset(split.test)
            public_test = public_real_test_audit(raw_test)
            if not public_test["pass"]:
                raise RuntimeError(f"hard-stop: invalid final public-real test: {public_test}")
            processed_corpus = SignalPreprocessor().fit(raw_train).transform(batch)
            train = processed_corpus.subset(split.train)
            val = processed_corpus.subset(split.val)
            test = processed_corpus.subset(split.test)
            leakage = leakage_audit(train, val, test)
            if not leakage["pass"]:
                raise RuntimeError(f"hard-stop: final leakage audit failed: {leakage}")
            manifests.append(
                {
                    "freeze_hash": freeze_hash,
                    "split_mode": split.split_mode,
                    "k_fault_groups": k,
                    "train_group_ids": list(split.train_groups),
                    "val_group_ids": list(split.val_groups),
                    "test_group_ids": list(split.test_groups),
                    "train_condition": TRAIN_CONDITION,
                    "test_condition": TEST_CONDITION,
                    "test_source_types": public_test["source_types"],
                }
            )
            normal_parents = np.asarray(
                [i for i in split.train if batch.metadata[int(i)].label_binary == 0], dtype=int
            )
            fault_parents = np.asarray(
                [i for i in split.train if batch.metadata[int(i)].label_binary == 1], dtype=int
            )
            selected_train_fault_groups = {
                batch.metadata[int(i)].group_id for i in fault_parents
            }
            calibration_audit = {
                "source_groups": sorted(selected_train_fault_groups),
                "source_is_train_only": selected_train_fault_groups.issubset(set(split.train_groups)),
                "validation_overlap": sorted(selected_train_fault_groups & set(split.val_groups)),
                "test_overlap": sorted(selected_train_fault_groups & set(split.test_groups)),
            }
            calibration_audit["pass"] = bool(
                calibration_audit["source_is_train_only"]
                and not calibration_audit["validation_overlap"]
                and not calibration_audit["test_overlap"]
            )
            if not calibration_audit["pass"]:
                raise RuntimeError(f"hard-stop: calibration audit failed: {calibration_audit}")
            if k == 0:
                v2_generator = T0V2Generator(base_v2)
            else:
                v2_config = calibrate_t0v2_from_training_faults(
                    train.signals[train.labels == 1], fs_hz=64_000.0, base=base_v2
                )
                v2_generator = T0V2Generator(v2_config)
            if k == 0:
                m = min(len(normal_parents), 32)
                e0, e0_prediction, e0_trace = _evaluate_arm(
                    train, test, seed=seed, fs_hz=64_000.0, one_class=True
                )
                t0 = v2_generator.generate_from_parents(
                    processed_corpus,
                    _choose_parents(normal_parents, m, 20_000 + seed),
                    seed=20_000 + seed,
                    split_seed=0,
                )
                e2_train = _concat(train, t0)
                e2, e2_prediction, e2_trace = _evaluate_arm(
                    e2_train, test, seed=seed, fs_hz=64_000.0
                )
                traces = {"E0": e0_trace, "E2": e2_trace}
                training_audit = _training_difference_audit(traces)
                budget = {"pass": True, "protocol": "t0_v2_pseudo_fault_k0", "generated_count": m}
                method_rows = [
                    ("E0", e0, e0_prediction, e0_trace, {"pass": True, "protocol": "one_class_k0"}),
                    ("E2", e2, e2_prediction, e2_trace, budget),
                ]
            else:
                m = min(len(fault_parents), 32)
                t1 = t1_augment(
                    processed_corpus,
                    _choose_parents(fault_parents, m, 30_000 + seed),
                    seed=30_000 + seed,
                )
                t0 = v2_generator.generate_from_parents(
                    processed_corpus,
                    _choose_parents(normal_parents, m, 20_000 + seed),
                    seed=20_000 + seed,
                    split_seed=0,
                )
                e0, e0_prediction, e0_trace = _evaluate_arm(train, test, seed=seed, fs_hz=64_000.0)
                e1_train = _concat(train, t1)
                e2_train = _concat(train, t0)
                budget = budget_audit(train, e1_train, expected_total=len(train.signals) + m)
                budget["t0_total"] = len(e2_train.signals)
                budget["budget_match_t0_t1"] = len(e2_train.signals) == len(e1_train.signals)
                budget["pass"] = bool(budget["pass"] and budget["budget_match_t0_t1"])
                if not budget["pass"]:
                    raise RuntimeError(f"hard-stop: final budget audit failed: {budget}")
                e1, e1_prediction, e1_trace = _evaluate_arm(e1_train, test, seed=seed, fs_hz=64_000.0)
                e2, e2_prediction, e2_trace = _evaluate_arm(e2_train, test, seed=seed, fs_hz=64_000.0)
                traces = {"E0": e0_trace, "E1": e1_trace, "E2": e2_trace}
                training_audit = _training_difference_audit(traces)
                method_rows = [
                    ("E0", e0, e0_prediction, e0_trace, {"pass": True, "protocol": "real_only"}),
                    ("E1", e1, e1_prediction, e1_trace, {**budget, "method": "E1"}),
                    ("E2", e2, e2_prediction, e2_trace, {**budget, "method": "E2"}),
                ]
            if not training_audit["pass"]:
                raise RuntimeError(f"hard-stop: final training audit failed: {training_audit}")
            for method, metrics, prediction, trace, method_budget in method_rows:
                rows.append(
                    _row(
                        method=method,
                        k=k,
                        seed=seed,
                        split=split,
                        metrics=metrics,
                        leakage=leakage,
                        public_test=public_test,
                        budget=method_budget,
                        files=files,
                        prediction_trace=prediction,
                        training_trace=trace,
                        training_audit=training_audit,
                        calibration_audit=calibration_audit,
                        v2_config=v2_generator.config,
                    )
                )
    (out / "raw_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "split_manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    summary = aggregate_public_results(
        rows,
        dataset="Paderborn_Bearing_DataCenter_T0_v2",
        experiment="Paderborn_T0_v2_E4_final_holdout",
    )
    summary.update(
        {
            "freeze_hash": freeze_hash,
            "train_condition": TRAIN_CONDITION,
            "test_condition": TEST_CONDITION,
            "test_bearings": list(TEST_BEARINGS),
            "measurement_indices": list(measurements),
            "all_calibration_audits_pass": all(row["calibration_audit"]["pass"] for row in rows),
            "dataset_description": "New Paderborn bearing- and condition-disjoint holdout; train/validation use N15_M07_F10 and final test uses untouched N09_M07_F10 measured vibration_1.",
            "license": "CC BY-NC 4.0; citation required; no commercial redistribution",
            "dataset_files": [item.__dict__ for item in files],
        }
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "protocol_freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    return {"rows": rows, "summary": summary}
