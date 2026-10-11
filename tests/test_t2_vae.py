import numpy as np

from denso_a1.schema import SampleBatch, SampleMetadata
from denso_a1.t2_vae import ConditionalVAE, VAEConfig


def _batch(n: int, length: int = 64) -> SampleBatch:
    metadata = [
        SampleMetadata(
            sample_id=f"sample-{i}",
            source_type="public_real",
            fault_origin="accelerated_degradation",
            source_dataset="test",
            source_version="test",
            raw_record_id="test",
            group_id="group-a",
            condition_id="condition-a",
            n_samples=length,
            label_binary=1,
            operating_cond={"speed_rpm": 1500, "torque_nm": 0.7, "radial_force_n": 1000},
        )
        for i in range(n)
    ]
    return SampleBatch(np.random.default_rng(1).normal(size=(n, length)), metadata)


def test_conditional_vae_fit_and_generate_shape() -> None:
    vae = ConditionalVAE(
        VAEConfig(signal_length=64, hidden_dim=16, latent_dim=4, epochs=2, patience=1, seed=3)
    )
    history = vae.fit(_batch(8), _batch(4))
    generated = vae.generate(n=3, condition_metadata=_batch(4).metadata, source_groups=("group-a",), seed=4)
    assert history
    assert generated.signals.shape == (3, 64)
    assert all(item.generator == "t2_conditional_vae" for item in generated.metadata)
    assert all(item.parent_group_ids == ["group-a"] for item in generated.metadata)
