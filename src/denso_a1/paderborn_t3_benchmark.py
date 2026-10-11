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
from denso_a1.eval.audits import leakage_audit
from denso_a1.eval.evaluator import evaluate_with_trace
from denso_a1.failure_analysis import _compare
from denso_a1.generators.augment import t1_augment
from denso_a1.generators.physics import (
    T0V2Config,
    T0V2Generator,
    calibrate_t0v2_from_training_faults,
)
from denso_a1.generators.t3_fault_preserving import (
    T3Config,
    apply_policy,
)
from denso_a1.public_benchmark import _choose_parents, _concat, _training_trace
from denso_a1.schema import SampleBatch
from denso_a1.t2_vae import ConditionalVAE, VAEConfig

TRAIN_CONDITIONS = ("N15_M07_F10", "N15_M07_F04")
FINAL_TEST_CONDITION = "N15_M01_F10"
TRAIN_HEALTHY = ("K002", "K003")
TRAIN_FAULTS = ("KA04", "KI04")
VAL_BEARINGS = ("K004", "KA16", "KI14")
FINAL_TEST_BEARINGS = ("K001", "KA15", "KI16")
MEASUREMENTS = (1, 2, 3, 4, 5)
GENERATED_PER_SEED = 32
SEEDS = (0, 1, 2, 3, 4)

POLICIES: dict[str, tuple[str, ...]] = {
    "amplitude": ("amplitude",),
    "shift": ("shift",),
    "noise": ("noise",),
    "phase": ("phase",),
    "spectral": ("spectral",),
    "time_scale": ("time_scale",),
    "envelope": ("envelope",),
    "amplitude_shift": ("amplitude", "shift"),
    "amplitude_noise": ("amplitude", "noise"),
    "amplitude_phase": ("amplitude", "phase"),
    "amplitude_envelope": ("amplitude", "envelope"),
    "conservative_combo": ("amplitude", "shift", "noise", "phase", "spectral", "envelope"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_corpus(raw_root: str | Path, measurements: tuple[int, ...]) -> tuple[SampleBatch, tuple[Any, ...]]:
    train_val = TRAIN_HEALTHY + TRAIN_FAULTS + VAL_BEARINGS
    datasets = [
        load_paderborn(raw_root, bearing_ids=train_val, condition_id=condition, measurement_indices=measurements)
        for condition in TRAIN_CONDITIONS
    ]
    datasets.append(
        load_paderborn(raw_root, bearing_ids=FINAL_TEST_BEARINGS, condition_id=FINAL_TEST_CONDITION, measurement_indices=measurements)
    )
    return (
        SampleBatch(
            np.concatenate([dataset.batch.signals for dataset in datasets], axis=0),
            [item for dataset in datasets for item in dataset.batch.metadata],
        ),
        tuple(item for dataset in datasets for item in dataset.files),
    )


def _split(batch: SampleBatch, k: int) -> ProtocolSplit:
    selected = TRAIN_FAULTS[:k]
    group = lambda bearing: f"paderborn-bearing-{bearing}"
    train_groups = {group(bearing) for bearing in TRAIN_HEALTHY + selected}
    val_groups = {group(bearing) for bearing in VAL_BEARINGS}
    test_groups = {group(bearing) for bearing in FINAL_TEST_BEARINGS}
    train = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in train_groups and m.condition_id in TRAIN_CONDITIONS], dtype=int)
    val = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in val_groups and m.condition_id in TRAIN_CONDITIONS], dtype=int)
    test = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in test_groups and m.condition_id == FINAL_TEST_CONDITION], dtype=int)
    if not train.size or not val.size or not test.size:
        raise ValueError(f"empty T3 split for k={k}")
    if {batch.metadata[int(i)].group_id for i in train} & {batch.metadata[int(i)].group_id for i in val}:
        raise RuntimeError("T3 train/validation group overlap")
    if {batch.metadata[int(i)].condition_id for i in test} != {FINAL_TEST_CONDITION}:
        raise RuntimeError("T3 final test condition is not frozen")
    if {batch.metadata[int(i)].condition_id for i in np.concatenate([train, val])} != set(TRAIN_CONDITIONS):
        raise RuntimeError("T3 train/validation conditions are not frozen")
    return ProtocolSplit(
        train=train,
        val=val,
        test=test,
        selected_fault_groups=tuple(group(bearing) for bearing in selected),
        train_groups=tuple(sorted(train_groups)),
        val_groups=tuple(sorted(val_groups)),
        test_groups=tuple(sorted(test_groups)),
        split_mode="t3_new_bearing_and_condition_disjoint_holdout",
    )


