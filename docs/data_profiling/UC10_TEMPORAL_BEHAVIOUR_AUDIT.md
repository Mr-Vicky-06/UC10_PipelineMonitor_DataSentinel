# UC10 Temporal Behaviour Audit

## 1. Objective
To understand normal longitudinal behaviour across the Claims and PDE datasets on daily pipeline windows, distinguishing expected variance from true anomalies.

## 2. Normal Behaviour Profile
Based on the `uc10_feature_matrix.parquet` aggregation, normal behaviour across the sample windows (approx. 2015-2026) demonstrates:

- **Volume Fluctuations:** Daily claim and PDE counts exhibit high volatility depending on the day of the week and holiday schedules. A single day dropping by 15-20% may be entirely normal weekend behavior.
- **Ratio Stability:** The `claim_pde_ratio` generally hovers around 0.12, indicating a relatively stable relationship between medical events and pharmacy events within this synthesized sample.
- **Cost Variances:** `median_rx_cost` and `median_claim_amount` show extreme right-tail skewness on a line-by-line basis, but median aggregations per window stabilize this noise effectively.

## 3. Detecting Anomalies vs Expected Variance
Because standard deviations are heavily skewed by weekend drops, the pipeline's use of **Rolling Median Absolute Deviation (MAD)** is mathematically justified over standard Z-Scores. 

### What is anomalous?
- A **Volume Drop** > 40% (exceeding 3.5 MAD) on a historically high-volume weekday.
- A sudden shift in the `claim_pde_ratio`, such as Claims arriving normally while PDE drops to zero (indicating a specific upstream transfer failure, not a holiday).

### What is NOT anomalous?
- Gradual volume changes over months.
- Occasional single-day spikes within 2 MAD.
- Zero data quality violations on the "clean" dataset.

## 4. Conclusion
True temporal anomalies in this dataset require looking beyond simple thresholds. The combination of rolling MAD (for univariate spikes/drops) and Isolation Forest (for multivariate ratios) is necessary to avoid high false-positive alert rates.
