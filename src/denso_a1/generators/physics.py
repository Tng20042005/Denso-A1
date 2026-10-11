from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import hilbert, welch

from denso_a1.schema import SampleBatch, SampleMetadata


@dataclass(frozen=True)
class PhysicsConfig:
    fs_hz: float = 1_000.0
    f_fault_hz: float = 80.0
    f_res_hz: float = 120.0
    damping: float = 0.08
    impulse_amplitude: float = 0.8
    jitter_std: float = 0.025
    modulation_depth: float = 0.25
    snr_db: float = 14.0
    severity: float = 1.0

    def validate(self) -> None:
        nyquist = self.fs_hz / 2
        if not 0 < self.f_fault_hz < nyquist:
            raise ValueError("f_fault_hz must be between zero and Nyquist")
        if not 0 < self.f_res_hz < nyquist:
            raise ValueError("f_res_hz must be between zero and Nyquist")
        if not 0 < self.damping < 1:
            raise ValueError("damping must be in (0, 1)")
        if not 0 <= self.modulation_depth <= 1:
            raise ValueError("modulation_depth must be in [0, 1]")
        if self.snr_db <= 0 or self.severity < 0:
            raise ValueError("snr_db must be positive and severity non-negative")

    @property
    def config_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:16]


def bearing_characteristic_frequencies(
    shaft_hz: float, n_elements: int, roller_diameter: float, pitch_diameter: float, angle_rad: float
) -> dict[str, float]:
    """Return BPFO/BPFI/BSF/FTF only when geometry is available."""
    ratio = (roller_diameter / pitch_diameter) * np.cos(angle_rad)
    return {
        "BPFO": (n_elements / 2) * shaft_hz * (1 - ratio),
        "BPFI": (n_elements / 2) * shaft_hz * (1 + ratio),
        "BSF": (pitch_diameter / (2 * roller_diameter)) * shaft_hz * (1 - ratio**2),
        "FTF": (shaft_hz / 2) * (1 - ratio),
    }


def _rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(signal))) + 1e-12)


def _inject(signal: np.ndarray, config: PhysicsConfig, rng: np.random.Generator) -> np.ndarray:
    config.validate()
    n = len(signal)
    t = np.arange(n) / config.fs_hz
    period = config.fs_hz / config.f_fault_hz
    phase = rng.uniform(0, period)
    impulses = np.zeros(n)
    cursor = phase
    while cursor < n:
        idx = round(cursor)
        if 0 <= idx < n:
            impulses[idx] = 1.0
        cursor += max(1.0, period * (1 + rng.normal(0, config.jitter_std)))
    resonance_len = max(8, round(config.fs_hz / config.f_res_hz * 6))
    impulse_t = np.arange(resonance_len) / config.fs_hz
    ring = np.exp(-config.damping * config.fs_hz * impulse_t) * np.sin(2 * np.pi * config.f_res_hz * impulse_t)
    resonance = np.convolve(impulses, ring, mode="same")
    resonance /= max(_rms(resonance), 1e-12)
    modulation = 1 + config.modulation_depth * np.sin(2 * np.pi * (config.f_fault_hz / 3) * t)
    injected = config.severity * config.impulse_amplitude * modulation * resonance
    target_noise_rms = _rms(signal) / (10 ** (config.snr_db / 20))
    return signal + injected + rng.normal(0, target_noise_rms, n)


