# DENSO data onboarding runbook

1. Store factory data outside this repository and confirm NDA/usage rules.
2. Profile format, sampling rate, channels, units, missingness, saturation,
   and dead channels.
3. Assign immutable `raw_record_id` and `group_id`; document label provenance.
4. Freeze a real test group list before tuning preprocessing or T0 parameters.
5. Choose scenario 1 (normal + few faults), scenario 2 (normal only), or
   scenario 3 (no target data).
6. Fit preprocessing only on train; calibrate T0 only on train/validation.
7. Re-run E0/E1/E2/E4 with the same audit and budget rules.
8. Obtain domain review before naming any mechanism as a physical fault.

No generated sample may have a validation/test parent. No factory data should
be committed to a public repository.
