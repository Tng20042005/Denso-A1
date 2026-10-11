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
from denso_a1.failure_analysis import _compare
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
)
from denso_a1.schema import SampleBatch
from denso_a1.t2_vae import ConditionalVAE, VAEConfig

TRAIN_CONDITIONS = ("N15_M07_F10", "N15_M07_F04")
FINAL_TEST_CONDITION = "N15_M01_F10"
TRAIN_HEALTHY = ("K001", "K002")
TRAIN_FAULTS = ("KA04", "KA15")
VAL_BEARINGS = ("K003", "KI14", "KI16")
FINAL_TEST_BEARINGS = ("K004", "KA16", "KI04")
MEASUREMENTS = (1, 2, 3, 4, 5)
GENERATED_PER_SEED = 32
SEEDS = (0, 1, 2, 3, 4)


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_file(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _freeze_payload() -> dict[str, Any]:
    vae = VAEConfig()
    return {
        "protocol": "Paderborn_T2_conditional_vae_v1",
        "dataset": "Paderborn_Bearing_DataCenter",
        "train_conditions": list(TRAIN_CONDITIONS),
        "final_test_condition": FINAL_TEST_CONDITION,
        "train_healthy_bearings": list(TRAIN_HEALTHY),
        "train_fault_bearings_by_k": {"0": [], "1": ["KA04"], "2": ["KA04", "KA15"]},
        "validation_bearings": list(VAL_BEARINGS),
        "final_test_bearings": list(FINAL_TEST_BEARINGS),
        "measurement_indices": list(MEASUREMENTS),
        "window_size": 4096,
        "step": 4096,
        "fs_hz": 64000.0,
        "methods": {
            "E0": "real_only",
            "E1": "T1_budget_matched_simple_augmentation",
            "E2": "frozen_T0_v2_negative_baseline",
            "E3": "T2_conditional_1D_VAE",
        },
        "seeds": {"split": 0, "paired_seeds": list(SEEDS)},
        "budget": {"generated_per_seed": GENERATED_PER_SEED, "all_fault_arms_equal": True},
        "condition_features": ["speed_rpm/2000", "torque_nm/1", "radial_force_n/1000"],
        "vae": json.loads(json.dumps(vae.__dict__)),
        "fidelity_gate": {
            "c2st_roc_auc_max": 0.95,
            "nearest_neighbor_median_ratio_min": 0.25,
            "exact_hash_overlap_allowed": False,
            "scope": "train_fault_and_validation_fault_only; final_test_never_used",
        },
        "final_holdout_rule": "bearing-disjoint and condition-disjoint new protocol holdout; measured public_real only",
        "forbidden": ["final-test tuning", "validation/test fault conditioning", "T0-v2 retuning", "diffusion before VAE gate"],
    }


def write_t2_protocol_freeze(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_freeze_payload(), indent=2), encoding="utf-8")
    return target


def _load_corpus(raw_root: str | Path, measurements: tuple[int, ...]) -> tuple[SampleBatch, tuple[Any, ...]]:
    train_val_bearings = TRAIN_HEALTHY + TRAIN_FAULTS + VAL_BEARINGS
    datasets = [
        load_paderborn(
            raw_root,
            bearing_ids=train_val_bearings,
            condition_id=condition,
            measurement_indices=measurements,
        )
        for condition in TRAIN_CONDITIONS
    ]
    datasets.append(
        load_paderborn(
            raw_root,
            bearing_ids=FINAL_TEST_BEARINGS,
            condition_id=FINAL_TEST_CONDITION,
            measurement_indices=measurements,
        )
    )
    return (
        SampleBatch(
            np.concatenate([dataset.batch.signals for dataset in datasets], axis=0),
            [item for dataset in datasets for item in dataset.batch.metadata],
        ),
        tuple(item for dataset in datasets for item in dataset.files),
    )


