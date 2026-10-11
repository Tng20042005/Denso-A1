from __future__ import annotations

from collections import Counter
from typing import Any

from denso_a1.schema import SampleBatch


def leakage_audit(train: SampleBatch, val: SampleBatch, test: SampleBatch) -> dict[str, Any]:
    train_groups = set(train.groups)
    val_groups = set(val.groups)
    test_groups = set(test.groups)
    overlaps = {
        "train_val": sorted(train_groups & val_groups),
        "train_test": sorted(train_groups & test_groups),
        "val_test": sorted(val_groups & test_groups),
    }
    parent_train_only = all(
        parent_group in train_groups
        for item in train.metadata
        if item.source_type == "generated"
        for parent_group in item.parent_group_ids
    )
    ids = [m.sample_id for m in train.metadata + val.metadata + test.metadata]
    result = {
        "group_overlap": overlaps,
        "group_overlap_pass": not any(overlaps.values()),
        "duplicate_sample_ids": [item for item, count in Counter(ids).items() if count > 1],
        "parent_train_only": parent_train_only,
        "pass": not any(overlaps.values()) and parent_train_only and len(ids) == len(set(ids)),
    }
    return result


def budget_audit(real_train: SampleBatch, augmented_train: SampleBatch, *, expected_total: int) -> dict[str, Any]:
    total = len(augmented_train.signals)
    return {
        "real_train_count": len(real_train.signals),
        "augmented_train_count": total,
        "expected_total": expected_total,
        "pass": total == expected_total,
    }
