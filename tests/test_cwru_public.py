import numpy as np
from scipy.io import savemat

from denso_a1.data.cwru import load_cwru, make_cwru_cross_load_split
from denso_a1.data.paderborn import make_paderborn_bearing_split
from denso_a1.data.preprocess import SignalPreprocessor
from denso_a1.data.public_split import public_real_test_audit
from denso_a1.data.simulated import make_protocol_split
from denso_a1.eval.audits import leakage_audit
from denso_a1.public_benchmark import aggregate_public_results
from denso_a1.schema import SampleBatch, SampleMetadata


def test_cwru_loader_and_public_test_audit(tmp_path):
    file_ids = (97, 98, 99, 100, 105, 106, 107, 108)
    for file_id in file_ids:
        signal = np.linspace(-1, 1, 2048) + file_id / 1000
        savemat(tmp_path / f"{file_id}.mat", {f"X{file_id:03d}_DE_time": signal[:, None], f"X{file_id:03d}RPM": [[1797]]})
    dataset = load_cwru(tmp_path, window_size=1024, file_ids=file_ids)
    split = make_protocol_split(dataset.batch, k=1, split_seed=1, subset_seed=2)
    train = dataset.batch.subset(split.train)
    test = dataset.batch.subset(split.test)
    processed = SignalPreprocessor().fit(train).transform(dataset.batch)
    assert processed.signals.shape == dataset.batch.signals.shape
    assert public_real_test_audit(test)["pass"] is True
    assert leakage_audit(processed.subset(split.train), processed.subset(split.val), processed.subset(split.test))["pass"] is True


def test_cwru_cross_load_split_holds_out_complete_load(tmp_path):
    file_ids = tuple(range(97, 101)) + tuple(range(105, 109)) + tuple(range(118, 122)) + tuple(range(130, 134))
    for file_id in file_ids:
        signal = np.linspace(-1, 1, 2048) + file_id / 1000
        savemat(tmp_path / f"{file_id}.mat", {f"X{file_id:03d}_DE_time": signal[:, None], f"X{file_id:03d}RPM": [[1797]]})
    dataset = load_cwru(tmp_path, window_size=1024, file_ids=file_ids)
    split = make_cwru_cross_load_split(dataset.batch, k=1, split_seed=0, subset_seed=2)
    test_loads = {dataset.batch.metadata[int(i)].operating_cond["motor_load_hp"] for i in split.test}
    train_loads = {dataset.batch.metadata[int(i)].operating_cond["motor_load_hp"] for i in split.train}
    assert test_loads == {0}
    assert not test_loads & train_loads
    assert split.split_mode == "cross_load"


def test_public_aggregate_reports_pr_auc_and_f1():
    rows = []
    for seed in range(5):
        for method, pr_auc, f1 in (("E0", 0.8, 0.6), ("E1", 0.85, 0.65), ("E2", 0.9, 0.7)):
            rows.append(
                {
                    "k_fault_groups": 1,
                    "method": method,
                    "model_seed": seed,
                    "split_mode": "random_group",
                    "metrics": {"pr_auc": pr_auc, "f1": f1},
                    "public_real_test_audit": {"pass": True},
                    "leakage_audit": {"pass": True},
                    "budget_audit": {"pass": True},
                    "training_difference_audit": {"pass": True},
                }
            )
    summary = aggregate_public_results(rows)
    assert summary["experiment"] == "E4_k_sweep"
    assert summary["k_values"] == [1]
    assert set(summary["groups"]["k=1:E2"]["metrics"]) == {"pr_auc", "f1"}
    assert set(summary["paired_deltas"]["k=1:E2-E0"]["metrics"]) == {"pr_auc", "f1"}


def test_paderborn_split_is_bearing_disjoint():
    groups = [(f"healthy-{i}", 0) for i in range(4)] + [(f"fault-{i}", 1) for i in range(5)]
    metadata = [
        SampleMetadata(
            sample_id=f"{group}-sample",
            source_type="public_real",
            fault_origin="accelerated_degradation" if label else "unknown",
            source_dataset="Paderborn_Bearing_DataCenter",
            source_version="test",
            raw_record_id=f"{group}.mat",
            group_id=group,
            condition_id="N15_M07_F10",
            label_binary=label,
        )
        for group, label in groups
    ]
    batch = SampleBatch(np.zeros((len(metadata), 8)), metadata)
    split = make_paderborn_bearing_split(batch, k=2, split_seed=0, subset_seed=1)
    train_groups = {metadata[int(i)].group_id for i in split.train}
    val_groups = {metadata[int(i)].group_id for i in split.val}
    test_groups = {metadata[int(i)].group_id for i in split.test}
    assert split.split_mode == "bearing_disjoint"
    assert not train_groups & val_groups & test_groups
    assert not train_groups & val_groups
    assert not train_groups & test_groups
    assert not val_groups & test_groups