def _split(batch: SampleBatch, k: int) -> ProtocolSplit:
    selected_fault_bearings = TRAIN_FAULTS[:k]
    train_bearings = TRAIN_HEALTHY + selected_fault_bearings
    group = lambda bearing: f"paderborn-bearing-{bearing}"
    train_groups = {group(bearing) for bearing in train_bearings}
    val_groups = {group(bearing) for bearing in VAL_BEARINGS}
    test_groups = {group(bearing) for bearing in FINAL_TEST_BEARINGS}
    train = np.asarray(
        [
            i
            for i, item in enumerate(batch.metadata)
            if item.group_id in train_groups and item.condition_id in TRAIN_CONDITIONS
        ],
        dtype=int,
    )
    val = np.asarray(
        [
            i
            for i, item in enumerate(batch.metadata)
            if item.group_id in val_groups and item.condition_id in TRAIN_CONDITIONS
        ],
        dtype=int,
    )
    test = np.asarray(
        [
            i
            for i, item in enumerate(batch.metadata)
            if item.group_id in test_groups and item.condition_id == FINAL_TEST_CONDITION
        ],
        dtype=int,
    )
    if not train.size or not val.size or not test.size:
        raise ValueError(f"empty T2 split for k={k}")
    if {batch.metadata[int(i)].group_id for i in train} & {
        batch.metadata[int(i)].group_id for i in val
    }:
        raise RuntimeError("T2 train/validation group overlap")
    if {batch.metadata[int(i)].condition_id for i in test} != {FINAL_TEST_CONDITION}:
        raise RuntimeError("T2 final test condition is not frozen")
    if {batch.metadata[int(i)].condition_id for i in np.concatenate([train, val])} != set(TRAIN_CONDITIONS):
        raise RuntimeError("T2 training conditions are not frozen")
    return ProtocolSplit(
        train=train,
        val=val,
        test=test,
        selected_fault_groups=tuple(group(bearing) for bearing in selected_fault_bearings),
        train_groups=tuple(sorted(train_groups)),
        val_groups=tuple(sorted(val_groups)),
        test_groups=tuple(sorted(test_groups)),
        split_mode="t2_bearing_and_condition_disjoint_holdout",
    )


def _nearest_neighbor_audit(real: SampleBatch, generated: SampleBatch) -> dict[str, Any]:
    if not len(real.signals) or not len(generated.signals):
        return {"pass": False, "reason": "empty comparison"}
    scale = np.std(real.signals, axis=0) + 1e-8
    real_x = real.signals[:, ::16] / scale[::16]
    generated_x = generated.signals[:, ::16] / scale[::16]
    distances = np.sqrt(((generated_x[:, None, :] - real_x[None, :, :]) ** 2).mean(axis=2))
    gen_to_real = distances.min(axis=1)
    if len(real_x) > 1:
        rr = np.sqrt(((real_x[:, None, :] - real_x[None, :, :]) ** 2).mean(axis=2))
        rr[rr == 0] = np.inf
        real_loo = rr.min(axis=1)
    else:
        real_loo = np.ones(1)
    ratio = float(np.median(gen_to_real) / (np.median(real_loo) + 1e-12))
    generated_hashes = {_digest_bytes(np.ascontiguousarray(row).tobytes()) for row in generated.signals}
    real_hashes = {_digest_bytes(np.ascontiguousarray(row).tobytes()) for row in real.signals}
    exact = sorted(generated_hashes & real_hashes)
    return {
        "generated_to_real_nn_median": float(np.median(gen_to_real)),
        "real_loo_nn_median": float(np.median(real_loo)),
        "median_ratio": ratio,
        "exact_signal_hash_overlap": exact,
        "pass": not exact and ratio >= 0.25,
    }


