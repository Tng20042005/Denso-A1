from __future__ import annotations

import numpy as np
from scipy.signal import welch


def extract_features(signals: np.ndarray, fs_hz: float) -> np.ndarray:
    values = np.asarray(signals, dtype=float)
    x = values - np.mean(values, axis=1, keepdims=True)
    rms = np.sqrt(np.mean(x**2, axis=1))
    std = np.std(x, axis=1) + 1e-12
    crest = np.max(np.abs(x), axis=1) / (rms + 1e-12)
    kurtosis = np.mean((x / std[:, None]) ** 4, axis=1)
    freqs, psd = welch(x, fs=fs_hz, nperseg=min(256, x.shape[1]), axis=1)
    bands = [(0, 40), (40, 100), (100, 180), (180, fs_hz / 2)]
    band_powers = []
    for lo, hi in bands:
        mask = (freqs >= lo) & (freqs < hi)
        band_powers.append(np.trapezoid(psd[:, mask], freqs[mask], axis=1))
    return np.column_stack([rms, std, crest, kurtosis, *band_powers])