class T0Generator:
    """Physics-informed, mechanism-like anomaly injector.

    It does not claim that an output is a physical DENSO fault; the output is
    labelled as algorithmic injection and retains train-only parent provenance.
    """

    name = "t0_physics_injection"
    version = "0.1"

    def __init__(self, config: PhysicsConfig | None = None) -> None:
        self.config = config or PhysicsConfig()
        self.config.validate()

    def inject(self, signal: np.ndarray, *, seed: int) -> np.ndarray:
        return _inject(np.asarray(signal, dtype=float), self.config, np.random.default_rng(seed))

    def generate_from_parents(
        self, parents: SampleBatch, parent_indices: np.ndarray | list[int], *, seed: int, split_seed: int | None = None
    ) -> SampleBatch:
        rng = np.random.default_rng(seed)
        idx = np.asarray(parent_indices, dtype=int)
        outputs = []
        metadata: list[SampleMetadata] = []
        for ordinal, parent_index in enumerate(idx):
            parent = parents.metadata[int(parent_index)]
            child_seed = int(rng.integers(0, 2**31 - 1))
            outputs.append(self.inject(parents.signals[int(parent_index)], seed=child_seed))
            metadata.append(
                SampleMetadata(
                    sample_id=f"{parent.sample_id}-t0-{ordinal:04d}",
                    source_type="generated",
                    fault_origin="algorithmic_injection",
                    source_dataset=parent.source_dataset,
                    source_version=parent.source_version,
                    raw_record_id=parent.raw_record_id,
                    group_id=f"generated-{parent.group_id}-{ordinal:04d}",
                    condition_id=parent.condition_id,
                    parent_ids=[parent.sample_id],
                    parent_group_ids=[parent.group_id],
                    split_role="train",
                    fs_hz=parent.fs_hz,
                    n_samples=parents.signals.shape[1],
                    label_binary=1,
                    label_condition="mechanism_like_injection",
                    severity=self.config.severity,
                    generator=self.name,
                    generator_version=self.version,
                    config_hash=self.config.config_hash,
                    split_seed=split_seed,
                    generator_seed=child_seed,
                    operating_cond=parent.operating_cond.copy(),
                    created_at=parent.created_at,
                )
            )
        return SampleBatch(np.asarray(outputs), metadata)


@dataclass(frozen=True)
class T0V2Config:
    """Frozen physics-only defaults for the failure-analysis follow-up."""

    fs_hz: float = 64_000.0
    f_fault_hz: float = 100.0
    f_res_hz: float = 5_000.0
    damping: float = 0.04
    impulse_amplitude: float = 0.35
    jitter_std: float = 0.025
    modulation_depth: float = 0.10
    snr_db: float = 10.0
    severity: float = 1.0
    impulse_width_samples: float = 8.0

    def validate(self) -> None:
        if not 0 < self.f_fault_hz < self.fs_hz / 2:
            raise ValueError("f_fault_hz must be between zero and Nyquist")
        if not 0 < self.f_res_hz < self.fs_hz / 2:
            raise ValueError("f_res_hz must be between zero and Nyquist")
        if not 0 < self.damping < 1:
            raise ValueError("damping must be in (0, 1)")
        if self.impulse_amplitude < 0 or self.impulse_width_samples < 0:
            raise ValueError("impulse amplitude and width must be non-negative")
        if not 0 <= self.modulation_depth <= 1 or self.snr_db <= 0 or self.severity < 0:
            raise ValueError("invalid T0-v2 modulation, SNR, or severity")

    @property
    def config_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:16]


def _inject_v2(signal: np.ndarray, config: T0V2Config, rng: np.random.Generator) -> np.ndarray:
    config.validate()
    n = len(signal)
    t = np.arange(n) / config.fs_hz
    period = config.fs_hz / config.f_fault_hz
    phase = rng.uniform(0, period)
    impulses = np.zeros(n)
    cursor = phase
    while cursor < n:
        idx = round(cursor)
        if 0 <= idx < n:
            impulses[idx] = 1.0
        cursor += max(1.0, period * (1 + rng.normal(0, config.jitter_std)))
    if config.impulse_width_samples > 0:
        impulses = gaussian_filter1d(impulses, sigma=config.impulse_width_samples, mode="wrap")
        impulses /= max(np.max(impulses), 1e-12)
    resonance_len = max(16, round(config.fs_hz / config.f_res_hz * 8))
    impulse_t = np.arange(resonance_len) / config.fs_hz
    ring = np.exp(-config.damping * config.fs_hz * impulse_t) * np.sin(
        2 * np.pi * config.f_res_hz * impulse_t
    )
    resonance = np.convolve(impulses, ring, mode="same")
    resonance /= max(_rms(resonance), 1e-12)
    modulation = 1 + config.modulation_depth * np.sin(2 * np.pi * config.f_fault_hz * t)
    injected = config.severity * config.impulse_amplitude * modulation * resonance
    target_noise_rms = _rms(signal) / (10 ** (config.snr_db / 20))
    return signal + injected + rng.normal(0, target_noise_rms, n)


