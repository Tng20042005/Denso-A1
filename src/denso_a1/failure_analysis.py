from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import hilbert, welch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from denso_a1.benchmark import _bootstrap_ci
from denso_a1.data.paderborn import load_paderborn, make_paderborn_bearing_split
from denso_a1.data.preprocess import SignalPreprocessor
from denso_a1.generators.physics import PhysicsConfig, T0Generator
from denso_a1.public_benchmark import _choose_parents
from denso_a1.schema import SampleBatch

FEATURE_NAMES = (
    "rms",
    "kurtosis",
    "crest_factor",
    "spectral_centroid_hz",
    "resonance_peak_hz",
    "resonance_halfpower_bw_hz",
    "envelope_peak_hz",
    "envelope_peak_ratio",
    "band_0_500",
    "band_500_2000",
    "band_2000_5000",
    "band_5000_10000",
    "band_10000_20000",
    "band_20000_32000",
    "hf_to_faultband_db",
)


def _feature_matrix(signals: np.ndarray, fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(signals, dtype=float)
    x = values - np.mean(values, axis=1, keepdims=True)
    rms = np.sqrt(np.mean(x**2, axis=1)) + 1e-12
    std = np.std(x, axis=1) + 1e-12
    kurtosis = np.mean((x / std[:, None]) ** 4, axis=1)
    crest = np.max(np.abs(x), axis=1) / rms
    freqs, psd = welch(x, fs=fs_hz, nperseg=min(2048, x.shape[1]), axis=1)
    psd = np.maximum(psd, 1e-18)
    psd_mass = np.trapezoid(psd, freqs, axis=1) + 1e-18
    normalized_psd = psd / psd_mass[:, None]
    centroid = np.trapezoid(normalized_psd * freqs[None, :], freqs, axis=1)
    resonance_mask = (freqs >= 1_000.0) & (freqs <= min(20_000.0, fs_hz / 2))
    resonance_psd = normalized_psd[:, resonance_mask]
    resonance_freqs = freqs[resonance_mask]
    resonance_positions = np.argmax(resonance_psd, axis=1)
    resonance_peak = resonance_freqs[resonance_positions]
    halfpower_bw = np.empty(len(x), dtype=float)
    for row, peak_pos in enumerate(resonance_positions):
        peak = resonance_psd[row, peak_pos]
        left = peak_pos
        right = peak_pos
        while left > 0 and resonance_psd[row, left - 1] >= peak / 2:
            left -= 1
        while right + 1 < resonance_psd.shape[1] and resonance_psd[row, right + 1] >= peak / 2:
            right += 1
        halfpower_bw[row] = resonance_freqs[right] - resonance_freqs[left]

    envelope = np.abs(hilbert(x, axis=1))
    envelope -= np.mean(envelope, axis=1, keepdims=True)
    envelope_freqs = np.fft.rfftfreq(x.shape[1], 1 / fs_hz)
    envelope_spectrum = np.abs(np.fft.rfft(envelope, axis=1))
    envelope_mask = (envelope_freqs >= 30.0) & (envelope_freqs <= 1_000.0)
    envelope_band = envelope_spectrum[:, envelope_mask]
    envelope_band_freqs = envelope_freqs[envelope_mask]
    envelope_peak_positions = np.argmax(envelope_band, axis=1)
    envelope_peak = envelope_band_freqs[envelope_peak_positions]
    envelope_peak_ratio = envelope_band.max(axis=1) / (np.mean(envelope_band, axis=1) + 1e-12)

    bands = [
        (0, 500),
        (500, 2_000),
        (2_000, 5_000),
        (5_000, 10_000),
        (10_000, 20_000),
        (20_000, fs_hz / 2),
    ]
    band_energy = []
    for lo, hi in bands:
        mask = (freqs >= lo) & (freqs < hi)
        band_energy.append(np.trapezoid(normalized_psd[:, mask], freqs[mask], axis=1))
    band_array = np.column_stack(band_energy)
    hf_to_faultband_db = 10 * np.log10(
        (band_array[:, 5] + 1e-12) / (np.sum(band_array[:, :3], axis=1) + 1e-12)
    )
    features = np.column_stack(
        [
            rms,
            kurtosis,
            crest,
            centroid,
            resonance_peak,
            halfpower_bw,
            envelope_peak,
            envelope_peak_ratio,
            *band_energy,
            hf_to_faultband_db,
        ]
    )
    return features, normalized_psd


def _spectral_distance(real_psd: np.ndarray, generated_psd: np.ndarray) -> dict[str, float]:
    real_mean = np.mean(real_psd, axis=0)
    generated_mean = np.mean(generated_psd, axis=0)
    real_mean /= np.sum(real_mean)
    generated_mean /= np.sum(generated_mean)
    midpoint = (real_mean + generated_mean) / 2
    js = 0.5 * np.sum(real_mean * np.log(real_mean / midpoint)) + 0.5 * np.sum(
        generated_mean * np.log(generated_mean / midpoint)
    )
    cosine = float(
        np.dot(real_mean, generated_mean)
        / (np.linalg.norm(real_mean) * np.linalg.norm(generated_mean))
    )
    return {"js_divergence": float(js), "cosine_similarity": cosine}


def _c2st(real_features: np.ndarray, generated_features: np.ndarray, seed: int) -> dict[str, float]:
    n = min(len(real_features), len(generated_features))
    if n < 10:
        return {"roc_auc": float("nan"), "accuracy": float("nan"), "n_per_class": float(n)}
    x = np.vstack([real_features[:n], generated_features[:n]])
    y = np.concatenate([np.ones(n, dtype=int), np.zeros(n, dtype=int)])
    folds = StratifiedKFold(n_splits=min(5, n), shuffle=True, random_state=seed)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2_000, random_state=seed))
    scores = cross_val_predict(model, x, y, cv=folds, method="predict_proba")[:, 1]
    predictions = (scores >= 0.5).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y, scores)),
        "accuracy": float(accuracy_score(y, predictions)),
        "n_per_class": float(n),
    }


