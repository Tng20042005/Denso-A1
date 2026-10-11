from __future__ import annotations

from typing import Any

from denso_a1.schema import SampleBatch


def public_real_test_audit(test: SampleBatch) -> dict[str, Any]:
    source_types = sorted({item.source_type for item in test.metadata})
    fault_groups = sorted({item.group_id for item in test.metadata if item.label_binary == 1})
    generated_ids = [item.sample_id for item in test.metadata if item.source_type == "generated"]
    return {
        "source_types": source_types,
        "test_only_measured_public_real": source_types == ["public_real"],
        "fault_group_count": len(fault_groups),
        "fault_groups": fault_groups,
        "has_real_faults": bool(fault_groups),
        "generated_sample_ids": generated_ids,
        "pass": source_types == ["public_real"] and bool(fault_groups) and not generated_ids,
    }
