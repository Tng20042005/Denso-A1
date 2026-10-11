from denso_a1.data.simulated import make_simulated_dataset
from denso_a1.generators.physics import T0Generator


def test_generated_samples_keep_parent_provenance():
    corpus = make_simulated_dataset(normal_groups=2, fault_groups=2, windows_per_group=1, seed=8)
    generated = T0Generator().generate_from_parents(corpus, [0, 1], seed=4, split_seed=9)
    assert all(item.source_type == "generated" for item in generated.metadata)
    assert all(item.fault_origin == "algorithmic_injection" for item in generated.metadata)
    assert all(len(item.parent_ids) == 1 and len(item.parent_group_ids) == 1 for item in generated.metadata)