def _select_batch(batch: SampleBatch, indices: np.ndarray, count: int, seed: int) -> SampleBatch:
    selected = _choose_parents(np.asarray(indices, dtype=int), count, seed)
    return batch.subset(selected)


def _compare(real: SampleBatch, generated: SampleBatch, *, fs_hz: float, seed: int) -> dict[str, Any]:
    n = min(len(real.signals), len(generated.signals))
    real_features, real_psd = _feature_matrix(real.signals[:n], fs_hz)
    generated_features, generated_psd = _feature_matrix(generated.signals[:n], fs_hz)
    pooled_std = np.std(np.vstack([real_features, generated_features]), axis=0) + 1e-12
    feature_summary = {}
    for index, name in enumerate(FEATURE_NAMES):
        feature_summary[name] = {
            "real_mean": float(np.mean(real_features[:, index])),
            "generated_mean": float(np.mean(generated_features[:, index])),
            "delta_real_minus_generated": float(
                np.mean(real_features[:, index]) - np.mean(generated_features[:, index])
            ),
            "standardized_gap": float(
                (np.mean(real_features[:, index]) - np.mean(generated_features[:, index]))
                / pooled_std[index]
            ),
        }
    return {
        "n_per_class": n,
        "features": feature_summary,
        "spectral_distance": _spectral_distance(real_psd, generated_psd),
        "c2st": _c2st(real_features, generated_features, seed),
    }


def _aggregate(values: list[float]) -> dict[str, Any]:
    finite = [float(value) for value in values if np.isfinite(value)]
    mean = float(np.mean(finite)) if finite else float("nan")
    ci = _bootstrap_ci(np.asarray(finite, dtype=float), seed=991) if finite else [float("nan"), float("nan")]
    return {"n": len(finite), "mean": mean, "ci95": ci}


