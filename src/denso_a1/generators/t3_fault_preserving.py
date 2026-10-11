from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass

import numpy as np
from scipy.signal import hilbert

from denso_a1.schema import SampleBatch, SampleMetadata

T3_OPERATORS = (
    "amplitude",
    "shift",
    "noise",
    "phase",
    "spectral",
    "time_scale",
    "envelope",
)


@dataclass(frozen=True)
class T3Config:
    """Conservative, frozen ranges for measured-fault-preserving augmentation."""

    amplitude_min: float = 0.98
    amplitude_max: float = 1.02
    shift_fraction: float = 0.005
    noise_fraction_min: float = 0.02
    noise_fraction_max: float = 0.06
    noise_max_hz: float = 16_000.0
    phase_std_rad: float = 0.015
    spectral_fraction: float = 0.02
    spectral_min_hz: float = 500.0
    time_scale_fraction: float = 0.003
    envelope_fraction: float = 0.02
    envelope_nodes: int = 32
    version: str = "t3-fault-preserving-v1"

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()


def _smooth_random(rng: np.random.Generator, n: int, nodes: int) -> np.ndarray:
    anchors = np.linspace(0.0, 1.0, max(2, nodes))
    values = rng.normal(0.0, 1.0, len(anchors))
    return np.interp(np.linspace(0.0, 1.0, n), anchors, values)


def _edge_shift(signal: np.ndarray, shift: int) -> np.ndarray:
    if shift == 0:
        return signal.copy()
    result = np.empty_like(signal)
    if shift > 0:
        result[:shift] = signal[0]
        result[shift:] = signal[:-shift]
    else:
        amount = -shift
        result[-amount:] = signal[-1]
        result[:-amount] = signal[amount:]
    return result


def _amplitude(signal: np.ndarray, rng: np.random.Generator, cfg: T3Config) -> np.ndarray:
    return signal * rng.uniform(cfg.amplitude_min, cfg.amplitude_max)


def _shift(signal: np.ndarray, rng: np.random.Generator, cfg: T3Config) -> np.ndarray:
    limit = max(1, round(len(signal) * cfg.shift_fraction))
    return _edge_shift(signal, int(rng.integers(-limit, limit + 1)))


def _normal_floor_noise(
    normal_signal: np.ndarray, target_rms: float, rng: np.random.Generator, cfg: T3Config
) -> np.ndarray:
    centered = normal_signal - np.mean(normal_signal)
    spectrum = np.fft.rfft(centered)
    frequencies = np.fft.rfftfreq(len(centered), d=1.0 / 64_000.0)
    mask = (frequencies > 0.0) & (frequencies <= cfg.noise_max_hz)
    random_phase = rng.uniform(-np.pi, np.pi, len(spectrum))
    shaped = np.zeros_like(spectrum, dtype=complex)
    shaped[mask] = np.abs(spectrum[mask]) * np.exp(1j * random_phase[mask])
    noise = np.fft.irfft(shaped, n=len(centered)).real
    noise_rms = float(np.sqrt(np.mean(noise**2))) + 1e-12
    return noise * (target_rms / noise_rms)


def _noise(signal: np.ndarray, normal_signal: np.ndarray, rng: np.random.Generator, cfg: T3Config) -> np.ndarray:
    fraction = rng.uniform(cfg.noise_fraction_min, cfg.noise_fraction_max)
    rms = float(np.sqrt(np.mean((signal - np.mean(signal)) ** 2)))
    return signal + _normal_floor_noise(normal_signal, fraction * rms, rng, cfg)


def _phase(signal: np.ndarray, rng: np.random.Generator, cfg: T3Config) -> np.ndarray:
    spectrum = np.fft.rfft(signal - np.mean(signal))
    phase = np.angle(spectrum)
    perturbation = rng.normal(0.0, cfg.phase_std_rad, len(phase))
    perturbation[0] = 0.0
    if len(perturbation) > 1:
        perturbation[-1] = 0.0
    return np.fft.irfft(np.abs(spectrum) * np.exp(1j * (phase + perturbation)), n=len(signal)).real


