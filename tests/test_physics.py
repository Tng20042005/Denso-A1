import numpy as np
import pytest

from denso_a1.generators.physics import (
    PhysicsConfig,
    T0Generator,
    T0V2Config,
    T0V2Generator,
    bearing_characteristic_frequencies,
    envelope_spectrum,
)


def test_bearing_frequency_formula_is_explicit():
    values = bearing_characteristic_frequencies(20, 8, 0.01, 0.05, 0.0)
    assert values["BPFO"] < values["BPFI"]
    assert values["FTF"] > 0


def test_t0_is_reproducible_and_has_fault_peak():
    signal = np.sin(np.linspace(0, 20 * np.pi, 512))
    generator = T0Generator(PhysicsConfig(f_fault_hz=80, f_res_hz=120))
    first = generator.inject(signal, seed=123)
    second = generator.inject(signal, seed=123)
    assert np.array_equal(first, second)
    frequencies, spectrum = envelope_spectrum(first, 1_000)
    near_fault = (frequencies > 70) & (frequencies < 90)
    assert float(np.max(spectrum[near_fault])) > 0


def test_t0_rejects_aliasing_configuration():
    with pytest.raises(ValueError):
        T0Generator(PhysicsConfig(fs_hz=100, f_fault_hz=60))


def test_t0_v2_is_reproducible_and_uses_frozen_version():
    signal = np.sin(np.linspace(0, 20 * np.pi, 512))
    generator = T0V2Generator(T0V2Config(fs_hz=1_000, f_fault_hz=80, f_res_hz=120))
    first = generator.inject(signal, seed=123)
    second = generator.inject(signal, seed=123)
    assert np.array_equal(first, second)
    assert generator.version == "0.2"
