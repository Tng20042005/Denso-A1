from denso_a1.data.simulated import make_protocol_split, make_simulated_dataset
from denso_a1.eval.audits import leakage_audit


def test_group_split_has_no_overlap_and_k_counts_groups():
    corpus = make_simulated_dataset(seed=3)
    split = make_protocol_split(corpus, k=1, split_seed=4, subset_seed=5)
    assert len(split.selected_fault_groups) == 1
    assert set(split.train_groups).isdisjoint(split.val_groups)
    assert set(split.train_groups).isdisjoint(split.test_groups)
    audit = leakage_audit(corpus.subset(split.train), corpus.subset(split.val), corpus.subset(split.test))
    assert audit["pass"] is True
