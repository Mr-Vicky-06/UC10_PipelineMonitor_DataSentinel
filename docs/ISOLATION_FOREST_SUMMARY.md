# Isolation Forest Summary

## 1. Objective
Implement a multivariate machine learning anomaly detector using Isolation Forest to identify unusual combinations of pipeline and data behavior, fulfilling the final component of the UC10 Hybrid Anomaly Detection architecture.

## 2. Feature Set
- **Included**: 18 numerical behavioral and operational features (e.g., `pde_count`, `null_rate`, `claim_pde_ratio`, `backlog`).
- **Excluded**: Raw identifiers (`BENE_ID`, `CLM_ID`), temporal indices (`feature_date`), and anomaly labels.

## 3. Temporal Splitting
- **Training Period**: 2015-02-25 to 2020-10-07 (70% split). The model only fits on this historical data.
- **Testing Period**: 2020-10-08 to 2023-03-03 (30% split). The model predicts unseen data in this period.

## 4. Model Configuration
- **Algorithm**: `sklearn.ensemble.IsolationForest`
- **Contamination**: `0.02` (Configurable via `configs/anomaly_config.yaml`). This forces the tree path length threshold to bound the top 2% of the training dataset.

## 5. Detection Results & Controlled Anomaly
- Evaluated cleanly on the baseline.
- An extreme multivariate operational failure (dropping volume while spiking backlog and failure rates) was injected into a holdout testing window.
- The Isolation Forest successfully detected the abnormal feature profile (Score < 0) and flagged it.

## 6. Comparison with MAD
- **MAD** is optimal for fast, univariate detection of volume drops or spikes on a rolling window.
- **Isolation Forest** is optimal for identifying days where individual metrics might hover near their standard deviations, but their *combination* is highly irregular.

## 7. Limitations
- **Not Causal**: The model identifies abnormal feature combinations. It does NOT provide a root cause analysis (e.g., it will say "throughput down + backlog up is unusual", not "database connection failed").
- **Simulated Metrics**: The operational metrics used are synthetic and deterministic. In production, real noisy telemetry would require careful hyperparameter tuning.

## 8. Next Step
Proceed to **Phase 5/6: Evidence Fusion**, where the outputs from the DQ rules, the Statistical MAD detector, and this Isolation Forest detector will be combined to generate a final anomaly assessment and severity rating.
