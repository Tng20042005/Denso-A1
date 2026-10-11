from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from denso_a1.schema import SampleBatch, SampleMetadata


@dataclass(frozen=True)
class ProtocolSplit:
    train: np.ndarray
    val: np.ndarray
    test: np.ndarray
    selected_fault_groups: tuple[str, ...]
    train_groups: tuple[str, ...]
    val_groups: tuple[str, ...]
    test_groups: tuple[str, ...]
    split_mode: str = "random_group"
    heldout_load_hp: int | None = None
    val_load_hp: int | None = None


def _normal_signal(t: np.ndarray, rng: np.random.Generator, speed_hz: float) -> np.ndarray:
    phase = rng.uniform(0, 2 * np.pi)
    base = 0.85 * np.sin(2 * np.pi * speed_hz * t + phase)
    harmonic = 0.18 * np.sin(2 * np.pi * 2 * speed_hz * t + phase / 3)
    slow = 0.08 * np.sin(2 * np.pi * 1.5 * t + rng.uniform(0, 2 * np.pi))
    return base + harmonic + slow + rng.normal(0, 0.08, len(t))


def _physical_fault_signal(t: np.ndarray, rng: np.random.Generator, speed_hz: float) -> np.ndarray:
    signal = _normal_signal(t, rng, speed_hz)
    fault_hz = speed_hz * rng.choice([3.2, 4.1, 5.0])
    period = max(1, round(len(t) / (fault_hz * (t[-1] - t[0] + 1 / len(t)))))
    impulse_positions = np.arange(rng.integers(0, period), len(t), period)
    impulse = np.zeros_like(t)
    decay = max(2, int(0.018 * len(t)))
    for pos in impulse_positions:
        end = min(len(t), pos + decay)
        impulse[pos:end] += np.exp(-np.arange(end - pos) / (0.25 * decay))
    resonance = 0.42 * impulse * np.sin(2 * np.pi * 120 * t)
    modulation = 1 + 0.25 * np.sin(2 * np.pi * speed_hz * t)
    return signal + 0.8 * modulation * resonance + rng.normal(0, 0.04, len(t))


def make_simulated_dataset(
    *,
    normal_groups: int = 12,
    fault_groups: int = 8,
    windows_per_group: int = 4,
    length: int = 512,
    fs_hz: float = 1_000.0,
    seed: int = 7,
) -> SampleBatch:
    """Create a mechanism-validation corpus with explicit simulated provenance."""
    rng = np.random.default_rng(seed)
    t = np.arange(length) / fs_hz
    signals: list[np.ndarray] = []
    metadata: list[SampleMetadata] = []
    stamp = datetime.now(UTC).isoformat()
    for label, count in ((0, normal_groups), (1, fault_groups)):
        for group_number in range(count):
            group_id = f"sim-{('normal' if label == 0 else 'fault')}-{group_number:03d}"
            speed_hz = float(rng.choice([18.0, 22.0, 26.0]))
            for window in range(windows_per_group):
                signal = (_physical_fault_signal if label else _normal_signal)(t, rng, speed_hz)
                sample_id = f"{group_id}-w{window:03d}"
                signals.append(signal)
                metadata.append(
                    SampleMetadata(
                        sample_id=sample_id,
                        source_type="simulated",
                        fault_origin="seeded_physical" if label else "unknown",
                        source_dataset="denso_a1_simulator",
                        source_version="0.1",
                        raw_record_id=group_id,
                        group_id=group_id,
                        condition_id=f"speed-{speed_hz:g}hz",
                        fs_hz=fs_hz,
                        n_samples=length,
                        label_binary=label,
                        label_condition="simulated_fault" if label else "normal",
                        operating_cond={"speed_hz": speed_hz},
                        created_at=stamp,
                    )
                )
    return SampleBatch(np.asarray(signals), metadata)


def make_protocol_split(batch: SampleBatch, *, k: int, split_seed: int, subset_seed: int) -> ProtocolSplit:
    """Split by group and select exactly k fault groups for training."""
    rng = np.random.default_rng(split_seed)
    subset_rng = np.random.default_rng(subset_seed)
    normal_groups = sorted({m.group_id for m in batch.metadata if m.label_binary == 0})
    fault_groups = sorted({m.group_id for m in batch.metadata if m.label_binary == 1})
    rng.shuffle(normal_groups)
    rng.shuffle(fault_groups)
    if len(normal_groups) < 4 or len(fault_groups) < 3:
        raise ValueError("need at least four normal and three fault groups")
    # Keep at least one normal group in each role for small public corpora such
    # as the four-file CWRU normal baseline subset.
    if len(normal_groups) <= 4:
        n_test, n_val = 1, 1
    else:
        n_test = max(2, len(normal_groups) // 5)
        n_val = max(2, len(normal_groups) // 5)
    test_groups = set(normal_groups[:n_test] + fault_groups[:2])
    val_groups = set(normal_groups[n_test : n_test + n_val] + fault_groups[2:3])
    remaining_faults = [g for g in fault_groups if g not in test_groups | val_groups]
    if k > len(remaining_faults):
        raise ValueError(f"k={k} exceeds available train fault groups={len(remaining_faults)}")
    subset_rng.shuffle(remaining_faults)
    selected_faults = tuple(sorted(remaining_faults[:k]))
    train_groups = set(normal_groups[n_test + n_val :]) | set(selected_faults)
    train = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in train_groups], dtype=int)
    val = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in val_groups], dtype=int)
    test = np.asarray([i for i, m in enumerate(batch.metadata) if m.group_id in test_groups], dtype=int)
    batch.with_split("train", train, split_seed)
    batch.with_split("val", val, split_seed)
    batch.with_split("test", test, split_seed)
    return ProtocolSplit(
        train=train,
        val=val,
        test=test,
        selected_fault_groups=selected_faults,
        train_groups=tuple(sorted(train_groups)),
        val_groups=tuple(sorted(val_groups)),
        test_groups=tuple(sorted(test_groups)),
        split_mode="random_group",
    )
