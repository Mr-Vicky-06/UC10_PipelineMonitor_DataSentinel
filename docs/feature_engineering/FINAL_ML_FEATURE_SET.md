# Final ML Feature Set

The following 18 features have passed the pre-anomaly audit and are designated as the final ML feature set for Isolation Forest and Statistical Detection. `feature_date` is strictly retained as temporal metadata/index.

### DATA QUALITY
*(Baseline is currently 0, to be activated during anomaly injection)*
- `null_rate`
- `duplicate_rate`
- `claims_null_rate`
- `cross_dataset_mismatch_rate`
- `dq_violation_rate`

### HEALTHCARE DATA VOLUME / BEHAVIOR
- `pde_count`
- `claim_count`
- `unique_beneficiary_count`
- `unique_provider_count`
- `claim_pde_ratio`
- `volume_change_pct`

### DISTRIBUTION
- `median_days_supply`
- `median_rx_cost`
- `median_claim_amount`

### OPERATIONAL (SIMULATED)
- `processing_duration`
- `throughput`
- `failure_rate`
- `backlog`
