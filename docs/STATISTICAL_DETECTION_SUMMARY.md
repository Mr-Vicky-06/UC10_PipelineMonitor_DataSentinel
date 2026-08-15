# Statistical Detection Summary

## Methodology
- **Algorithm**: Rolling Median + Median Absolute Deviation (MAD).
- **Leakage Prevention**: Baseline exclusively uses trailing data (`T-7` to `T-1`). Current observation is excluded. Future data is strictly ignored.
- **Scoring**: Robust Z-Score scaling applied (`0.6745`).

## Configuration
- **Historical Window**: 7 days.
- **Anomaly Threshold**: 3.5.
- **Metrics Analyzed**: 18 numeric behavioral features extracted during the Feature Engineering phase (including volume, quality, and simulated operational metrics).

## Edge Case Policies
- **Cold-Start Policy**: The first 7 days are ignored for anomaly scoring. They are explicitly tagged with a severity of `INSUFFICIENT_HISTORY`.
- **Zero-MAD Policy**: 
  - Division by zero prevented.
  - If a metric historically flatlines (MAD=0) but the current value spikes, it is scored as a distribution shift and flagged.
  - If it remains flatlined (Current == Median), it is assigned Z=0.0.

## Results
- **Clean Baseline**: Evaluated perfectly. Minor natural anomalies tagged, largely normal distribution.
- **Injected Anomaly**: 40% reduction in PDE/Claim volume successfully detected on day 50 as a `DECREASE` with `LOW` severity.
- **Performance**: High recall for significant shifts on high-volume metrics (like PDE). Low-volume metrics (like inpatient claims) require larger absolute shifts to break the MAD threshold.

## Limitations
- Evaluates each metric independently. Will miss multivariate interactions (e.g. Metric A drops while Metric B drops, which may be anomalous together but normal individually). 
- Sensitive to extreme sparsity on low-volume metrics.

## Next Step
- Proceed to Phase 4: **Isolation Forest** (Multivariate ML Detection) to catch complex cross-metric anomalies.