class T0V2Generator:
    """Minimal follow-up generator frozen after the T0 failure analysis.

    The default configuration is physics-only. Calibration, when explicitly
    supplied, must be derived from train fault groups by the caller.
    """

    name = "t0_physics_injection_v2"
    version = "0.2"

    def __init__(self, config: T0V2Config | None = None) -> None:
        self.config = config or T0V2Config()
        self.config.validate()

    def inject(self, signal: np.ndarray, *, seed: int) -> np.ndarray:
        return _inject_v2(np.asarray(signal, dtype=float), self.config, np.random.default_rng(seed))

    def generate_from_parents(
        self,
        parents: SampleBatch,
        parent_indices: np.ndarray | list[int],
        *,
        seed: int,
        split_seed: int | None = None,
    ) -> SampleBatch:
        rng = np.random.default_rng(seed)
        idx = np.asarray(parent_indices, dtype=int)
        outputs = []
        metadata: list[SampleMetadata] = []
        for ordinal, parent_index in enumerate(idx):
            parent = parents.metadata[int(parent_index)]
            child_seed = int(rng.integers(0, 2**31 - 1))
            outputs.append(self.inject(parents.signals[int(parent_index)], seed=child_seed))
            metadata.append(
                SampleMetadata(
                    sample_id=f"{parent.sample_id}-t0v2-{ordinal:04d}",
                    source_type="generated",
                    fault_origin="algorithmic_injection",
                    source_dataset=parent.source_dataset,
                    source_version=parent.source_version,
                    raw_record_id=parent.raw_record_id,
                    group_id=f"generated-v2-{parent.group_id}-{ordinal:04d}",
                    condition_id=parent.condition_id,
                    parent_ids=[parent.sample_id],
                    parent_group_ids=[parent.group_id],
                    split_role="train",
                    fs_hz=parent.fs_hz,
                    n_samples=parents.signals.shape[1],
                    label_binary=1,
                    label_condition="mechanism_like_injection_v2",
                    severity=self.config.severity,
                    generator=self.name,
                    generator_version=self.version,
                    config_hash=self.config.config_hash,
                    split_seed=split_seed,
                    generator_seed=child_seed,
                    operating_cond=parent.operating_cond.copy(),
                    created_at=parent.created_at,
                )
            )
        return SampleBatch(np.asarray(outputs), metadata)


def calibrate_t0v2_from_training_faults(
    fault_signals: np.ndarray, *, fs_hz: float, base: T0V2Config | None = None
) -> T0V2Config:
    """Calibrate only frequency anchors from the supplied train fault groups."""
    config = base or T0V2Config(fs_hz=fs_hz)
    values = np.asarray(fault_signals, dtype=float)
    if values.ndim != 2 or len(values) == 0:
        raise ValueError("training fault signals must be a non-empty 2D array")
    centered = values - np.mean(values, axis=1, keepdims=True)
    envelope = np.abs(hilbert(centered, axis=1))
    envelope -= np.mean(envelope, axis=1, keepdims=True)
    envelope_freqs = np.fft.rfftfreq(values.shape[1], 1 / fs_hz)
    envelope_spectrum = np.abs(np.fft.rfft(envelope, axis=1))
    envelope_mask = (envelope_freqs >= 30.0) & (envelope_freqs <= 500.0)
    fault_frequency = np.median(
        envelope_freqs[envelope_mask][np.argmax(envelope_spectrum[:, envelope_mask], axis=1)]
    )
    freqs, psd = welch(centered, fs=fs_hz, nperseg=min(2048, values.shape[1]), axis=1)
    resonance_mask = (freqs >= 1_000.0) & (freqs <= min(20_000.0, fs_hz / 2))
    resonance_frequency = np.median(
        freqs[resonance_mask][np.argmax(psd[:, resonance_mask], axis=1)]
    )
    return replace(
        config,
        fs_hz=fs_hz,
        f_fault_hz=float(fault_frequency),
        f_res_hz=float(resonance_frequency),
    )


def envelope_spectrum(signal: np.ndarray, fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    envelope = np.abs(hilbert(np.asarray(signal, dtype=float)))
    centered = envelope - envelope.mean()
    spectrum = np.abs(np.fft.rfft(centered))
    frequencies = np.fft.rfftfreq(len(signal), 1 / fs_hz)
    return frequencies, spectrum