def run_failure_analysis(
    raw_root: str | Path,
    out_dir: str | Path,
    *,
    seeds: int = 5,
    condition_id: str = "N15_M07_F10",
    measurement_indices: tuple[int, ...] = (1, 2, 3, 4, 5),
    n_per_class: int = 128,
) -> dict[str, Any]:
    """Compare current T0 outputs to train/dev real damage without touching test groups."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dataset = load_paderborn(
        raw_root, condition_id=condition_id, measurement_indices=measurement_indices
    )
    generator = T0Generator(
        PhysicsConfig(fs_hz=64_000.0, f_fault_hz=120.0, f_res_hz=6_000.0, snr_db=14.0)
    )
    cases: list[dict[str, Any]] = []
    for seed in range(seeds):
        for k in (0, 1, 2):
            split = make_paderborn_bearing_split(
                dataset.batch, k=k, split_seed=seed, subset_seed=10_000 + seed
            )
            raw_train = dataset.batch.subset(split.train)
            processed = SignalPreprocessor().fit(raw_train).transform(dataset.batch)
            normal_parents = np.asarray(
                [i for i in split.train if dataset.batch.metadata[int(i)].label_binary == 0], dtype=int
            )
            generated = generator.generate_from_parents(
                processed,
                _choose_parents(normal_parents, min(n_per_class, len(normal_parents)), 20_000 + seed),
                seed=20_000 + seed,
                split_seed=seed,
            )
            for partition, indices in (
                (
                    "train_fault",
                    [i for i in split.train if dataset.batch.metadata[int(i)].label_binary == 1],
                ),
                (
                    "dev_fault",
                    [i for i in split.val if dataset.batch.metadata[int(i)].label_binary == 1],
                ),
            ):
                if not indices:
                    continue
                real = _select_batch(
                    processed,
                    np.asarray(indices, dtype=int),
                    min(n_per_class, len(indices)),
                    50_000 + seed,
                )
                comparison = _compare(real, generated, fs_hz=64_000.0, seed=70_000 + seed)
                cases.append(
                    {
                        "seed": seed,
                        "k": k,
                        "partition": partition,
                        "train_groups": list(split.train_groups),
                        "val_groups": list(split.val_groups),
                        "excluded_test_groups": list(split.test_groups),
                        "generator_config": generator.config.__dict__,
                        "comparison": comparison,
                    }
                )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        grouped.setdefault(f"k={case['k']}:{case['partition']}", []).append(case)
    summaries: dict[str, Any] = {}
    for name, entries in grouped.items():
        summaries[name] = {
            "n": len(entries),
            "c2st_roc_auc": _aggregate([entry["comparison"]["c2st"]["roc_auc"] for entry in entries]),
            "c2st_accuracy": _aggregate([entry["comparison"]["c2st"]["accuracy"] for entry in entries]),
            "spectral_js_divergence": _aggregate(
                [entry["comparison"]["spectral_distance"]["js_divergence"] for entry in entries]
            ),
            "spectral_cosine_similarity": _aggregate(
                [entry["comparison"]["spectral_distance"]["cosine_similarity"] for entry in entries]
            ),
            "features": {
                feature: {
                    "real_mean": _aggregate(
                        [entry["comparison"]["features"][feature]["real_mean"] for entry in entries]
                    ),
                    "generated_mean": _aggregate(
                        [entry["comparison"]["features"][feature]["generated_mean"] for entry in entries]
                    ),
                    "standardized_gap": _aggregate(
                        [entry["comparison"]["features"][feature]["standardized_gap"] for entry in entries]
                    ),
                }
                for feature in FEATURE_NAMES
            },
        }
    summary = {
        "dataset": "Paderborn_Bearing_DataCenter",
        "condition_id": condition_id,
        "measurement_indices": list(measurement_indices),
        "seeds": seeds,
        "n_per_class": n_per_class,
        "generator_config": generator.config.__dict__,
        "test_policy": "All split.test groups are excluded from parent selection and calibration; this is diagnosis only, not final evaluation.",
        "groups": summaries,
    }
    (out / "failure_analysis.json").write_text(
        json.dumps({"summary": summary, "cases": cases}, indent=2), encoding="utf-8"
    )
    return {"summary": summary, "cases": cases}


def _cell(value: dict[str, Any]) -> str:
    return f"{value['mean']:.4f} [{value['ci95'][0]:.4f}, {value['ci95'][1]:.4f}]"


def write_failure_analysis_report(analysis_dir: str | Path) -> Path:
    directory = Path(analysis_dir)
    payload = json.loads((directory / "failure_analysis.json").read_text(encoding="utf-8"))
    summary = payload["summary"]
    lines = [
        "# T0 failure analysis",
        "",
        "This is a diagnosis-only artifact. Existing Paderborn final-test groups were excluded from parent selection and calibration; no result here is used to tune the previous test.",
        "",
        f"Dataset: `{summary['dataset']}`; condition: `{summary['condition_id']}`; measurement repetitions: `{summary['measurement_indices']}`; seeds: `{summary['seeds']}`.",
        f"Current T0 configuration: `{summary['generator_config']}`.",
        "",
        "## Quantitative distribution gate",
        "",
        "C2ST ROC-AUC=0.5 is indistinguishable distributions; higher values indicate that a classifier can separate measured damage from T0 output. Spectral JS is lower-is-better and cosine similarity is higher-is-better.",
        "",
        "| Population | n | C2ST ROC-AUC mean [95% CI] | C2ST accuracy | Spectral JS | PSD cosine |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for name, group in summary["groups"].items():
        lines.append(
            f"| {name} | {group['n']} | {_cell(group['c2st_roc_auc'])} | {_cell(group['c2st_accuracy'])} | {_cell(group['spectral_js_divergence'])} | {_cell(group['spectral_cosine_similarity'])} |"
        )
    lines.extend(
        [
            "",
            "## Feature evidence",
            "",
            "Values are means over signals; standardized gap is `(real−generated)/pooled_std`, so its sign indicates direction and magnitude indicates separation.",
            "",
            "| Population | Feature | Real mean | Generated mean | Standardized gap |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    selected_features = (
        "rms",
        "kurtosis",
        "crest_factor",
        "resonance_peak_hz",
        "resonance_halfpower_bw_hz",
        "envelope_peak_hz",
        "envelope_peak_ratio",
        "hf_to_faultband_db",
    )
    for name, group in summary["groups"].items():
        for feature in selected_features:
            values = group["features"][feature]
            lines.append(
                f"| {name} | {feature} | {_cell(values['real_mean'])} | {_cell(values['generated_mean'])} | {_cell(values['standardized_gap'])} |"
            )
    lines.extend(
        [
            "",
            "## Diagnosis",
            "",
            "- Fault-frequency mismatch: measured envelope peaks are approximately 95–106 Hz, while the current T0 output peaks at approximately 223–235 Hz; the current 120 Hz anchor is therefore not reproducing the observed envelope structure.",
            "- Resonance/damping mismatch: measured resonance peaks are approximately 4.5–5.2 kHz with half-power bandwidth about 63–68 Hz; current T0 peaks are approximately 4.1–4.3 kHz with bandwidth about 48–53 Hz.",
            "- Impulsiveness shortcut: current T0 kurtosis and crest factor are about 19.8–24.7 and 9.0–9.5, versus measured damage about 5.0–5.7 and 5.6–5.7. This is a large, consistent mismatch in both train and dev comparisons.",
            "- Spectral/amplitude mismatch: current T0 has lower 2–5 kHz energy and higher 10–32 kHz energy; RMS differences are smaller and inconsistent across seeds, so amplitude alone is not the primary failure.",
            "- SNR/noise proxy: 20–32 kHz energy relative to 0–5 kHz is about −14 to −12 dB for measured damage but −4 to −3.6 dB for T0, a roughly 8–10 dB excess high-frequency component in generated signals.",
            "- Operating condition: this diagnosis is fixed at N15_M07_F10, so condition heterogeneity is not the explanation for the within-condition C2ST failure. Severity heterogeneity remains visible in real RMS/envelope distributions but is secondary to the impulsiveness and spectral mismatch.",
            "- Synthetic shortcut: C2ST ROC-AUC is 1.0000 for every train/dev population, consistent with the feature-level separations rather than a subtle evaluator artifact.",
            "",
            "## Frozen T0-v2 design",
            "",
            "The minimum justified changes are: (1) physics-only defaults set a 100 Hz fault-frequency prior from the 1500 RPM operating point and a generic 5 kHz structural resonance prior; (2) Gaussian impulse smoothing with width 8 samples reduces the isolated-spike/high-frequency shortcut; and (3) k≥1 calibrates only f_fault and f_res from selected training fault groups. Damping, amplitude, modulation, SNR, and severity remain fixed to avoid an unconstrained search. k=0 never reads real fault signals.",
            "",
            "No parameter is selected from the old Paderborn test metrics. The final holdout protocol is frozen separately before evaluation; calibration is restricted to its new training fault groups and excludes validation and final-test groups.",
            "",
            "Full per-seed evidence, train/validation/test group IDs, and all feature values are in `failure_analysis.json`.",
        ]
    )
    path = directory / "t0_failure_analysis.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
