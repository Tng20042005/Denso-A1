from pathlib import Path

import numpy as np

from denso_a1.safety_gate_validation import (
    _corrupt_signal,
    _monotonicity,
    _utility_rows,
)


def test_diagnostic_corruptions_preserve_signal_shape() -> None:
    signal = np.sin(np.linspace(0.0, 20.0, 4096))
    for kind in (
        "band_limited_noise",
        "frequency_anchor_shift",
        "spectral_distortion",
        "impulse_sharpening",
        "envelope_distortion",
    ):
        corrupted = _corrupt_signal(signal, kind, 0.5, seed=7)
        assert corrupted.shape == signal.shape
        assert np.all(np.isfinite(corrupted))


def test_monotonicity_reports_consistent_and_mixed_series() -> None:
    consistent = _monotonicity([0.0, 0.2, 0.4, 0.8], increasing=True)
    mixed = _monotonicity([0.0, 0.4, 0.2, 0.8], increasing=True)
    assert consistent["interpretation"] == "consistent"
    assert mixed["interpretation"] == "mixed"


def test_utility_association_contains_frozen_configurations() -> None:
    rows = _utility_rows(Path(__file__).parents[1])
    assert len(rows) == 18
    assert {row["method"] for row in rows} == {
        "T0",
        "T0-v2",
        "T2 conditional-VAE",
        "T3 fault-preserving augmentation",
    }
