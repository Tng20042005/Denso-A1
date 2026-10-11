from __future__ import annotations

import numpy as np

from denso_a1.schema import SampleBatch, SampleMetadata


def t1_augment(parents: SampleBatch, parent_indices: np.ndarray | list[int], *, seed: int) -> SampleBatch:
    """Budget-matched, non-physics baseline: jitter, scaling and circular shift."""
    rng = np.random.default_rng(seed)
    outputs: list[np.ndarray] = []
    metadata: list[SampleMetadata] = []
    for ordinal, parent_index in enumerate(np.asarray(parent_indices, dtype=int)):
        parent = parents.metadata[int(parent_index)]
        signal = parents.signals[int(parent_index)]
        scale = float(rng.uniform(0.94, 1.06))
        shift = int(rng.integers(-len(signal) // 20, len(signal) // 20 + 1))
        augmented = np.roll(signal * scale, shift) + rng.normal(0, 0.015 * np.std(signal), len(signal))
        outputs.append(augmented)
        metadata.append(
            SampleMetadata(
                sample_id=f"{parent.sample_id}-t1-{ordinal:04d}",
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
                n_samples=len(signal),
                label_binary=parent.label_binary,
                label_condition="simple_augmentation",
                generator="t1_simple_augmentation",
                generator_version="0.1",
                generator_seed=seed,
                operating_cond=parent.operating_cond.copy(),
                created_at=parent.created_at,
            )
        )
    return SampleBatch(np.asarray(outputs), metadata)
