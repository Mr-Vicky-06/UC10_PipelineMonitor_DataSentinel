# Isolation Forest Evaluation

## 1. Prototype Scope
This evaluation is based on a lightweight MVP implementation of an Isolation Forest using `scikit-learn`, trained strictly on temporal data (70% split). The goal is to prove out the architecture, not to achieve production-grade precision/recall.

## 2. Temporal Splitting
- **Training Set**: 2,045 windows (2015-02-25 to 2020-10-07)
- **Validation/Testing Set**: 877 windows (2020-10-08 to 2023-03-03)
- **Leakage Prevention**: Strictly enforced. The model was trained *only* on the first 70% of the timeline. The injected test anomaly was placed in the 30% holdout set.

## 3. Clean Baseline False-Positive Rate
By setting `contamination=0.02`, the model is configured to flag the top 2% most unusual points *within its training set* as anomalies. When applied to the testing set, it flagged roughly a similar proportion of natural variance as "anomalous". In a production system, these thresholds would be tuned against confirmed incident data.

## 4. Controlled Multivariate Anomaly Test
A severe operational degradation was simulated on a window in the testing set (2022-01-06):
- `claim_count`: Dropped to 1
- `pde_count`: Dropped to 10
- `processing_duration`: Spiked to 500.0s (Max baseline was 148s)
- `backlog`: Spiked to 100 (Max baseline was 15)
- `throughput`: Dropped to 0.0001
- `failure_rate`: Spiked to 45% (Max baseline was 0%)

**Detection Result**: 
- The model successfully flagged this combination as an anomaly (`Prediction = -1`).
- The anomaly score dropped below 0 (`-0.0017`).

## 5. MAD vs Isolation Forest Comparison

| Scenario | DQ Engine | Statistical MAD | Isolation Forest |
|---|:---:|:---:|:---:|
| Missing Beneficiary ID | ✓ | | |
| Duplicate PDE | ✓ | | |
| Invalid Date Format | ✓ | | |
| Referential Failure (Claim without Bene) | ✓ | | |
| Large Volume Drop (Single Metric) | | ✓ | ✓ |
| Multivariate Degradation (e.g., Backlog ↑, Throughput ↓) | | ? | ✓ |

**Conclusion**:
- **Rules (DQ)** detect explicit structural and data-quality violations.
- **MAD** acts as a sensitive tripwire for sharp, single-metric temporal deviations (like sudden volume drops).
- **Isolation Forest** acts as a safety net to catch unusual combinations of features that might individually evade single-metric thresholds.
