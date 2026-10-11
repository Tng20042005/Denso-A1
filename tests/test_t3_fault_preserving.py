import numpy as np

from denso_a1.generators.t3_fault_preserving import T3Config, apply_policy
from denso_a1.schema import SampleBatch, SampleMetadata


def _batch(label: int, group: str, n: int = 4, length: int = 128) -> SampleBatch:
    metadata = [
        SampleMetadata(
            sample_id=f"{group}-{i}",
            source_type="public_real",
            fault_origin="accelerated_degradation",
            source_dataset="test",
            source_version="test",
            raw_record_id="test",
            group_id=group,
            condition_id="N15_M07_F10",
            n_samples=length,
            label_binary=label,
            operating_cond={"speed_rpm": 1500, "torque_nm": 0.7, "radial_force_n": 1000},
        )
        for i in range(n)
    ]
    signals = np.random.default_rng(4).normal(size=(n, length))
    return SampleBatch(signals, metadata)


def test_t3_policy_preserves_parent_provenance_and_shape() -> None:
    faults = _batch(1, "fault-group")
    normal = _batch(0, "normal-group")
    generated = apply_policy(
        faults,
        normal,
        [0, 1],
        policy=("amplitude", "shift", "noise", "phase", "spectral", "envelope"),
        seed=9,
        config=T3Config(),
    )
    assert generated.signals.shape == (2, 128)
    assert all(item.source_type == "generated" for item in generated.metadata)
    assert all(item.parent_ids for item in generated.metadata)
    assert all(item.parent_group_ids == ["fault-group"] for item in generated.metadata)
    assert all(item.generator == "t3_fault_preserving_augmentation" for item in generated.metadata)
