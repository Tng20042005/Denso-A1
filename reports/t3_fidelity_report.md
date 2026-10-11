# T3 fidelity report

Fidelity is measured on train/validation fault populations only; final-test labels and signals are not used for this diagnostic.

The frozen gate requires C2ST ROC-AUC <= 0.95, PSD JS <= 0.25, PSD cosine >= 0.65, envelope-anchor drift <= 50 Hz, NN ratio >= 0.25 and no exact signal-hash overlap.

See `reports/t3_benchmark/raw_metrics.json` for full feature vectors and per-sample provenance.

| k | seed | partition | C2ST ROC-AUC | PSD JS | PSD cosine | anchor drift Hz | NN ratio | gate |
|---:|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 0 | train_fault | 0.6943 | 0.0198 | 0.9552 | 0.00 | 0.000 | REJECT |
| 1 | 0 | validation_fault | 0.9980 | 0.0845 | 0.7269 | 0.00 | 1.537 | REJECT |
| 2 | 0 | train_fault | 0.8721 | 0.0742 | 0.8541 | 13.67 | 0.000 | REJECT |
| 2 | 0 | validation_fault | 0.9971 | 0.1256 | 0.7188 | 13.67 | 1.403 | REJECT |
| 1 | 1 | train_fault | 0.6484 | 0.0145 | 0.9662 | 0.00 | 0.000 | REJECT |
| 1 | 1 | validation_fault | 0.9990 | 0.0811 | 0.7379 | 0.00 | 1.577 | REJECT |
| 2 | 1 | train_fault | 0.8359 | 0.0699 | 0.8500 | 2.44 | 0.000 | REJECT |
| 2 | 1 | validation_fault | 0.9990 | 0.1293 | 0.6819 | 2.44 | 1.341 | REJECT |
| 1 | 2 | train_fault | 0.7397 | 0.0178 | 0.9582 | 0.00 | 0.000 | REJECT |
| 1 | 2 | validation_fault | 1.0000 | 0.0777 | 0.7606 | 0.00 | 1.555 | REJECT |
| 2 | 2 | train_fault | 0.7959 | 0.0647 | 0.8604 | 7.32 | 0.000 | REJECT |
| 2 | 2 | validation_fault | 0.9980 | 0.1202 | 0.7072 | 7.32 | 1.304 | REJECT |
| 1 | 3 | train_fault | 0.7129 | 0.0169 | 0.9625 | 0.00 | 0.000 | REJECT |
| 1 | 3 | validation_fault | 1.0000 | 0.0789 | 0.7457 | 0.00 | 1.561 | REJECT |
| 2 | 3 | train_fault | 0.8125 | 0.0470 | 0.9172 | 7.32 | 0.000 | REJECT |
| 2 | 3 | validation_fault | 0.9990 | 0.1009 | 0.7532 | 7.32 | 1.472 | REJECT |
| 1 | 4 | train_fault | 0.7139 | 0.0221 | 0.9477 | 0.00 | 0.000 | REJECT |
| 1 | 4 | validation_fault | 1.0000 | 0.0787 | 0.7595 | 0.00 | 1.556 | REJECT |
| 2 | 4 | train_fault | 0.8760 | 0.0694 | 0.8430 | 5.37 | 0.000 | REJECT |
| 2 | 4 | validation_fault | 0.9990 | 0.1167 | 0.7264 | 5.37 | 1.310 | REJECT |
