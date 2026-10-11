from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

import numpy as np

from denso_a1.schema import SampleBatch


@dataclass
class SignalPreprocessor:
    """Train-only global centering/scaling for measured signals."""

    mean_: float | None = None
    scale_: float | None = None

    def fit(self, train: SampleBatch) -> SignalPreprocessor:
        if not train.metadata or any(item.split_role not in {"train", "unassigned"} for item in train.metadata):
            raise ValueError("preprocessor must be fit on train-role samples only")
        self.mean_ = float(np.mean(train.signals))
        self.scale_ = float(np.std(train.signals))
        if not np.isfinite(self.scale_) or self.scale_ < 1e-12:
            raise ValueError("train signal scale is invalid")
        return self

    def transform(self, batch: SampleBatch) -> SampleBatch:
        if self.mean_ is None or self.scale_ is None:
            raise RuntimeError("fit must be called before transform")
        return SampleBatch((batch.signals - self.mean_) / self.scale_, deepcopy(batch.metadata))

    def fit_transform(self, train: SampleBatch) -> SampleBatch:
        return self.fit(train).transform(train)
