from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score


def recall_at_fixed_fpr(y_true: np.ndarray, scores: np.ndarray, fpr: float = 0.10) -> float:
    negatives = scores[y_true == 0]
    if len(negatives) == 0 or np.sum(y_true == 1) == 0:
        return float("nan")
    threshold = float(np.quantile(negatives, 1 - fpr))
    return float(np.mean(scores[y_true == 1] >= threshold))


def classification_metrics(y_true: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    threshold = float(np.quantile(scores, 0.5))
    predictions = (scores >= threshold).astype(int)
    result = {
        "pr_auc": float(average_precision_score(y_true, scores)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "recall_at_fpr_10": recall_at_fixed_fpr(y_true, scores),
    }
    result["roc_auc"] = float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) > 1 else float("nan")
    return result