def _nearest_neighbor(real: SampleBatch, generated: SampleBatch) -> dict[str, Any]:
    if not len(real.signals) or not len(generated.signals):
        return {"pass": False, "reason": "empty population"}
    scale = np.std(real.signals, axis=0) + 1e-8
    real_x = real.signals[:, ::16] / scale[::16]
    generated_x = generated.signals[:, ::16] / scale[::16]
    distances = np.sqrt(((generated_x[:, None, :] - real_x[None, :, :]) ** 2).mean(axis=2))
    gen_nn = distances.min(axis=1)
    if len(real_x) > 1:
        real_dist = np.sqrt(((real_x[:, None, :] - real_x[None, :, :]) ** 2).mean(axis=2))
        real_dist[real_dist == 0] = np.inf
        real_loo = real_dist.min(axis=1)
    else:
        real_loo = np.ones(1)
    generated_hashes = {hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest() for row in generated.signals}
    real_hashes = {hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest() for row in real.signals}
    exact = sorted(generated_hashes & real_hashes)
    ratio = float(np.median(gen_nn) / (np.median(real_loo) + 1e-12))
    return {
        "generated_to_real_nn_median": float(np.median(gen_nn)),
        "real_loo_nn_median": float(np.median(real_loo)),
        "median_ratio": ratio,
        "exact_signal_hash_overlap": exact,
        "pass": not exact and ratio >= 0.25,
    }


def _fidelity(real: SampleBatch, generated: SampleBatch, *, seed: int, partition: str) -> dict[str, Any]:
    comparison = _compare(real, generated, fs_hz=64_000.0, seed=seed)
    real_anchor = comparison["features"]["envelope_peak_hz"]["real_mean"]
    generated_anchor = comparison["features"]["envelope_peak_hz"]["generated_mean"]
    anchor_drift = abs(real_anchor - generated_anchor)
    nn = _nearest_neighbor(real, generated)
    c2st = comparison["c2st"]["roc_auc"]
    return {
        "partition": partition,
        "comparison": comparison,
        "anchor_drift_hz": float(anchor_drift),
        "nearest_neighbor": nn,
        "fidelity_gate_pass": bool(nn["pass"] and np.isfinite(c2st) and c2st <= 0.95 and anchor_drift <= 50.0),
    }


def _development_score(case: dict[str, Any]) -> tuple[float, bool]:
    comparison = case["comparison"]
    c2st = float(comparison["c2st"]["roc_auc"])
    distance = comparison["spectral_distance"]
    nn = case["nearest_neighbor"]
    passed = bool(
        np.isfinite(c2st)
        and c2st <= 0.95
        and distance["js_divergence"] <= 0.25
        and distance["cosine_similarity"] >= 0.65
        and case["anchor_drift_hz"] <= 50.0
        and nn["pass"]
    )
    score = (
        max(0.0, c2st - 0.5)
        + distance["js_divergence"]
        + max(0.0, 1.0 - distance["cosine_similarity"])
        + case["anchor_drift_hz"] / 1000.0
        + max(0.0, 0.25 - nn["median_ratio"])
    )
    return float(score), passed