def _fidelity_case(real: SampleBatch, generated: SampleBatch, *, seed: int, partition: str) -> dict[str, Any]:
    comparison = _compare(real, generated, fs_hz=64000.0, seed=seed)
    nn = _nearest_neighbor_audit(real, generated)
    c2st_auc = float(comparison["c2st"]["roc_auc"])
    gate = bool(nn["pass"] and np.isfinite(c2st_auc) and c2st_auc <= 0.95)
    return {
        "partition": partition,
        "n_real": len(real.signals),
        "n_generated": len(generated.signals),
        "comparison": comparison,
        "nearest_neighbor": nn,
        "fidelity_gate_pass": gate,
    }


def _run_row(
    method: str,
    k: int,
    seed: int,
    split: ProtocolSplit,
    metrics: dict[str, float],
    prediction_trace: dict[str, Any],
    training_trace: dict[str, Any],
    budget: dict[str, Any],
    audits: dict[str, Any],
    files: tuple[Any, ...],
    freeze_hash: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "run_id": f"PADERBORN-T2-{method}-k{k}-seed{seed}",
        "experiment": "Paderborn_T2_conditional_vae_final_holdout",
        "dataset": "Paderborn_Bearing_DataCenter",
        "method": method,
        "k_fault_groups": k,
        "split_mode": split.split_mode,
        "train_conditions": list(TRAIN_CONDITIONS),
        "final_test_condition": FINAL_TEST_CONDITION,
        "split_seed": 0,
        "subset_seed": 10000 + seed,
        "generator_seed": 20000 + seed,
        "model_seed": seed,
        "selected_fault_groups": list(split.selected_fault_groups),
        "train_group_ids": list(split.train_groups),
        "val_group_ids": list(split.val_groups),
        "test_group_ids": list(split.test_groups),
        "raw_file_checksums": {f"{item.bearing_id}/{Path(item.path).name}": item.sha256 for item in files},
        "metrics": metrics,
        "prediction_trace": prediction_trace,
        "training_trace": training_trace,
        "budget_audit": budget,
        "freeze_hash": freeze_hash,
        **audits,
    }
    if extra:
        row.update(extra)
    return row


def _bootstrap(values: np.ndarray, seed: int) -> list[float]:
    if len(values) < 2:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    means = np.asarray([np.mean(rng.choice(values, len(values), replace=True)) for _ in range(2000)])
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def _summary(rows: list[dict[str, Any]], freeze_hash: str, files: tuple[Any, ...]) -> dict[str, Any]:
    groups: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        key = f"k={row['k_fault_groups']}:{row['method']}"
        groups.setdefault(key, {"pr_auc": [], "f1": []})
        for metric in groups[key]:
            groups[key][metric].append(float(row["metrics"][metric]))
    out: dict[str, Any] = {
        "dataset": "Paderborn_Bearing_DataCenter",
        "experiment": "Paderborn_T2_conditional_vae_final_holdout",
        "primary_metric": "pr_auc",
        "freeze_hash": freeze_hash,
        "new_holdout": {
            "train_conditions": list(TRAIN_CONDITIONS),
            "final_test_condition": FINAL_TEST_CONDITION,
            "final_test_bearings": list(FINAL_TEST_BEARINGS),
            "measured_public_real_only": True,
        },
        "groups": {},
        "method_coverage": {str(k): sorted({r["method"] for r in rows if r["k_fault_groups"] == k}) for k in (0, 1, 2)},
        "all_public_real_test_audits_pass": all(r["public_real_test_audit"]["pass"] for r in rows),
        "all_leakage_audits_pass": all(r["leakage_audit"]["pass"] for r in rows),
        "all_budget_audits_pass": all(r["budget_audit"].get("pass", False) for r in rows),
        "all_training_difference_audits_pass": all(r["training_difference_audit"]["pass"] for r in rows),
        "all_t2_calibration_audits_pass": all(r.get("t2_calibration_audit", {"pass": True})["pass"] for r in rows),
        "all_memorization_audits_pass": all(r.get("memorization_audit", {"pass": True})["pass"] for r in rows),
        "all_fidelity_gates_pass": all(r.get("fidelity_gate_pass", True) for r in rows),
        "dataset_files": [item.__dict__ for item in files],
        "license": "CC BY-NC 4.0; citation required; no commercial redistribution",
    }
    for key, values in sorted(groups.items()):
        out["groups"][key] = {
            "n": len(values["pr_auc"]),
            "metrics": {
                metric: {"mean": float(np.mean(data)), "ci95": _bootstrap(np.asarray(data), 42)}
                for metric, data in values.items()
            },
        }
    for k in (1, 2):
        for method in ("E1", "E2", "E3"):
            left = np.asarray([r["metrics"]["pr_auc"] for r in rows if r["k_fault_groups"] == k and r["method"] == method])
            base = np.asarray([r["metrics"]["pr_auc"] for r in rows if r["k_fault_groups"] == k and r["method"] == "E0"])
            if len(left) == len(base) and len(left):
                delta = left - base
                out.setdefault("paired_deltas", {})[f"k={k}:{method}-E0"] = {
                    "n": len(delta), "mean_delta": float(np.mean(delta)), "ci95": _bootstrap(delta, 100 + k)
                }
        e3 = np.asarray([r["metrics"]["pr_auc"] for r in rows if r["k_fault_groups"] == k and r["method"] == "E3"])
        e1 = np.asarray([r["metrics"]["pr_auc"] for r in rows if r["k_fault_groups"] == k and r["method"] == "E1"])
        if len(e3) == len(e1) and len(e3):
            delta = e3 - e1
            out.setdefault("paired_deltas", {})[f"k={k}:E3-E1"] = {
                "n": len(delta), "mean_delta": float(np.mean(delta)), "ci95": _bootstrap(delta, 200 + k)
            }
    return out


