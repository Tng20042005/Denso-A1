from __future__ import annotations

import hashlib
import json

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier

from denso_a1.eval.features import extract_features
from denso_a1.eval.metrics import classification_metrics
from denso_a1.schema import SampleBatch


def _hash_array(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    return hashlib.sha256(array.tobytes()).hexdigest()


def _hash_strings(values: list[str]) -> str:
    payload = json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def evaluate_with_trace(
    train: SampleBatch,
    test: SampleBatch,
    *,
    fs_hz: float,
    seed: int,
    one_class: bool = False,
) -> tuple[dict[str, float], dict[str, object]]:
    x_train = extract_features(train.signals, fs_hz)
    x_test = extract_features(test.signals, fs_hz)
    if one_class:
        normal = x_train[train.labels == 0]
        model = IsolationForest(n_estimators=100, contamination="auto", random_state=seed)
        model.fit(normal)
        scores = -model.score_samples(x_test)
    else:
        if len(np.unique(train.labels)) < 2:
            raise ValueError("supervised evaluator requires both classes")
        model = RandomForestClassifier(
            n_estimators=120, class_weight="balanced", random_state=seed, min_samples_leaf=2, n_jobs=1
        )
        model.fit(x_train, train.labels)
        scores = model.predict_proba(x_test)[:, 1]
    metrics = classification_metrics(test.labels, scores)
    threshold = float(np.quantile(scores, 0.5))
    predictions = (scores >= threshold).astype(np.int8)
    trace = {
        "test_count": len(test.metadata),
        "test_sample_id_hash": _hash_strings([item.sample_id for item in test.metadata]),
        "test_label_hash": _hash_array(test.labels),
        "score_hash": _hash_array(np.asarray(scores, dtype=np.float64)),
        "prediction_hash": _hash_array(predictions),
        "threshold": threshold,
    }
    return metrics, trace


def evaluate(
    train: SampleBatch,
    test: SampleBatch,
    *,
    fs_hz: float,
    seed: int,
    one_class: bool = False,
) -> dict[str, float]:
    metrics, _ = evaluate_with_trace(train, test, fs_hz=fs_hz, seed=seed, one_class=one_class)
    return metrics
