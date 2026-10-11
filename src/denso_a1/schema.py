from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

SOURCE_TYPES = {"denso_real", "public_real", "simulated", "generated"}
FAULT_ORIGINS = {"field_observed", "accelerated_degradation", "seeded_physical", "algorithmic_injection", "unknown"}


@dataclass
class SampleMetadata:
    sample_id: str
    source_type: str
    fault_origin: str
    source_dataset: str
    source_version: str
    raw_record_id: str
    group_id: str
    condition_id: str | None
    parent_ids: list[str] = field(default_factory=list)
    parent_group_ids: list[str] = field(default_factory=list)
    split_role: str = "unassigned"
    fs_hz: float = 1_000.0
    n_channels: int = 1
    n_samples: int = 0
    units: str = "normalized"
    label_binary: int = 0
    label_condition: str = "normal"
    severity: float | None = None
    generator: str | None = None
    generator_version: str | None = None
    config_hash: str | None = None
    split_seed: int | None = None
    subset_seed: int | None = None
    generator_seed: int | None = None
    operating_cond: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"unsupported source_type={self.source_type}")
        if self.fault_origin not in FAULT_ORIGINS:
            raise ValueError(f"unsupported fault_origin={self.fault_origin}")
        if self.label_binary not in (0, 1):
            raise ValueError("label_binary must be 0 or 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SampleBatch:
    signals: np.ndarray
    metadata: list[SampleMetadata]

    def __post_init__(self) -> None:
        self.signals = np.asarray(self.signals, dtype=np.float64)
        if self.signals.ndim != 2:
            raise ValueError("signals must have shape (n_samples, signal_length)")
        if len(self.metadata) != len(self.signals):
            raise ValueError("metadata and signals must have equal length")
        for item in self.metadata:
            if item.n_samples not in (0, self.signals.shape[1]):
                raise ValueError("metadata n_samples does not match signal length")
            item.n_samples = self.signals.shape[1]

    @property
    def labels(self) -> np.ndarray:
        return np.asarray([m.label_binary for m in self.metadata], dtype=np.int64)

    @property
    def groups(self) -> np.ndarray:
        return np.asarray([m.group_id for m in self.metadata], dtype=object)

    def subset(self, indices: np.ndarray | list[int]) -> SampleBatch:
        idx = np.asarray(indices, dtype=int)
        return SampleBatch(self.signals[idx], [self.metadata[int(i)] for i in idx])

    def with_split(self, role: str, indices: np.ndarray | list[int], split_seed: int) -> None:
        for i in np.asarray(indices, dtype=int):
            self.metadata[int(i)].split_role = role
            self.metadata[int(i)].split_seed = split_seed