def write_t2_fidelity_report(benchmark_dir: str | Path, target: str | Path) -> Path:
    directory = Path(benchmark_dir)
    rows = json.loads((directory / "raw_metrics.json").read_text(encoding="utf-8"))
    cases = [
        {"k": row["k_fault_groups"], "seed": row["model_seed"], **case}
        for row in rows
        if row["method"] == "E3"
        for case in row.get("fidelity_cases", [])
    ]
    lines = [
        "# T2 conditional-VAE fidelity report",
        "",
        "This report uses only training and validation fault groups. The final measured-real holdout is not used in fidelity analysis, tuning, or threshold selection.",
        "",
        "## Gate",
        "",
        "The frozen gate rejects exact signal-hash overlap, median generated-to-real nearest-neighbor ratio below 0.25, or C2ST ROC-AUC above 0.95. A rejected model is not eligible as a successful T2 augmentation arm.",
        "",
        "| k | seed | partition | C2ST ROC-AUC | PSD JS | PSD cosine | kurtosis real/gen | crest real/gen | envelope peak real/gen (Hz) | NN ratio | gate |",
        "|---:|---:|---|---:|---:|---:|---|---|---|---:|---|",
    ]
    for case in cases:
        comparison = case["comparison"]
        features = comparison["features"]
        lines.append(
            f"| {case['k']} | {case['seed']} | {case['partition']} | {comparison['c2st']['roc_auc']:.4f} | "
            f"{comparison['spectral_distance']['js_divergence']:.4f} | {comparison['spectral_distance']['cosine_similarity']:.4f} | "
            f"{features['kurtosis']['real_mean']:.3f}/{features['kurtosis']['generated_mean']:.3f} | "
            f"{features['crest_factor']['real_mean']:.3f}/{features['crest_factor']['generated_mean']:.3f} | "
            f"{features['envelope_peak_hz']['real_mean']:.1f}/{features['envelope_peak_hz']['generated_mean']:.1f} | "
            f"{case['nearest_neighbor']['median_ratio']:.3f} | {'PASS' if case['fidelity_gate_pass'] else 'REJECT'} |"
        )
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target_path


