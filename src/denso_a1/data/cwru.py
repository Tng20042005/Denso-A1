from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from denso_a1.data.simulated import ProtocolSplit
from denso_a1.schema import SampleBatch, SampleMetadata

# Official CWRU 12 kHz registry used for this first public-real run.
CWRU_FILE_REGISTRY: dict[int, dict[str, object]] = {
    97: {"label": 0, "condition": "normal", "load_hp": 0},
    98: {"label": 0, "condition": "normal", "load_hp": 1},
    99: {"label": 0, "condition": "normal", "load_hp": 2},
    100: {"label": 0, "condition": "normal", "load_hp": 3},
    105: {"label": 1, "condition": "inner_007", "load_hp": 0},
    106: {"label": 1, "condition": "inner_007", "load_hp": 1},
    107: {"label": 1, "condition": "inner_007", "load_hp": 2},
    108: {"label": 1, "condition": "inner_007", "load_hp": 3},
    118: {"label": 1, "condition": "ball_007", "load_hp": 0},
    119: {"label": 1, "condition": "ball_007", "load_hp": 1},
    120: {"label": 1, "condition": "ball_007", "load_hp": 2},
    121: {"label": 1, "condition": "ball_007", "load_hp": 3},
    130: {"label": 1, "condition": "outer_007_6", "load_hp": 0},
    131: {"label": 1, "condition": "outer_007_6", "load_hp": 1},
    132: {"label": 1, "condition": "outer_007_6", "load_hp": 2},
    133: {"label": 1, "condition": "outer_007_6", "load_hp": 3},
}


@dataclass(frozen=True)
class CWRUFileRecord:
    file_id: int
    path: str
    sha256: str
    n_raw_samples: int
    fs_hz: float
    channel: str
    rpm: float
    label_binary: int
    label_condition: str
    group_id: str