def _spectral(signal: np.ndarray, rng: np.random.Generator, cfg: T3Config) -> np.ndarray:
    centered = signal - np.mean(signal)
    spectrum = np.fft.rfft(centered)
    frequencies = np.fft.rfftfreq(len(signal), d=1.0 / 64_000.0)
    perturbation = _smooth_random(rng, len(spectrum), cfg.envelope_nodes)
    perturbation = np.clip(1.0 + cfg.spectral_fraction * perturbation, 1.0 - cfg.spectral_fraction, 1.0 + cfg.spectral_fraction)
    perturbation[frequencies < cfg.spectral_min_hz] = 1.0
    return np.fft.irfft(np.abs(spectrum) * perturbation * np.exp(1j * np.angle(spectrum)), n=len(signal)).real


def _time_scale(signal: np.ndarray, metadata: SampleMetadata, cfg: T3Config) -> np.ndarray:
    speed = float(metadata.operating_cond.get("speed_rpm", 1500.0))
    reference = 1500.0
    scale = np.clip(reference / max(speed, 1.0), 1.0 - cfg.time_scale_fraction, 1.0 + cfg.time_scale_fraction)
    center = (len(signal) - 1) / 2.0
    source = center + (np.arange(len(signal)) - center) / scale
    return np.interp(source, np.arange(len(signal)), signal, left=signal[0], right=signal[-1])


def _envelope(signal: np.ndarray, rng: np.random.Generator, cfg: T3Config) -> np.ndarray:
    centered = signal - np.mean(signal)
    analytic = hilbert(centered)
    envelope = np.abs(analytic)
    phase = np.angle(analytic)
    factor = 1.0 + cfg.envelope_fraction * _smooth_random(rng, len(signal), cfg.envelope_nodes)
    factor = np.clip(factor, 1.0 - cfg.envelope_fraction, 1.0 + cfg.envelope_fraction)
    return np.real((envelope * factor) * np.exp(1j * phase)) + np.mean(signal)


def apply_operator(
    signal: np.ndarray,
    metadata: SampleMetadata,
    normal_signal: np.ndarray,
    operator: str,
    rng: np.random.Generator,
    config: T3Config,
) -> np.ndarray:
    if operator == "amplitude":
        return _amplitude(signal, rng, config)
    if operator == "shift":
        return _shift(signal, rng, config)
    if operator == "noise":
        return _noise(signal, normal_signal, rng, config)
    if operator == "phase":
        return _phase(signal, rng, config)
    if operator == "spectral":
        return _spectral(signal, rng, config)
    if operator == "time_scale":
        return _time_scale(signal, metadata, config)
    if operator == "envelope":
        return _envelope(signal, rng, config)
    raise ValueError(f"unknown T3 operator: {operator}")


def apply_policy(
    parents: SampleBatch,
    normal_reference: SampleBatch,
    parent_indices: Iterable[int],
    *,
    policy: tuple[str, ...],
    seed: int,
    config: T3Config | None = None,
) -> SampleBatch:
    config = config or T3Config()
    if not policy or any(operator not in T3_OPERATORS for operator in policy):
        raise ValueError(f"invalid T3 policy: {policy}")
    normal_signals = normal_reference.signals
    rng = np.random.default_rng(seed)
    outputs: list[np.ndarray] = []
    metadata: list[SampleMetadata] = []
    for ordinal, parent_index in enumerate(np.asarray(list(parent_indices), dtype=int)):
        parent = parents.metadata[int(parent_index)]
        signal = parents.signals[int(parent_index)].copy()
        normal_signal = normal_signals[int(rng.integers(0, len(normal_signals)))]
        for operator in policy:
            signal = apply_operator(signal, parent, normal_signal, operator, rng, config)
        metadata.append(
            SampleMetadata(
                sample_id=f"{parent.sample_id}-t3-{seed}-{ordinal:04d}",
                source_type="generated",
                fault_origin="algorithmic_injection",
                source_dataset=parent.source_dataset,
                source_version=parent.source_version,
                raw_record_id=parent.raw_record_id,
                group_id=f"generated-t3-{parent.group_id}-{seed}-{ordinal:04d}",
                condition_id=parent.condition_id,
                parent_ids=[parent.sample_id],
                parent_group_ids=[parent.group_id],
                split_role="train",
                fs_hz=parent.fs_hz,
                n_samples=len(signal),
                units=parent.units,
                label_binary=parent.label_binary,
                label_condition="t3_fault_preserving_augmentation",
                generator="t3_fault_preserving_augmentation",
                generator_version=config.version,
                config_hash=config.digest(),
                generator_seed=seed,
                operating_cond={**parent.operating_cond, "t3_policy": list(policy)},
                created_at=parent.created_at,
            )
        )
        outputs.append(signal)
    return SampleBatch(np.asarray(outputs), metadata)
