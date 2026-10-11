from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from denso_a1.data.simulated import ProtocolSplit
from denso_a1.schema import SampleBatch, SampleMetadata

PADERBORN_HEALTHY = ("K001", "K002", "K003", "K004")
PADERBORN_REAL_FAULTS = ("KA04", "KA15", "KA16", "KI04", "KI14", "KI16")
PADERBORN_CONDITIONS = {
    "N15_M07_F10": {"speed_rpm": 1500.0, "torque_nm": 0.7, "radial_force_n": 1000.0},
    "N15_M01_F10": {"speed_rpm": 1500.0, "torque_nm": 0.1, "radial_force_n": 1000.0},
    "N15_M07_F04": {"speed_rpm": 1500.0, "torque_nm": 0.7, "radial_force_n": 400.0},
    "N09_M07_F10": {"speed_rpm": 900.0, "torque_nm": 0.7, "radial_force_n": 1000.0},
}


@dataclass(frozen=True)
class PaderbornFileRecord:
    bearing_id: str
    path: str
    sha256: str
    n_raw_samples: int
    fs_hz: float
    channel: str
    condition_id: str
    label_binary: int
    label_condition: str
    group_id: str


@dataclass(frozen=True)
class PaderbornDataset:
    batch: SampleBatch
    files: tuple[PaderbornFileRecord, ...]
    condition_id: str
    measurement_indices: tuple[int, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _measurement_root(mat: dict[str, object]) -> object:
    candidates = [value for key, value in mat.items() if not key.startswith("_")]
    if len(candidates) != 1:
        raise ValueError(f"expected one measurement root, found {len(candidates)}")
    return candidates[0]


def _load_vibration(path: Path) -> np.ndarray:
    mat = loadmat(path, struct_as_record=False, squeeze_me=True)
    root = _measurement_root(mat)
    channels = getattr(root, "Y", None)
    if channels is None:
        raise KeyError(f"{path}: missing Y channels")
    for channel in np.atleast_1d(channels):
        if getattr(channel, "Name", None) == "vibration_1":
            signal = np.asarray(channel.Data, dtype=np.float64).reshape(-1)
            if not np.all(np.isfinite(signal)):
                raise ValueError(f"{path}: vibration contains non-finite values")
            return signal
    raise KeyError(f"{path}: missing vibration_1 channel")


def load_paderborn(
    root: str | Path,
    *,
    bearing_ids: tuple[str, ...] = PADERBORN_HEALTHY + PADERBORN_REAL_FAULTS,
    condition_id: str = "N15_M07_F10",
    fs_hz: float = 64_000.0,
    window_size: int = 4096,
    step: int = 4096,
    measurement_indices: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> PaderbornDataset:
    """Load one fixed operating condition from official Paderborn archives."""
    if condition_id not in PADERBORN_CONDITIONS:
        raise ValueError(f"unknown Paderborn condition_id={condition_id}")
    root_path = Path(root)
    signals: list[np.ndarray] = []
    metadata: list[SampleMetadata] = []
    records: list[PaderbornFileRecord] = []
    stamp = datetime.now(UTC).isoformat()
    condition = PADERBORN_CONDITIONS[condition_id]
    file_pattern = re.compile(rf"^{re.escape(condition_id)}_(?P<bearing>[A-Z0-9]+)_(?P<rep>\d+)\.mat$")
    for bearing_id in bearing_ids:
        bearing_dir = root_path / bearing_id
        paths = sorted(
            path
            for path in bearing_dir.glob(f"{condition_id}_{bearing_id}_*.mat")
            if int(path.stem.rsplit("_", 1)[1]) in set(measurement_indices)
        )
        if not paths:
            raise FileNotFoundError(f"no {condition_id} files found under {bearing_dir}")
        label = 0 if bearing_id.startswith("K") and not bearing_id.startswith(("KA", "KI", "KB")) else 1
        label_condition = "healthy" if label == 0 else "real_accelerated_damage"
        fault_origin = "unknown" if label == 0 else "accelerated_degradation"
        group_id = f"paderborn-bearing-{bearing_id}"
        for path in paths:
            match = file_pattern.match(path.name)
            if match is None or match.group("bearing") != bearing_id:
                raise ValueError(f"unexpected Paderborn file name: {path.name}")
            signal = _load_vibration(path)
            starts = range(0, len(signal) - window_size + 1, step)
            windows = [signal[start : start + window_size] for start in starts]
            if not windows:
                raise ValueError(f"{path}: signal shorter than window_size={window_size}")
            raw_record_id = path.name
            for window_index, window in enumerate(windows):
                signals.append(window)
                metadata.append(
                    SampleMetadata(
                        sample_id=f"{bearing_id}-{path.stem}-w{window_index:04d}",
                        source_type="public_real",
                        fault_origin=fault_origin,
                        source_dataset="Paderborn_Bearing_DataCenter",
                        source_version="official-bearing-archive",
                        raw_record_id=raw_record_id,
                        group_id=group_id,
                        condition_id=condition_id,
                        fs_hz=fs_hz,
                        n_samples=window_size,
                        units="acceleration_native_units",
                        label_binary=label,
                        label_condition=label_condition,
                        operating_cond={
                            **condition,
                            "bearing_id": bearing_id,
                            "channel": "vibration_1",
                            "measurement_file": raw_record_id,
                        },
                        created_at=stamp,
                    )
                )
            records.append(
                PaderbornFileRecord(
                    bearing_id=bearing_id,
                    path=str(path),
                    sha256=_sha256(path),
                    n_raw_samples=len(signal),
                    fs_hz=fs_hz,
                    channel="vibration_1",
                    condition_id=condition_id,
                    label_binary=label,
                    label_condition=label_condition,
                    group_id=group_id,
                )
            )
    return PaderbornDataset(
        SampleBatch(np.asarray(signals), metadata), tuple(records), condition_id, tuple(measurement_indices)
    )


def make_paderborn_bearing_split(
    batch: SampleBatch, *, k: int, split_seed: int, subset_seed: int
) -> ProtocolSplit:
    """Bearing-disjoint split with two test fault groups and k train fault groups."""
    healthy = sorted({m.group_id for m in batch.metadata if m.label_binary == 0})
    faults = sorted({m.group_id for m in batch.metadata if m.label_binary == 1})
    if len(healthy) < 4 or len(faults) < 5:
        raise ValueError("Paderborn split needs at least four healthy and five fault groups")
    rng = np.random.default_rng(split_seed)
    subset_rng = np.random.default_rng(subset_seed)
    rng.shuffle(healthy)
    rng.shuffle(faults)
    test_groups = set(healthy[:1] + faults[:2])
    val_groups = set(healthy[1:2] + faults[2:3])
    remaining_faults = faults[3:]
    if k > len(remaining_faults):
        raise ValueError(f"k={k} exceeds available Paderborn train fault groups={len(remaining_faults)}")
    subset_rng.shuffle(remaining_faults)
    selected_faults = tuple(sorted(remaining_faults[:k]))
    train_groups = set(healthy[2:]) | set(selected_faults)
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
        split_mode="bearing_disjoint",
    )