@dataclass(frozen=True)
class CWRUDataset:
    batch: SampleBatch
    files: tuple[CWRUFileRecord, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_de_signal(path: Path, file_id: int, channel: str) -> tuple[np.ndarray, float]:
    mat = loadmat(path)
    prefix = f"X{file_id:03d}_"
    key = f"{prefix}{channel}_time"
    if key not in mat:
        available = sorted(k for k in mat if k.startswith(prefix))
        raise KeyError(f"{path.name}: missing {key}; available={available}")
    rpm_key = f"X{file_id:03d}RPM"
    rpm = float(np.asarray(mat[rpm_key]).reshape(-1)[0]) if rpm_key in mat else float("nan")
    signal = np.asarray(mat[key], dtype=np.float64).reshape(-1)
    if not np.all(np.isfinite(signal)):
        raise ValueError(f"{path.name}: signal contains non-finite values")
    return signal, rpm


def load_cwru(
    root: str | Path,
    *,
    fs_hz: float = 12_000.0,
    window_size: int = 4096,
    step: int = 4096,
    channel: str = "DE",
    file_ids: tuple[int, ...] | None = None,
) -> CWRUDataset:
    """Load official CWRU Matlab files into the project provenance schema.

    Windowing is non-overlapping by default. Every window from one raw Matlab
    file shares one group, so group-level splitting prevents raw-record leakage.
    """
    root_path = Path(root)
    selected = file_ids or tuple(sorted(CWRU_FILE_REGISTRY))
    signals: list[np.ndarray] = []
    metadata: list[SampleMetadata] = []
    file_records: list[CWRUFileRecord] = []
    stamp = datetime.now(UTC).isoformat()
    for file_id in selected:
        if file_id not in CWRU_FILE_REGISTRY:
            raise KeyError(f"file_id={file_id} is not in the frozen CWRU registry")
        path = root_path / f"{file_id}.mat"
        if not path.exists():
            raise FileNotFoundError(path)
        spec = CWRU_FILE_REGISTRY[file_id]
        signal, rpm = _load_de_signal(path, file_id, channel)
        if not np.isfinite(rpm):
            rpm_by_load = {0: 1797.0, 1: 1772.0, 2: 1750.0, 3: 1730.0}
            rpm = rpm_by_load[int(spec["load_hp"])]
        group_id = f"cwru-file-{file_id:03d}"
        starts = range(0, len(signal) - window_size + 1, step)
        windows = [signal[start : start + window_size] for start in starts]
        if not windows:
            raise ValueError(f"{path.name}: signal shorter than window_size={window_size}")
        label = int(spec["label"])
        condition = str(spec["condition"])
        for window_index, window in enumerate(windows):
            signals.append(window)
            metadata.append(
                SampleMetadata(
                    sample_id=f"{group_id}-w{window_index:04d}",
                    source_type="public_real",
                    fault_origin="seeded_physical" if label else "unknown",
                    source_dataset="CWRU_Bearing_Data_Center",
                    source_version="official-12k-download",
                    raw_record_id=f"{file_id:03d}.mat",
                    group_id=group_id,
                    condition_id=f"load-{spec['load_hp']}hp",
                    fs_hz=fs_hz,
                    n_samples=window_size,
                    units="acceleration_native_units",
                    label_binary=label,
                    label_condition=condition,
                    operating_cond={"motor_load_hp": spec["load_hp"], "rpm": rpm, "channel": channel},
                    created_at=stamp,
                )
            )
        file_records.append(
            CWRUFileRecord(
                file_id=file_id,
                path=str(path),
                sha256=_sha256(path),
                n_raw_samples=len(signal),
                fs_hz=fs_hz,
                channel=channel,
                rpm=rpm,
                label_binary=label,
                label_condition=condition,
                group_id=group_id,
            )
        )
    return CWRUDataset(SampleBatch(np.asarray(signals), metadata), tuple(file_records))


def make_cwru_cross_load_split(
    batch: SampleBatch,
    *,
    k: int,
    split_seed: int,
    subset_seed: int,
    heldout_load_hp: int | None = None,
) -> ProtocolSplit:
    """Hold out one complete CWRU load for test and the next load for validation.

    Fault groups selected for training are sampled only from the remaining
    loads. This makes the test condition a load holdout while preserving the
    same group-level and few-shot semantics as the random-group protocol.
    """
    loads = sorted({int(item.operating_cond["motor_load_hp"]) for item in batch.metadata})
    if len(loads) < 4:
        raise ValueError("cross-load protocol requires four CWRU load conditions")
    if heldout_load_hp is None:
        heldout_load_hp = loads[split_seed % len(loads)]
    if heldout_load_hp not in loads:
        raise ValueError(f"unknown heldout_load_hp={heldout_load_hp}; available={loads}")
    holdout_index = loads.index(heldout_load_hp)
    val_load_hp = loads[(holdout_index + 1) % len(loads)]
    train_loads = set(loads) - {heldout_load_hp, val_load_hp}

    group_items: dict[str, list] = {}
    for index, item in enumerate(batch.metadata):
        group_items.setdefault(item.group_id, []).append((index, item))
    group_load = {
        group_id: int(items[0][1].operating_cond["motor_load_hp"])
        for group_id, items in group_items.items()
    }
    group_label = {group_id: items[0][1].label_binary for group_id, items in group_items.items()}
    test_groups = {group_id for group_id, load in group_load.items() if load == heldout_load_hp}
    val_groups = {group_id for group_id, load in group_load.items() if load == val_load_hp}
    train_candidate_groups = {group_id for group_id, load in group_load.items() if load in train_loads}
    fault_candidates = sorted(group_id for group_id in train_candidate_groups if group_label[group_id] == 1)
    if k > len(fault_candidates):
        raise ValueError(f"k={k} exceeds cross-load fault groups={len(fault_candidates)}")
    subset_rng = np.random.default_rng(subset_seed)
    subset_rng.shuffle(fault_candidates)
    selected_faults = tuple(sorted(fault_candidates[:k]))
    train_groups = {
        group_id
        for group_id in train_candidate_groups
        if group_label[group_id] == 0 or group_id in selected_faults
    }
    train = np.asarray([index for index, item in enumerate(batch.metadata) if item.group_id in train_groups], dtype=int)
    val = np.asarray([index for index, item in enumerate(batch.metadata) if item.group_id in val_groups], dtype=int)
    test = np.asarray([index for index, item in enumerate(batch.metadata) if item.group_id in test_groups], dtype=int)
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
        split_mode="cross_load",
        heldout_load_hp=heldout_load_hp,
        val_load_hp=val_load_hp,
    )