def run_t3_development(raw_root: str | Path, out_dir: str | Path, *, seeds: int = 5, measurements: tuple[int, ...] = MEASUREMENTS) -> dict[str, Any]:
    """Evaluate every transform on train/validation fault groups only."""
    if seeds < 5:
        raise ValueError("T3 development gate requires at least five seeds")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    batch, _ = _load_corpus(raw_root, measurements)
    cfg = T3Config()
    cases: list[dict[str, Any]] = []
    for seed in range(seeds):
        for k in (1, 2):
            split = _split(batch, k)
            processed = SignalPreprocessor().fit(batch.subset(split.train)).transform(batch)
            normal_indices = np.asarray([i for i in split.train if batch.metadata[int(i)].label_binary == 0], dtype=int)
            train_fault = processed.subset(np.flatnonzero(processed.labels == 1)[0:0])
            train_fault = processed.subset([i for i in range(len(processed.metadata)) if i in set(split.train) and processed.metadata[i].label_binary == 1])
            val_fault = processed.subset([i for i in range(len(processed.metadata)) if i in set(split.val) and processed.metadata[i].label_binary == 1])
            normal_batch = processed.subset(normal_indices)
            parent_indices = _choose_parents(np.arange(len(train_fault.signals)), GENERATED_PER_SEED, 30_000 + seed)
            for name, policy in POLICIES.items():
                generated = apply_policy(train_fault, normal_batch, parent_indices, policy=policy, seed=40_000 + seed, config=cfg)
                fidelity = _fidelity(val_fault, generated, seed=50_000 + seed, partition="validation_fault")
                score, passed = _development_score(fidelity)
                cases.append({"seed": seed, "k": k, "policy": name, "operators": list(policy), "complexity": len(policy), "score": score, "development_gate_pass": passed, **fidelity})
    aggregate: dict[str, dict[str, Any]] = {}
    for name, policy in POLICIES.items():
        entries = [case for case in cases if case["policy"] == name]
        aggregate[name] = {
            "n": len(entries),
            "mean_score": float(np.mean([case["score"] for case in entries])),
            "pass_rate": float(np.mean([case["development_gate_pass"] for case in entries])),
            "all_cases_pass": all(case["development_gate_pass"] for case in entries),
            "mean_c2st": float(np.mean([case["comparison"]["c2st"]["roc_auc"] for case in entries])),
            "mean_js": float(np.mean([case["comparison"]["spectral_distance"]["js_divergence"] for case in entries])),
            "mean_cosine": float(np.mean([case["comparison"]["spectral_distance"]["cosine_similarity"] for case in entries])),
            "mean_anchor_drift_hz": float(np.mean([case["anchor_drift_hz"] for case in entries])),
            "mean_nn_ratio": float(np.mean([case["nearest_neighbor"]["median_ratio"] for case in entries])),
            "complexity": len(policy),
        }
    eligible = [name for name, item in aggregate.items() if item["all_cases_pass"]]
    if eligible:
        selected = min(eligible, key=lambda name: (aggregate[name]["complexity"], aggregate[name]["mean_score"], name))
    else:
        selected = min(aggregate, key=lambda name: (aggregate[name]["mean_score"], aggregate[name]["complexity"], name))
    selection = {
        "selected_policy": selected,
        "selected_operators": list(POLICIES[selected]),
        "selection_criterion": "minimum operator count among policies passing every train/validation fidelity gate; otherwise lowest frozen validation score",
        "development_gate_pass": bool(aggregate[selected]["all_cases_pass"]),
        "aggregate": aggregate,
        "config": cfg.__dict__,
        "seeds": list(range(seeds)),
        "holdout_excluded": {"condition": FINAL_TEST_CONDITION, "bearings": list(FINAL_TEST_BEARINGS)},
        "cases": cases,
    }
    (out / "raw_development.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    (out / "selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    lines = [
        "# T3 pre-final development report",
        "",
        "All candidates use only train/validation fault groups. The final holdout condition and bearing groups are excluded from this gate.",
        "",
        f"Selected policy: `{selected}` ({', '.join(POLICIES[selected])}). Development gate: {'PASS' if selection['development_gate_pass'] else 'FAIL; lowest-score policy retained for diagnostic final comparison'}.",
        "",
        "| policy | operators | complexity | pass rate | mean C2ST | mean PSD JS | mean PSD cosine | mean anchor drift (Hz) | mean NN ratio |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, item in aggregate.items():
        lines.append(f"| {name} | {', '.join(POLICIES[name])} | {item['complexity']} | {item['pass_rate']:.2f} | {item['mean_c2st']:.4f} | {item['mean_js']:.4f} | {item['mean_cosine']:.4f} | {item['mean_anchor_drift_hz']:.2f} | {item['mean_nn_ratio']:.3f} |")
    (out / "development_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return selection


def write_t3_protocol_freeze(selection_path: str | Path, target: str | Path) -> Path:
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    if selection["selected_policy"] not in POLICIES:
        raise ValueError("selection contains an unknown T3 policy")
    payload = {
        "protocol": "Paderborn_T3_fault_preserving_augmentation_v1",
        "dataset": "Paderborn_Bearing_DataCenter",
        "train_conditions": list(TRAIN_CONDITIONS),
        "final_test_condition": FINAL_TEST_CONDITION,
        "train_healthy_bearings": list(TRAIN_HEALTHY),
        "train_fault_bearings_by_k": {"0": [], "1": [TRAIN_FAULTS[0]], "2": list(TRAIN_FAULTS)},
        "validation_bearings": list(VAL_BEARINGS),
        "final_test_bearings": list(FINAL_TEST_BEARINGS),
        "measurement_indices": list(MEASUREMENTS),
        "window_size": 4096,
        "step": 4096,
        "fs_hz": 64000.0,
        "methods": {"E0": "real_only", "E1": "existing_t1_generic_augmentation", "E2": "frozen_t0_v2", "E3": "frozen_conditional_vae", "E4": "frozen_t3_fault_preserving_augmentation"},
        "selected_policy": selection["selected_policy"],
        "selected_operators": selection["selected_operators"],
        "development_gate_pass": selection["development_gate_pass"],
        "t3_config": selection["config"],
        "vae_config": VAEConfig().__dict__,
        "seeds": {"paired_seeds": list(SEEDS), "split_seed": 0},
        "budget": {"generated_per_seed": GENERATED_PER_SEED, "all_generated_arms_equal": True},
        "selection_criterion": selection["selection_criterion"],
        "fidelity_gate": {"c2st_roc_auc_max": 0.95, "psd_js_max": 0.25, "psd_cosine_min": 0.65, "anchor_drift_hz_max": 50.0, "nn_ratio_min": 0.25, "exact_hash_overlap_allowed": False},
        "k0_rule": "no measured fault information; do not fabricate T3 result",
        "final_holdout_rule": "new measured-real bearing/condition-disjoint holdout; no final-test tuning",
        "closed_branches": ["T0", "T0-v2", "conditional-VAE-T2"],
        "forbidden": ["GAN", "diffusion", "final-test parameter search", "additional raw-data augmentation after E4 failure"],
    }
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target_path


def _evaluate(train: SampleBatch, test: SampleBatch, seed: int, one_class: bool = False) -> tuple[dict[str, float], dict[str, Any]]:
    return evaluate_with_trace(train, test, fs_hz=64_000.0, seed=seed, one_class=one_class)


def _row(method: str, k: int, seed: int, split: ProtocolSplit, metrics: dict[str, float], prediction: dict[str, Any], training: dict[str, Any], budget: dict[str, Any], audits: dict[str, Any], files: tuple[Any, ...], freeze_hash: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "run_id": f"PADERBORN-T3-{method}-k{k}-seed{seed}",
        "experiment": "Paderborn_T3_fault_preserving_augmentation_final_holdout",
        "dataset": "Paderborn_Bearing_DataCenter",
        "method": method,
        "k_fault_groups": k,
        "split_mode": split.split_mode,
        "train_conditions": list(TRAIN_CONDITIONS),
        "final_test_condition": FINAL_TEST_CONDITION,
        "split_seed": 0,
        "subset_seed": 10_000 + seed,
        "generator_seed": 20_000 + seed,
        "model_seed": seed,
        "selected_fault_groups": list(split.selected_fault_groups),
        "train_group_ids": list(split.train_groups),
        "val_group_ids": list(split.val_groups),
        "test_group_ids": list(split.test_groups),
        "metrics": metrics,
        "prediction_trace": prediction,
        "training_trace": training,
        "budget_audit": budget,
        "leakage_audit": audits["leakage_audit"],
        "public_real_test_audit": audits["public_real_test_audit"],
        "provenance_audit": audits.get("provenance_audit", {"pass": True}),
        "fidelity_cases": audits.get("fidelity_cases", []),
        "fidelity_gate_pass": audits.get("fidelity_gate_pass", True),
        "freeze_hash": freeze_hash,
        "raw_file_checksums": {f"{item.bearing_id}/{Path(item.path).name}": item.sha256 for item in files},
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


def _aggregate(rows: list[dict[str, Any]], freeze_hash: str, files: tuple[Any, ...]) -> dict[str, Any]:
    summary: dict[str, Any] = {"dataset": "Paderborn_Bearing_DataCenter", "experiment": "Paderborn_T3_fault_preserving_augmentation_final_holdout", "primary_metric": "pr_auc", "freeze_hash": freeze_hash, "groups": {}, "method_coverage": {}, "new_holdout": {"condition": FINAL_TEST_CONDITION, "bearings": list(FINAL_TEST_BEARINGS), "measured_public_real_only": True}, "dataset_files": [item.__dict__ for item in files]}
    for k in (0, 1, 2):
        summary["method_coverage"][str(k)] = sorted({row["method"] for row in rows if row["k_fault_groups"] == k})
    for key in sorted({f"k={row['k_fault_groups']}:{row['method']}" for row in rows}):
        values = [row for row in rows if f"k={row['k_fault_groups']}:{row['method']}" == key]
        summary["groups"][key] = {"n": len(values), "metrics": {metric: {"mean": float(np.mean([row["metrics"][metric] for row in values])), "ci95": _bootstrap(np.asarray([row["metrics"][metric] for row in values]), 42)} for metric in ("pr_auc", "f1")}}
    summary.update({
        "all_public_real_test_audits_pass": all(row["public_real_test_audit"]["pass"] for row in rows),
        "all_leakage_audits_pass": all(row["leakage_audit"]["pass"] for row in rows),
        "all_budget_audits_pass": all(row["budget_audit"].get("pass", False) for row in rows),
        "all_provenance_audits_pass": all(row["provenance_audit"].get("pass", False) for row in rows),
        "all_fidelity_gates_pass": all(row.get("fidelity_gate_pass", True) for row in rows),
    })
    for comparator in ("E0", "E1", "E2", "E3"):
        for k in (1, 2):
            e4 = np.asarray([row["metrics"]["pr_auc"] for row in rows if row["method"] == "E4" and row["k_fault_groups"] == k])
            base = np.asarray([row["metrics"]["pr_auc"] for row in rows if row["method"] == comparator and row["k_fault_groups"] == k])
            if len(e4) == len(base) and len(e4):
                delta = e4 - base
                summary.setdefault("paired_deltas", {})[f"k={k}:E4-{comparator}"] = {"n": len(delta), "mean_delta": float(np.mean(delta)), "ci95": _bootstrap(delta, 100 + k)}
    return summary


def _write_reports(out: Path, summary: dict[str, Any], selection: dict[str, Any]) -> None:
    dev_lines = [
        "# T3 pre-final development report",
        "",
        "Candidate selection uses only train/validation fault groups; the final holdout was excluded.",
        "",
        f"Selected policy: `{selection['selected_policy']}`; development gate: {'PASS' if selection['development_gate_pass'] else 'FAIL (diagnostic lowest-score policy retained)' }.",
        "",
        "See `reports/t3_development/raw_development.json` and `selection.json` for every operator and combination.",
    ]
    (out.parent / "t3_development_report.md").write_text("\n".join(dev_lines) + "\n", encoding="utf-8")
    fidelity_lines = [
        "# T3 fidelity report",
        "",
        "Fidelity is measured on train/validation fault populations only; final-test labels and signals are not used for this diagnostic.",
        "",
        "The frozen gate requires C2ST ROC-AUC <= 0.95, PSD JS <= 0.25, PSD cosine >= 0.65, envelope-anchor drift <= 50 Hz, NN ratio >= 0.25 and no exact signal-hash overlap.",
        "",
        "See `reports/t3_benchmark/raw_metrics.json` for full feature vectors and per-sample provenance.",
        "",
        "| k | seed | partition | C2ST ROC-AUC | PSD JS | PSD cosine | anchor drift Hz | NN ratio | gate |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    raw_rows = json.loads((out / "raw_metrics.json").read_text(encoding="utf-8"))
    for row in raw_rows:
        if row["method"] != "E4":
            continue
        for case in row.get("fidelity_cases", []):
            comparison = case["comparison"]
            fidelity_lines.append(
                f"| {row['k_fault_groups']} | {row['model_seed']} | {case['partition']} | {comparison['c2st']['roc_auc']:.4f} | "
                f"{comparison['spectral_distance']['js_divergence']:.4f} | {comparison['spectral_distance']['cosine_similarity']:.4f} | "
                f"{case['anchor_drift_hz']:.2f} | {case['nearest_neighbor']['median_ratio']:.3f} | "
                f"{'PASS' if case['fidelity_gate_pass'] else 'REJECT'} |"
            )
    (out.parent / "t3_fidelity_report.md").write_text("\n".join(fidelity_lines) + "\n", encoding="utf-8")
    lines = [
        "# T3 fault-preserving augmentation benchmark report",
        "",
        "## Validity boundary",
        "",
        f"The new measured-real final holdout is `{FINAL_TEST_CONDITION}` on bearings `{', '.join(FINAL_TEST_BEARINGS)}`. Training/validation use `{', '.join(TRAIN_CONDITIONS)}` with bearing-disjoint groups. No final-test data was used for operator selection, VAE fitting, calibration or threshold selection.",
        "",
        f"Protocol SHA256: `{summary['freeze_hash']}`.",
        "",
        "Audit status: " + ", ".join(f"{name}={'PASS' if summary[key] else 'FAIL'}" for name, key in (("public-real", "all_public_real_test_audits_pass"), ("leakage", "all_leakage_audits_pass"), ("budget", "all_budget_audits_pass"), ("provenance", "all_provenance_audits_pass"), ("fidelity", "all_fidelity_gates_pass"))) + ".",
        "",
        "## Held-out metrics",
        "",
        "| setup | n | PR-AUC mean [95% CI] | F1 mean [95% CI] |",
        "|---|---:|---|---|",
    ]
    for key, item in sorted(summary["groups"].items()):
        pr, f1 = item["metrics"]["pr_auc"], item["metrics"]["f1"]
        lines.append(f"| {key} | {item['n']} | {pr['mean']:.4f} [{pr['ci95'][0]:.4f}, {pr['ci95'][1]:.4f}] | {f1['mean']:.4f} [{f1['ci95'][0]:.4f}, {f1['ci95'][1]:.4f}] |")
    lines += ["", "## Paired E4 deltas", "", "| comparison | n | PR-AUC delta [95% CI] |", "|---|---:|---|"]
    for key, delta in sorted(summary.get("paired_deltas", {}).items()):
        lines.append(f"| {key} | {delta['n']} | {delta['mean_delta']:.4f} [{delta['ci95'][0]:.4f}, {delta['ci95'][1]:.4f}] |")
    lines += ["", "## Decision", "", "E4 PASS requires held-out improvement over E0/E1 and no severe fidelity failure. k=0 intentionally has no E4 result because no measured fault information is available; no synthetic T3 result is fabricated."]
    if not summary["all_fidelity_gates_pass"] or any(delta["mean_delta"] <= 0 for key, delta in summary.get("paired_deltas", {}).items() if key.endswith(("E4-E0", "E4-E1"))):
        lines += ["", "Decision: FAIL. T3 does not establish a safe, useful augmentation improvement. Stop raw-data augmentation research; do not try GAN, diffusion, or further generative architectures merely to search for a positive result."]
        synthesis = """# Final negative-result synthesis\n\nThe DENSO-A1 raw-waveform augmentation objective is closed after four negative branches:\n\n- T0 physics synthesis: real-vs-generated C2ST ROC-AUC was 1.0 with large PSD/envelope and higher-order-statistic mismatches.\n- T0-v2: the frozen Paderborn final holdout produced negative E2−E0 PR-AUC deltas at k=0,1,2.\n- Conditional-VAE T2: C2ST ROC-AUC was 1.0 on train/validation populations and held-out E3−E0 PR-AUC was negative.\n- T3 fault-preserving augmentation: the frozen operator policy did not satisfy the combined fidelity/utility gate on the new measured-real holdout.\n\nAll reported branches used leakage and budget controls; this is a negative scientific result, not evidence that more expressive generators should be searched. The recommended next step is to change the project objective toward measured-data diagnosis, representation learning, or uncertainty/calibration rather than continuing raw-data synthesis tuning.\n"""
        (out.parent / "final_negative_result_synthesis.md").write_text(synthesis, encoding="utf-8")
    (out.parent / "t3_benchmark_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_paderborn_t3_benchmark(raw_root: str | Path, out_dir: str | Path, *, freeze_path: str | Path, seeds: int = 5, measurements: tuple[int, ...] = MEASUREMENTS) -> dict[str, Any]:
    freeze = json.loads(Path(freeze_path).read_text(encoding="utf-8"))
    if seeds < 5:
        raise ValueError("T3 final evaluation requires at least five paired seeds")
    if freeze["protocol"] != "Paderborn_T3_fault_preserving_augmentation_v1":
        raise RuntimeError("wrong T3 protocol freeze")
    freeze_hash = _sha256(Path(freeze_path))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    batch, files = _load_corpus(raw_root, measurements)
    selection = {"selected_policy": freeze["selected_policy"], "selected_operators": freeze["selected_operators"], "development_gate_pass": freeze["development_gate_pass"]}
    policy = tuple(freeze["selected_operators"])
    t3_config = T3Config(**freeze["t3_config"])
    rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for seed in range(seeds):
        for k in (0, 1, 2):
            split = _split(batch, k)
            raw_train, raw_test = batch.subset(split.train), batch.subset(split.test)
            public_test = public_real_test_audit(raw_test)
            processed = SignalPreprocessor().fit(raw_train).transform(batch)
            train, val, test = processed.subset(split.train), processed.subset(split.val), processed.subset(split.test)
            leakage = leakage_audit(train, val, test)
            if not public_test["pass"] or not leakage["pass"]:
                raise RuntimeError(f"T3 hard-stop audit failure: public={public_test}, leakage={leakage}")
            manifests.append({"freeze_hash": freeze_hash, "seed": seed, "k": k, "train_groups": list(split.train_groups), "val_groups": list(split.val_groups), "test_groups": list(split.test_groups), "test_condition": FINAL_TEST_CONDITION, "test_source_types": public_test["source_types"]})
            normal_indices = np.asarray([i for i in split.train if batch.metadata[int(i)].label_binary == 0], dtype=int)
            fault_indices = np.asarray([i for i in split.train if batch.metadata[int(i)].label_binary == 1], dtype=int)
            normal_batch = processed.subset(normal_indices)
            train_fault = processed.subset([i for i in split.train if batch.metadata[int(i)].label_binary == 1])
            val_fault = processed.subset([i for i in split.val if batch.metadata[int(i)].label_binary == 1])
            e0, e0_pred = _evaluate(train, test, seed, one_class=k == 0)
            if k == 0:
                m = min(len(normal_indices), GENERATED_PER_SEED)
                rows.append(_row("E0", k, seed, split, e0, e0_pred, _training_trace(train), {"pass": True, "protocol": "real_only"}, {"leakage_audit": leakage, "public_real_test_audit": public_test}, files, freeze_hash))
                t0 = T0V2Generator(T0V2Config()).generate_from_parents(processed, _choose_parents(normal_indices, m, 20_000 + seed), seed=20_000 + seed, split_seed=0)
                e2_train = _concat(train, t0)
                e2, e2_pred = _evaluate(e2_train, test, seed)
                rows.append(_row("E2", k, seed, split, e2, e2_pred, _training_trace(e2_train), {"pass": True, "protocol": "frozen_t0_v2_k0", "generated_count": m}, {"leakage_audit": leakage, "public_real_test_audit": public_test}, files, freeze_hash, {"t3_coverage": "not_applicable_no_measured_fault_information"}))
                continue
            m = min(len(fault_indices), GENERATED_PER_SEED)
            t1 = t1_augment(processed, _choose_parents(fault_indices, m, 30_000 + seed), seed=30_000 + seed)
            v2_cfg = calibrate_t0v2_from_training_faults(train.signals[train.labels == 1], fs_hz=64_000.0, base=T0V2Config())
            t0 = T0V2Generator(v2_cfg).generate_from_parents(processed, _choose_parents(normal_indices, m, 20_000 + seed), seed=20_000 + seed, split_seed=0)
            vae_cfg = VAEConfig(seed=seed)
            vae = ConditionalVAE(vae_cfg)
            history = vae.fit(train_fault, val_fault)
            t2 = vae.generate(n=m, condition_metadata=train_fault.metadata, source_groups=tuple(sorted({item.group_id for item in train_fault.metadata})), seed=40_000 + seed)
            t3 = apply_policy(train_fault, normal_batch, _choose_parents(np.arange(len(train_fault.signals)), m, 30_000 + seed), policy=policy, seed=60_000 + seed, config=t3_config)
            arms = {"E0": train, "E1": _concat(train, t1), "E2": _concat(train, t0), "E3": _concat(train, t2), "E4": _concat(train, t3)}
            budget = {"real_train_count": len(train.signals), "generated_count": m, "total_expected": len(train.signals) + m, "arm_totals": {name: len(arm.signals) for name, arm in arms.items()}, "pass": all(len(arm.signals) == len(train.signals) + m for name, arm in arms.items() if name != "E0")}
            t3_groups = set(split.train_groups)
            provenance = {"parent_ids_present": all(item.parent_ids for item in t3.metadata), "parent_groups_train_only": all(set(item.parent_group_ids).issubset(t3_groups) for item in t3.metadata), "parent_group_ids": sorted({group for item in t3.metadata for group in item.parent_group_ids})}
            provenance["pass"] = bool(provenance["parent_ids_present"] and provenance["parent_groups_train_only"])
            fidelity_cases = [_fidelity(train_fault, t3, seed=70_000 + seed, partition="train_fault"), _fidelity(val_fault, t3, seed=80_000 + seed, partition="validation_fault")]
            fidelity_pass = all(case["fidelity_gate_pass"] for case in fidelity_cases)
            for method, arm in arms.items():
                metrics, prediction = _evaluate(arm, test, seed)
                rows.append(_row(method, k, seed, split, metrics, prediction, _training_trace(arm), {**budget, "method": method}, {"leakage_audit": leakage, "public_real_test_audit": public_test, "provenance_audit": provenance, "fidelity_cases": fidelity_cases if method == "E4" else [], "fidelity_gate_pass": fidelity_pass if method == "E4" else True}, files, freeze_hash, {"t0_v2_config": v2_cfg.__dict__ if method == "E2" else None, "vae_config": vae_cfg.__dict__ if method == "E3" else None, "vae_history": history if method == "E3" else None, "t3_policy": list(policy) if method == "E4" else None, "t3_config": t3_config.__dict__ if method == "E4" else None}))
    summary = _aggregate(rows, freeze_hash, files)
    (out / "raw_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "split_manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    (out / "protocol_freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    (out / "run_audit.md").write_text(f"# T3 per-run audit\n\nRows: {len(rows)}. Training/prediction hashes and provenance are in `raw_metrics.json`.\n\nPublic-real, leakage, budget and provenance audits are recorded per run. Fidelity is a separate gate; E4 is rejected if it fails.\n", encoding="utf-8")
    _write_reports(out, summary, selection)
    return {"rows": rows, "summary": summary}
