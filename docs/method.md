# Method

The pipeline has four explicit stages:

1. Simulated or incoming vibration is represented as a `SampleBatch` with
   provenance metadata.
2. Group-level protocol splitting assigns train/validation/test before any
   generated sample is created.
3. T0 injects a jittered periodic impulse train, damped resonance, amplitude
   modulation, and noise. Nyquist, damping, SNR, and parent-train guards are
   validated.
4. E0/E1/E2 train the same small evaluator family; E4 is the paired `k`-sweep
   over those arms. Reports include PR-AUC, F1, recall at 10% FPR, paired
   deltas, and bootstrap uncertainty.

T0 output is `source_type=generated`, `fault_origin=algorithmic_injection`,
and `label_condition=mechanism_like_injection`. It is deliberately not called
a DENSO fault or a field-observed fault.
