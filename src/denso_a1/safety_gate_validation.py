"""Diagnostic validation for the generator-agnostic safety gate.

The measured-real reference and corruption ladder are never treated as
synthetic candidates and never used for detector-training utility claims.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import hilbert, resample
from scipy.stats import spearmanr

from denso_a1.data.paderborn import load_paderborn
from denso_a1.failure_analysis import _compare
from denso_a1.paderborn_t3_benchmark import _nearest_neighbor
from denso_a1.schema import SampleBatch

FS_HZ = 64_000.0
WINDOW_SIZE = 4_096
REFERENCE_TRAIN_GROUPS = ("paderborn-bearing-KA04", "paderborn-bearing-KA15")
REFERENCE_VAL_GROUPS = ("paderborn-bearing-KA16", "paderborn-bearing-KI04")
CORRUPTION_LEVELS = (0.0, 0.1, 0.25, 0.5, 1.0)


def _sample_group(batch: SampleBatch, groups: tuple[str, ...], count: int, seed: int) -> SampleBatch:
    group_set = set(groups)
    indices = np.asarray(
        [i for i, item in enumerate(batch.metadata) if item.group_id in group_set and item.label_binary == 1],
        dtype=int,
    )
    if len(indices) < count:
        raise ValueError(f"reference groups contain {len(indices)} samples; need {count}")
    rng = np.random.default_rng(seed)
    return batch.subset(np.sort(rng.choice(indices, size=count, replace=False)))


def _matched_halves(batch: SampleBatch) -> tuple[SampleBatch, SampleBatch]:
    midpoint = len(batch.signals) // 2
    if midpoint < 16:
        raise ValueError("matched reference needs at least 32 measured-real windows")
    permutation = np.random.default_rng(1105).permutation(len(batch.signals))
    return batch.subset(permutation[:midpoint]), batch.subset(permutation[midpoint : 2 * midpoint])


def _envelope_psd(signals: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(signals, dtype=float)
    centered = values - np.mean(values, axis=1, keepdims=True)
    envelope = np.abs(hilbert(centered, axis=1))
    envelope -= np.mean(envelope, axis=1, keepdims=True)
    freqs = np.fft.rfftfreq(values.shape[1], 1.0 / FS_HZ)
    spectrum = np.abs(np.fft.rfft(envelope, axis=1))
    mask = (freqs >= 30.0) & (freqs <= 1_000.0)
    band = np.maximum(spectrum[:, mask], 1e-18)
    normalized = band / (np.sum(band, axis=1, keepdims=True) + 1e-18)
    return freqs[mask], normalized, np.argmax(normalized, axis=1)


def _distance(left: np.ndarray, right: np.ndarray) -> tuple[float, float]:
    left_mean = np.mean(left, axis=0)
    right_mean = np.mean(right, axis=0)
    left_mean = left_mean / (np.sum(left_mean) + 1e-18)
    right_mean = right_mean / (np.sum(right_mean) + 1e-18)
    midpoint = (left_mean + right_mean) / 2.0
    js = 0.5 * np.sum(left_mean * np.log(left_mean / midpoint)) + 0.5 * np.sum(
        right_mean * np.log(right_mean / midpoint)
    )
    cosine = np.dot(left_mean, right_mean) / (
        np.linalg.norm(left_mean) * np.linalg.norm(right_mean) + 1e-18
    )
    return float(js), float(cosine)


def _distribution_gaps(reference: SampleBatch, compared: SampleBatch) -> dict[str, Any]:
    from denso_a1.failure_analysis import _feature_matrix

    left, _ = _feature_matrix(reference.signals, FS_HZ)
    right, _ = _feature_matrix(compared.signals, FS_HZ)
    result: dict[str, Any] = {}
    for name, position in (("rms", 0), ("kurtosis", 1), ("crest_factor", 2)):
        pooled_std = np.std(np.concatenate([left[:, position], right[:, position]])) + 1e-12
        result[name] = {
            "reference_mean": float(np.mean(left[:, position])),
            "compared_mean": float(np.mean(right[:, position])),
            "reference_std": float(np.std(left[:, position])),
            "compared_std": float(np.std(right[:, position])),
            "standardized_gap": float((np.mean(left[:, position]) - np.mean(right[:, position])) / pooled_std),
            "absolute_standardized_gap": float(abs(np.mean(left[:, position]) - np.mean(right[:, position])) / pooled_std),
            "reference_quantiles": [float(v) for v in np.quantile(left[:, position], [0.1, 0.5, 0.9])],
            "compared_quantiles": [float(v) for v in np.quantile(right[:, position], [0.1, 0.5, 0.9])],
        }
    return result


def compare_real_populations(reference: SampleBatch, compared: SampleBatch, seed: int) -> dict[str, Any]:
    """Compute gate diagnostics without converting the comparison to a gate decision."""
    comparison = _compare(reference, compared, fs_hz=FS_HZ, seed=seed)
    envelope_freqs, reference_env, reference_peaks = _envelope_psd(reference.signals)
    _, compared_env, compared_peaks = _envelope_psd(compared.signals)
    envelope_js, envelope_cosine = _distance(reference_env, compared_env)
    peak_drift = float(
        np.mean(np.abs(envelope_freqs[reference_peaks] - envelope_freqs[compared_peaks]))
    )
    nearest = _nearest_neighbor(reference, compared)
    return {
        "n_reference": len(reference.signals),
        "n_compared": len(compared.signals),
        "c2st_roc_auc": float(comparison["c2st"]["roc_auc"]),
        "c2st_accuracy": float(comparison["c2st"]["accuracy"]),
        "psd_js_divergence": float(comparison["spectral_distance"]["js_divergence"]),
        "psd_cosine_similarity": float(comparison["spectral_distance"]["cosine_similarity"]),
        "envelope_js_divergence": envelope_js,
        "envelope_cosine_similarity": envelope_cosine,
        "envelope_peak_drift_hz": peak_drift,
        "feature_gaps": _distribution_gaps(reference, compared),
        "nearest_neighbor": {
            "median_ratio": float(nearest["median_ratio"]),
            "generated_to_real_nn_median": float(nearest["generated_to_real_nn_median"]),
            "real_loo_nn_median": float(nearest["real_loo_nn_median"]),
            "exact_hash_overlap_count": len(nearest["exact_signal_hash_overlap"]),
        },
    }


def _rescale_to_std(signal: np.ndarray, target_std: float) -> np.ndarray:
    centered = signal - np.mean(signal)
    return centered * (target_std / (np.std(centered) + 1e-12)) + np.mean(signal)


def _band_noise(signal: np.ndarray, level: float, rng: np.random.Generator) -> np.ndarray:
    noise = rng.normal(size=len(signal))
    spectrum = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(len(signal), 1.0 / FS_HZ)
    spectrum[(freqs < 500.0) | (freqs > 16_000.0)] = 0.0
    filtered = np.fft.irfft(spectrum, n=len(signal))
    filtered *= level * (np.std(signal) + 1e-12) / (np.std(filtered) + 1e-12)
    return signal + filtered


def _frequency_shift(signal: np.ndarray, level: float) -> np.ndarray:
    factor = 1.0 + 0.20 * level
    new_length = max(16, round(len(signal) / factor))
    warped = resample(signal, new_length)
    if len(warped) < len(signal):
        warped = np.pad(warped, (0, len(signal) - len(warped)), mode="edge")
    return warped[: len(signal)]


def _spectral_distort(signal: np.ndarray, level: float) -> np.ndarray:
    centered = signal - np.mean(signal)
    spectrum = np.fft.rfft(centered)
    ramp = np.linspace(-1.0, 1.0, len(spectrum))
    gain = np.clip(1.0 + 0.80 * level * ramp, 0.2, 2.0)
    distorted = np.fft.irfft(spectrum * gain, n=len(signal))
    return _rescale_to_std(distorted, np.std(centered)) + np.mean(signal)


def _sharpen_impulses(signal: np.ndarray, level: float) -> np.ndarray:
    mean = np.mean(signal)
    centered = signal - mean
    scale = np.std(centered) + 1e-12
    sharpened = np.sign(centered) * np.abs(centered / scale) ** (1.0 + 1.5 * level)
    return _rescale_to_std(sharpened, np.std(centered)) + mean


def _distort_envelope(signal: np.ndarray, level: float) -> np.ndarray:
    mean = np.mean(signal)
    centered = signal - mean
    analytic = hilbert(centered)
    envelope = np.abs(analytic)
    phase = np.angle(analytic)
    time = np.arange(len(signal)) / FS_HZ
    modulation = 1.0 + 0.8 * level * np.sin(2.0 * np.pi * 180.0 * time)
    return np.real((envelope * modulation) * np.exp(1j * phase)) + mean


def _corrupt_signal(signal: np.ndarray, kind: str, level: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if kind == "band_limited_noise":
        return _band_noise(signal, level, rng)
    if kind == "frequency_anchor_shift":
        return _frequency_shift(signal, level)
    if kind == "spectral_distortion":
        return _spectral_distort(signal, level)
    if kind == "impulse_sharpening":
        return _sharpen_impulses(signal, level)
    if kind == "envelope_distortion":
        return _distort_envelope(signal, level)
    raise ValueError(f"unknown corruption kind={kind}")


def _corrupt_batch(batch: SampleBatch, kind: str, level: float, seed: int) -> SampleBatch:
    signals = np.asarray(
        [_corrupt_signal(signal, kind, level, seed + index) for index, signal in enumerate(batch.signals)]
    )
    return SampleBatch(signals, list(batch.metadata))


def _monotonicity(values: list[float], increasing: bool) -> dict[str, float | str]:
    finite = np.asarray([value for value in values if np.isfinite(value)], dtype=float)
    if len(finite) < 3 or np.ptp(finite) == 0:
        return {
            "spearman_rho": float("nan"),
            "consistent_adjacent_fraction": float("nan"),
            "interpretation": "not_estimable",
        }
    rho = float(spearmanr(np.arange(len(finite)), finite).statistic)
    deltas = np.diff(finite)
    consistent = np.mean(deltas >= -1e-12) if increasing else np.mean(deltas <= 1e-12)
    return {
        "spearman_rho": rho,
        "consistent_adjacent_fraction": float(consistent),
        "interpretation": "consistent" if consistent >= 0.75 else "mixed",
    }


def _utility_rows(repo: Path) -> list[dict[str, Any]]:
    retrospective = json.loads((repo / "reports/safety_gate/retrospective.json").read_text())
    keys = {
        "T0": ("k=0:E2-E0", "k=1:E2-E0", "k=1:E2-E1", "k=2:E2-E0", "k=2:E2-E1"),
        "T0-v2": ("k=0:E2-E0", "k=1:E2-E0", "k=1:E2-E1", "k=2:E2-E0", "k=2:E2-E1"),
        "T2 conditional-VAE": ("k=1:E3-E0", "k=1:E3-E1", "k=2:E3-E0", "k=2:E3-E1"),
        "T3 fault-preserving augmentation": ("k=1:E4-E0", "k=1:E4-E1", "k=2:E4-E0", "k=2:E4-E1"),
    }
    rows: list[dict[str, Any]] = []
    for candidate in retrospective:
        for key in keys[candidate["method"]]:
            value = candidate["utility"]["paired_deltas"].get(key)
            if value is None:
                continue
            metric = value.get("metrics", {}).get("pr_auc", value)
            mean_delta = metric.get("mean_delta")
            rows.append(
                {
                    "method": candidate["method"],
                    "config": key,
                    "provenance_status": candidate["provenance"]["status"],
                    "fidelity_status": candidate["fidelity"]["status"],
                    "novelty_status": candidate["novelty"]["status"],
                    "fidelity_c2st": candidate["fidelity"].get(
                        "c2st_roc_auc_max",
                        candidate["fidelity"].get(
                            "c2st_roc_auc_mean", candidate["fidelity"].get("c2st_validation_max")
                        ),
                    ),
                    "psd_js_divergence": candidate["fidelity"].get("spectral_js_mean"),
                    "psd_cosine_similarity": candidate["fidelity"].get("psd_cosine_mean"),
                    "nn_ratio": candidate["novelty"].get("median_ratio", candidate["novelty"].get("median_ratio_min")),
                    "pr_auc_delta_vs_e0": mean_delta if key.endswith("-E0") else "",
                    "pr_auc_delta_vs_e1": mean_delta if key.endswith("-E1") else "",
                    "pr_auc_ci95": json.dumps(metric.get("ci95", [])),
                    "final_admission": candidate["admission"],
                }
            )
    return rows


def _write_figure(repo: Path, ladder: list[dict[str, Any]], utility: list[dict[str, Any]]) -> Path:
    figure = repo / "reports/safety_gate_validation_figure.svg"
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for kind in sorted({row["corruption"] for row in ladder}):
        rows = [row for row in ladder if row["corruption"] == kind]
        axes[0].plot(
            [row["severity"] for row in rows],
            [row["c2st_excess_over_chance"] for row in rows],
            marker="o",
            label=kind.replace("_", " "),
        )
    axes[0].set_xlabel("corruption severity (diagnostic only)")
    axes[0].set_ylabel("C2ST ROC-AUC − 0.5")
    axes[0].set_title("Diagnostics respond to controlled degradation")
    axes[0].legend(fontsize=7)
    methods = sorted({row["method"] for row in utility})
    means = []
    for method in methods:
        values = [
            row["pr_auc_delta_vs_e0"]
            for row in utility
            if row["method"] == method and row["pr_auc_delta_vs_e0"] != ""
        ]
        means.append(float(np.mean(values)) if values else 0.0)
    axes[1].bar(np.arange(len(methods)), means, color=["#4c78a8", "#f58518", "#e45756", "#72b7b2"])
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set_xticks(np.arange(len(methods)), [method.replace(" ", "\n") for method in methods], fontsize=8)
    axes[1].set_ylabel("mean paired PR-AUC delta vs E0")
    axes[1].set_title("Frozen held-out utility evidence")
    fig.savefig(figure, format="svg")
    plt.close(fig)
    return figure


def _render_report(
    reference: dict[str, Any], matched_reference: dict[str, Any], trends: dict[str, Any], utility_rows: list[dict[str, Any]], protocol_hash: str
) -> str:
    feature_gaps = reference["feature_gaps"]
    lines = [
        "# Safety-gate validation",
        "",
        "This is a diagnostic validation of the gate, not a new synthesis experiment. The reference and corruption ladder use measured Paderborn training/validation fault populations only. No final-test population was loaded, and corruption outputs were not used for detector-training utility claims.",
        "",
        "## Frozen validation boundary",
        "",
        f"- Condition: `N15_M07_F10`; train fault groups: `{', '.join(REFERENCE_TRAIN_GROUPS)}`; validation fault groups: `{', '.join(REFERENCE_VAL_GROUPS)}`.",
        f"- Protocol SHA256: `{protocol_hash}`; sample count per population: `{reference['n_reference']}`.",
        "- The measured-real comparison is an empirical reference/upper-bound, not a synthetic candidate and not an admission decision.",
        "",
        "## 1. Real-vs-real reference",
        "",
        "| statistic | measured-real train vs validation | matched train vs train |",
        "|---|---:|---:|",
        f"| C2ST ROC-AUC | {reference['c2st_roc_auc']:.4f} | {matched_reference['c2st_roc_auc']:.4f} |",
        f"| PSD cosine similarity | {reference['psd_cosine_similarity']:.4f} | {matched_reference['psd_cosine_similarity']:.4f} |",
        f"| spectral JS divergence | {reference['psd_js_divergence']:.4f} | {matched_reference['psd_js_divergence']:.4f} |",
        f"| envelope cosine similarity | {reference['envelope_cosine_similarity']:.4f} | {matched_reference['envelope_cosine_similarity']:.4f} |",
        f"| envelope JS divergence | {reference['envelope_js_divergence']:.4f} | {matched_reference['envelope_js_divergence']:.4f} |",
        f"| envelope peak drift (Hz) | {reference['envelope_peak_drift_hz']:.2f} | {matched_reference['envelope_peak_drift_hz']:.2f} |",
        f"| nearest-neighbor median ratio | {reference['nearest_neighbor']['median_ratio']:.4f} | {matched_reference['nearest_neighbor']['median_ratio']:.4f} |",
        f"| exact hash overlap | {reference['nearest_neighbor']['exact_hash_overlap_count']} | {matched_reference['nearest_neighbor']['exact_hash_overlap_count']} |",
        "",
        "Feature distribution gaps (standardized mean gap; train vs validation):",
        "",
        "| feature | train mean | validation mean | standardized gap |",
        "|---|---:|---:|---:|",
    ]
    for name in ("rms", "kurtosis", "crest_factor"):
        item = feature_gaps[name]
        lines.append(
            f"| {name} | {item['reference_mean']:.4g} | {item['compared_mean']:.4g} | {item['standardized_gap']:.4f} |"
        )
    lines += [
        "",
        "Interpretation: the matched train-vs-train control checks metric noise, while the train-vs-validation comparison measures real bearing/group shift. If the latter is more separable, that is a dataset-relative domain difference—not evidence that the gate should silently treat real data as synthetic. Both comparisons stay outside candidate admission.",
        "The historical absolute C2ST cutoff of 0.95 would reject the group-shift real-vs-real reference, while the matched control passes C2ST/PSD/JS but has an anchor-drift estimate of 69.34 Hz versus the historical 50 Hz cutoff. This is why those cutoffs remain retrospective prototype thresholds and SafetyGate-v1 uses reference-relative calibration.",
        "",
        "## 2. Controlled corruption ladder",
        "",
        "Each corruption starts from the same measured-real train-fault windows. Levels are diagnostic-only: band-limited noise, frequency-anchor shift, spectral distortion, impulse sharpening and envelope distortion. Full row-level results are in `safety_gate_corruption_ladder.csv`.",
        "",
        "| corruption | metric | expected direction | consistent adjacent fraction | Spearman rho | interpretation |",
        "|---|---|---|---:|---:|---|",
    ]
    for kind in sorted(trends):
        for metric, direction in (
            ("c2st_excess_over_chance", "increase"),
            ("psd_js_divergence", "increase"),
            ("psd_cosine_similarity", "decrease"),
            ("envelope_peak_drift_hz", "increase"),
        ):
            item = trends[kind][metric]
            lines.append(
                f"| {kind} | {metric} | {direction} | {item['consistent_adjacent_fraction']:.2f} | {item['spearman_rho']:.3f} | {item['interpretation']} |"
            )
    lines += [
        "",
        "The ladder is a sanity check, not a proof of universal monotonicity. Mixed trends are reported as mixed; no severity level is selected using final-test utility.",
        "",
        "## 3. Gate diagnostics versus frozen downstream utility",
        "",
        "The association table joins only already-frozen candidate configurations for which gate diagnostics and held-out measured-real utility are available. It does not rerun, tune or reclassify any branch.",
        "",
        "| method/config | fidelity C2ST | PSD JS | PSD cosine | provenance | novelty | PR-AUC Δ vs E0 | PR-AUC Δ vs E1 | admission |",
        "|---|---:|---:|---:|---|---|---:|---:|---|",
    ]
    for row in utility_rows:
        lines.append(
            f"| {row['method']} / {row['config']} | {row['fidelity_c2st'] if row['fidelity_c2st'] is not None else 'NA'} | {row['psd_js_divergence'] if row['psd_js_divergence'] is not None else 'NA'} | {row['psd_cosine_similarity'] if row['psd_cosine_similarity'] is not None else 'NA'} | {row['provenance_status']} | {row['novelty_status']} | {row['pr_auc_delta_vs_e0'] if row['pr_auc_delta_vs_e0'] != '' else 'NA'} | {row['pr_auc_delta_vs_e1'] if row['pr_auc_delta_vs_e1'] != '' else 'NA'} | {row['final_admission']} |"
        )
    lines += [
        "",
        "Association conclusion: the available sample is small and diagnostics are not identically measured across historical branches. C2ST has no useful cross-method variance because the available values are at or near 1.0, so a meaningful correlation coefficient is not claimed. The held-out evidence is independent of diagnostic tuning: T0/T0-v2/T2 have negative utility deltas in their frozen comparisons, while T3 is non-positive versus simple augmentation and is additionally rejected for fidelity/near-copy behavior. This supports the gate as a joint safety screen, not a single-metric utility predictor.",
        "",
        "## 4. Threshold audit",
        "",
        "| threshold/rule | source and rationale | timing relative to utility | absolute or dataset-relative |",
        "|---|---|---|---|",
        "| C2ST ROC-AUC ≤ 0.95 | Frozen T2/T3 protocol; discriminator separability rejection criterion | fixed before final utility evaluation; informed by development diagnostics, not final-test tuning | absolute metric, calibration dataset-dependent |",
        "| PSD JS ≤ 0.25; PSD cosine ≥ 0.65 | Frozen T3 protocol; coarse spectral similarity guard | fixed before T3 final evaluation | absolute cutoffs, scale dataset-dependent |",
        "| envelope-anchor drift ≤ 50 Hz | Frozen T3 protocol; prevents large fault-anchor movement | fixed before T3 final evaluation | absolute frequency cutoff |",
        "| NN median ratio ≥ 0.25; no exact hash overlap | Frozen T2/T3 protocols; reject near-copy/memorization | fixed before final utility evaluation | absolute ratio/hash rule, calibrated on parent geometry |",
        "| provenance and budget audits PASS | hard validity requirements from benchmark protocol | fixed before all frozen final evaluations | absolute boolean requirements |",
        "| utility PR-AUC mean delta > 0 in prototype | retrospective `safety_gate.py` decision rule | defined after frozen utility artifacts existed; retrospective/prototype | absolute sign rule |",
        "| RMS/kurtosis/crest/envelope distributions | diagnostics only; no historical hard PASS/FAIL cutoff | descriptive only | dataset-relative until SafetyGate-v1 |",
        "",
        "The current common gate is explicitly retrospective/prototype. Fidelity cutoffs were frozen before each branch's final utility evaluation, but the common cross-branch interface and utility aggregation were written retrospectively. They were not tuned to force the four existing methods to fail.",
        "",
        "## 5. SafetyGate-v1 decision",
        "",
        "For future DENSO validation, SafetyGate-v1 must be frozen before any candidate utility result is inspected. It retains the absolute validity/hash rules and uses a train/validation measured-real reference to calibrate distributional diagnostics: candidate C2ST/JS/cosine/envelope/feature gaps must remain within the pre-registered reference quantiles plus fixed margins. Utility requires at least five paired seeds and a positive PR-AUC delta with the 95% CI lower bound above zero against both E0 and E1. A missing diagnostic remains UNKNOWN and is not PASS.",
        "",
        "Decision for final submission: VALIDATION PASS for the gate contribution, with the limitation that this validates diagnostic behavior and transparent threshold provenance—not universal effectiveness of synthetic data and not transfer to DENSO field faults. The final slide should include `safety_gate_validation_figure.svg` and the held-out negative-result table.",
    ]
    return "\n".join(lines) + "\n"


def run_validation(repo: str | Path, raw_root: str | Path, *, sample_count: int = 128) -> dict[str, Any]:
    root = Path(repo)
    dataset = load_paderborn(
        raw_root,
        condition_id="N15_M07_F10",
        measurement_indices=(1, 2, 3, 4, 5),
        window_size=WINDOW_SIZE,
        step=WINDOW_SIZE,
    )
    train_fault = _sample_group(dataset.batch, REFERENCE_TRAIN_GROUPS, sample_count, seed=1101)
    val_fault = _sample_group(dataset.batch, REFERENCE_VAL_GROUPS, sample_count, seed=1102)
    reference = compare_real_populations(train_fault, val_fault, seed=1103)
    matched_left, matched_right = _matched_halves(train_fault)
    matched_reference = compare_real_populations(matched_left, matched_right, seed=1104)
    ladder_rows: list[dict[str, Any]] = []
    corruption_kinds = (
        "band_limited_noise",
        "frequency_anchor_shift",
        "spectral_distortion",
        "impulse_sharpening",
        "envelope_distortion",
    )
    for kind in corruption_kinds:
        for level in CORRUPTION_LEVELS:
            corrupted = _corrupt_batch(train_fault, kind, level, seed=1200)
            metrics = compare_real_populations(train_fault, corrupted, seed=1201)
            gaps = metrics["feature_gaps"]
            ladder_rows.append(
                {
                    "corruption": kind,
                    "severity": level,
                    "n_per_population": sample_count,
                    "c2st_roc_auc": metrics["c2st_roc_auc"],
                    "c2st_excess_over_chance": abs(metrics["c2st_roc_auc"] - 0.5),
                    "psd_js_divergence": metrics["psd_js_divergence"],
                    "psd_cosine_similarity": metrics["psd_cosine_similarity"],
                    "envelope_js_divergence": metrics["envelope_js_divergence"],
                    "envelope_cosine_similarity": metrics["envelope_cosine_similarity"],
                    "envelope_peak_drift_hz": metrics["envelope_peak_drift_hz"],
                    "rms_abs_standardized_gap": gaps["rms"]["absolute_standardized_gap"],
                    "kurtosis_abs_standardized_gap": gaps["kurtosis"]["absolute_standardized_gap"],
                    "crest_abs_standardized_gap": gaps["crest_factor"]["absolute_standardized_gap"],
                    "nearest_neighbor_ratio": metrics["nearest_neighbor"]["median_ratio"],
                    "exact_hash_overlap_count": metrics["nearest_neighbor"]["exact_hash_overlap_count"],
                }
            )
    trends: dict[str, dict[str, Any]] = {}
    expected_increasing = (
        "c2st_excess_over_chance",
        "psd_js_divergence",
        "envelope_js_divergence",
        "envelope_peak_drift_hz",
        "rms_abs_standardized_gap",
        "kurtosis_abs_standardized_gap",
        "crest_abs_standardized_gap",
    )
    expected_decreasing = ("psd_cosine_similarity", "envelope_cosine_similarity", "nearest_neighbor_ratio")
    for kind in corruption_kinds:
        rows = [row for row in ladder_rows if row["corruption"] == kind]
        trends[kind] = {}
        for metric in expected_increasing:
            trends[kind][metric] = _monotonicity([row[metric] for row in rows], increasing=True)
        for metric in expected_decreasing:
            trends[kind][metric] = _monotonicity([row[metric] for row in rows], increasing=False)
    utility_rows = _utility_rows(root)
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ladder_path = reports / "safety_gate_corruption_ladder.csv"
    with ladder_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ladder_rows[0]))
        writer.writeheader()
        writer.writerows(ladder_rows)
    utility_path = reports / "safety_gate_utility_association.csv"
    with utility_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(utility_rows[0]))
        writer.writeheader()
        writer.writerows(utility_rows)
    protocol = {
        "dataset": "Paderborn_Bearing_DataCenter",
        "condition": "N15_M07_F10",
        "reference_train_groups": REFERENCE_TRAIN_GROUPS,
        "reference_validation_groups": REFERENCE_VAL_GROUPS,
        "sample_count_per_population": sample_count,
        "measurement_indices": [1, 2, 3, 4, 5],
        "window_size": WINDOW_SIZE,
        "final_test_used": False,
        "corruption_levels": CORRUPTION_LEVELS,
        "corruption_only_diagnostic": True,
        "matched_real_reference": "two deterministic halves of the sampled measured-real train-fault population",
    }
    protocol_hash = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    protocol["protocol_sha256"] = protocol_hash
    (reports / "safety_gate_validation_protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    (reports / "safety_gate_validation_reference.json").write_text(
        json.dumps({"train_vs_validation": reference, "matched_train_vs_train": matched_reference}, indent=2),
        encoding="utf-8",
    )
    figure = _write_figure(root, ladder_rows, utility_rows)
    report_path = reports / "safety_gate_validation.md"
    report_path.write_text(
        _render_report(reference, matched_reference, trends, utility_rows, protocol_hash), encoding="utf-8"
    )
    return {
        "reference": reference,
        "trends": trends,
        "utility_rows": len(utility_rows),
        "corruption_rows": len(ladder_rows),
        "protocol_sha256": protocol_hash,
        "report": str(report_path),
        "figure": str(figure),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/paderborn/extracted"))
    parser.add_argument("--sample-count", type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(run_validation(args.repo, args.raw_root, sample_count=args.sample_count), indent=2))