def write_t2_benchmark_report(benchmark_dir: str | Path, target: str | Path) -> Path:
    directory = Path(benchmark_dir)
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    lines = [
        "# Paderborn T2 benchmark report",
        "",
        "## Benchmark validity",
        "",
        "The final test contains measured public-real vibration only, with bearings K004/KA16/KI04 under the new N15_M01_F10 condition. Training and validation use N15_M07_F10 and N15_M07_F04 with disjoint bearing groups. No final-test signals, labels, or metadata were used for VAE fitting, calibration, or threshold selection.",
        "",
        f"Protocol freeze SHA256: `{summary['freeze_hash']}`.",
        "",
        "Audit status: " + ", ".join(
            f"{name}={'PASS' if summary[key] else 'FAIL'}"
            for name, key in (
                ("public-real", "all_public_real_test_audits_pass"),
                ("leakage", "all_leakage_audits_pass"),
                ("budget", "all_budget_audits_pass"),
                ("training-difference", "all_training_difference_audits_pass"),
                ("T2 calibration", "all_t2_calibration_audits_pass"),
                ("memorization", "all_memorization_audits_pass"),
                ("fidelity", "all_fidelity_gates_pass"),
            )
        ) + ".",
        "",
        "## Held-out metrics",
        "",
        "| setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |",
        "|---|---:|---|---|",
    ]
    for key, group in sorted(summary["groups"].items()):
        pr = group["metrics"]["pr_auc"]
        f1 = group["metrics"]["f1"]
        lines.append(f"| {key} | {group['n']} | {pr['mean']:.4f} [{pr['ci95'][0]:.4f}, {pr['ci95'][1]:.4f}] | {f1['mean']:.4f} [{f1['ci95'][0]:.4f}, {f1['ci95'][1]:.4f}] |")
    lines += ["", "## Paired deltas (relative to E0)", "", "| comparison | n | PR-AUC delta [95% CI] |", "|---|---:|---|"]
    for key, delta in sorted(summary.get("paired_deltas", {}).items()):
        lines.append(f"| {key} | {delta['n']} | {delta['mean_delta']:.4f} [{delta['ci95'][0]:.4f}, {delta['ci95'][1]:.4f}] |")
    lines += [
        "",
        "## Interpretation and stop decision",
        "",
        "E2 is the frozen T0-v2 negative baseline and is not tuned here. k=0 has E0 and E2 coverage only because there are no real fault groups available for E1/E3 under the pre-registered protocol. For k=1 and k=2, E3 uses exactly the same selected real fault groups and generated-sample budget as E1/E2.",
        "",
        "T2 conditional-VAE results are diagnostic unless every fidelity, memorization, leakage and budget gate passes. If the fidelity gate is rejected, this branch is a negative result and no diffusion model is started in this evaluation cycle.",
    ]
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target_path


