# Experiments

The command-line benchmark writes immutable-per-run JSON records to
`reports/benchmark/raw_metrics.json`. Each row includes the seed taxonomy,
selected fault groups, source type, metrics, leakage audit, and budget audit.

When a licensed public dataset is added, create one subdirectory per frozen
dataset/protocol and preserve the test group manifest before changing the
generator or evaluator.