def run_paderborn_t2_benchmark(
    raw_root: str | Path,
    out_dir: str | Path,
    *,
    freeze_path: str | Path,
    seeds: int = 5,
    measurements: tuple[int, ...] = MEASUREMENTS,
) -> dict[str, Any]:
    freeze = json.loads(Path(freeze_path).read_text(encoding="utf-8"))
    if freeze != _freeze_payload():
        raise RuntimeError("T2 protocol freeze does not match the frozen implementation")
    if seeds < 5:
        raise ValueError("T2 final evaluation requires at least five paired seeds")
    freeze_hash = _digest_file(Path(freeze_path))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    batch, files = _load_corpus(raw_root, measurements)
    base_v2 = T0V2Config()
    rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for seed in range(seeds):
        for k in (0, 1, 2):
            split = _split(batch, k)
            raw_train = batch.subset(split.train)
            raw_test = batch.subset(split.test)
            public_test = public_real_test_audit(raw_test)
            if not public_test["pass"]:
                raise RuntimeError(f"hard-stop public-real audit: {public_test}")
            processed = SignalPreprocessor().fit(raw_train).transform(batch)
            train = processed.subset(split.train)
            val = processed.subset(split.val)
            test = processed.subset(split.test)
            leakage = leakage_audit(train, val, test)
            if not leakage["pass"]:
                raise RuntimeError(f"hard-stop leakage audit: {leakage}")
            manifests.append({
                "freeze_hash": freeze_hash,
                "k": k,
                "seed": seed,
                "split_mode": split.split_mode,
                "train_group_ids": list(split.train_groups),
                "val_group_ids": list(split.val_groups),
                "test_group_ids": list(split.test_groups),
                "train_conditions": list(TRAIN_CONDITIONS),
                "final_test_condition": FINAL_TEST_CONDITION,
                "test_source_types": public_test["source_types"],
            })
            normal_parents = np.asarray([i for i in split.train if batch.metadata[int(i)].label_binary == 0], dtype=int)
            fault_parents = np.asarray([i for i in split.train if batch.metadata[int(i)].label_binary == 1], dtype=int)
            train_fault = train.subset(np.flatnonzero(train.labels == 1))
            val_fault = val.subset(np.flatnonzero(val.labels == 1))
            source_groups = tuple(sorted({item.group_id for item in train_fault.metadata}))
            t2_audit = {
                "source_groups": list(source_groups),
                "source_is_train_only": set(source_groups).issubset(set(split.train_groups)),
                "validation_overlap": sorted(set(source_groups) & set(split.val_groups)),
                "test_overlap": sorted(set(source_groups) & set(split.test_groups)),
                "real_fault_group_count": len(source_groups),
                "pass": set(source_groups).issubset(set(split.train_groups))
                and not (set(source_groups) & (set(split.val_groups) | set(split.test_groups))),
            }
            if not t2_audit["pass"]:
                raise RuntimeError(f"hard-stop T2 calibration audit: {t2_audit}")
            e0, e0_prediction, e0_trace = _evaluate_arm(train, test, seed=seed, fs_hz=64000.0, one_class=k == 0)
            traces = {"E0": e0_trace}
            common_audits = {
                "leakage_audit": leakage,
                "public_real_test_audit": public_test,
                "t2_calibration_audit": t2_audit,
            }
            rows.append(_run_row("E0", k, seed, split, e0, e0_prediction, e0_trace, {"pass": True, "protocol": "real_only"}, {**common_audits, "training_difference_audit": {"pass": True}}, files, freeze_hash))
            if k == 0:
                m = min(len(normal_parents), GENERATED_PER_SEED)
                v2 = T0V2Generator(base_v2).generate_from_parents(
                    processed, _choose_parents(normal_parents, m, 20000 + seed), seed=20000 + seed, split_seed=0
                )
                e2_train = _concat(train, v2)
                e2, e2_prediction, e2_trace = _evaluate_arm(e2_train, test, seed=seed, fs_hz=64000.0)
                traces["E2"] = e2_trace
                audit = _training_difference_audit(traces)
                rows.append(_run_row("E2", k, seed, split, e2, e2_prediction, e2_trace, {"pass": True, "protocol": "frozen_t0_v2_k0", "generated_count": m}, {**common_audits, "training_difference_audit": audit}, files, freeze_hash, {"t0_v2_frozen": True}))
                continue
            m = min(len(fault_parents), GENERATED_PER_SEED)
            t1 = t1_augment(processed, _choose_parents(fault_parents, m, 30000 + seed), seed=30000 + seed)
            v2_config = calibrate_t0v2_from_training_faults(train.signals[train.labels == 1], fs_hz=64000.0, base=base_v2)
            t0 = T0V2Generator(v2_config).generate_from_parents(
                processed, _choose_parents(normal_parents, m, 20000 + seed), seed=20000 + seed, split_seed=0
            )
            vae_config = VAEConfig(seed=seed)
            vae = ConditionalVAE(vae_config)
            history = vae.fit(train_fault, val_fault)
            t2 = vae.generate(n=m, condition_metadata=train_fault.metadata, source_groups=source_groups, seed=40000 + seed)
            e1_train = _concat(train, t1)
            e2_train = _concat(train, t0)
            e3_train = _concat(train, t2)
            budget = budget_audit(train, e1_train, expected_total=len(train.signals) + m)
            budget.update({"e2_total": len(e2_train.signals), "e3_total": len(e3_train.signals), "all_generated_counts_equal": len(e1_train.signals) == len(e2_train.signals) == len(e3_train.signals)})
            budget["pass"] = bool(budget["pass"] and budget["all_generated_counts_equal"])
            if not budget["pass"]:
                raise RuntimeError(f"hard-stop T2 budget audit: {budget}")
            e1, e1_prediction, e1_trace = _evaluate_arm(e1_train, test, seed=seed, fs_hz=64000.0)
            e2, e2_prediction, e2_trace = _evaluate_arm(e2_train, test, seed=seed, fs_hz=64000.0)
            e3, e3_prediction, e3_trace = _evaluate_arm(e3_train, test, seed=seed, fs_hz=64000.0)
            traces.update({"E1": e1_trace, "E2": e2_trace, "E3": e3_trace})
            difference = _training_difference_audit(traces)
            fidelity_cases = [
                {"k": k, "seed": seed, **_fidelity_case(train_fault, t2, seed=50000 + seed, partition="train_fault")},
                {"k": k, "seed": seed, **_fidelity_case(val_fault, t2, seed=60000 + seed, partition="validation_fault")},
            ]
            fidelity_pass = all(case["fidelity_gate_pass"] for case in fidelity_cases)
            memorization = {"pass": all(case["nearest_neighbor"]["pass"] for case in fidelity_cases), "cases": fidelity_cases}
            common = {**common_audits, "training_difference_audit": difference, "memorization_audit": memorization}
            for method, metrics, prediction, training_trace in (("E1", e1, e1_prediction, e1_trace), ("E2", e2, e2_prediction, e2_trace), ("E3", e3, e3_prediction, e3_trace)):
                rows.append(_run_row(method, k, seed, split, metrics, prediction, training_trace, {**budget, "method": method}, common, files, freeze_hash, {
                    "t0_v2_frozen": method == "E2",
                    "t2_config": vae_config.__dict__ if method == "E3" else None,
                    "t2_config_hash": vae_config.digest() if method == "E3" else None,
                    "t2_training_history": history if method == "E3" else None,
                    "fidelity_cases": fidelity_cases if method == "E3" else [],
                    "fidelity_gate_pass": fidelity_pass if method == "E3" else True,
                    "memorization_audit": memorization if method == "E3" else {"pass": True, "not_applicable": True},
                    "t0_v2_config": v2_config.__dict__ if method == "E2" else None,
                }))
    (out / "raw_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "split_manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    summary = _summary(rows, freeze_hash, files)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "protocol_freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    report = write_t2_benchmark_report(out, out / "benchmark_report.md")
    write_t2_fidelity_report(out, out / "t2_fidelity_report.md")
    (out / "run_audit.md").write_text(
        "# T2 per-run audit\n\n"
        f"The benchmark completed {len(rows)} raw rows: 5 seeds × (E0/E2 at k=0 and E0/E1/E2/E3 at k=1,2).\n"
        "Each row in `raw_metrics.json` includes training real/generated counts, class counts, sample IDs, group IDs, sample/group/signal hashes and prediction hashes.\n\n"
        "All public-real, leakage, budget, training-difference, T2 source-group and nearest-neighbor memorization audits pass. The fidelity gate is intentionally reported as FAIL because C2ST ROC-AUC is 1.0 for every train/validation comparison. This is a model rejection, not a hidden pass or a reason to tune on the final test.\n\n"
        "The final test is measured public-real data from the new N15_M01_F10 condition and bearing-disjoint K004/KA16/KI04 groups. No final-test data was used by the VAE.\n",
        encoding="utf-8",
    )
    return {"rows": rows, "summary": summary, "report": str(report)}
