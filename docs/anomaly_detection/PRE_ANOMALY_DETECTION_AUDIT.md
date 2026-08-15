# Pre-Anomaly Detection Audit

## Temporal Baseline Check
- **Rows**: 2,922 (Representing exactly 8 years of daily data).
- **Format**: `feature_date` strings (YYYY-MM-DD).
- **Status**: Verified. No gaps, no duplicates. Daily grain is correct.

## Imputation & Validation Check
- **Missingness**: 0 NaNs. Imputation was performed via forward-fill for missing dates, and zero-fill for counts where no activity existed. 
- **Infinite Values**: 0. Divisions by zero were successfully replaced with NaNs and zero-filled.

## Operational Simulation Check
- The following metrics are completely deterministic and mathematically derived from `pde_count` and `claim_count` plus static noise:
  - `processing_duration` = 120 + (`pde_count` * 0.05) + N(0,5)
  - `throughput` = (`pde_count` + `claim_count`) / `processing_duration`
  - `failure_rate` = (`null_rate` + `duplicate_rate`) * 1.5
  - `backlog` = `pde_count` * U(0.01, 0.05)
- **Status**: These are strictly SIMULATED OPERATIONAL FEATURES. They will correlate perfectly with volume anomalies.

## Candidate Feature Audit

| Feature | Type | Detector | Leakage? | Stable? | Suitable? | Notes |
|---|---|---|---|---|---|---|
| `pde_count` | Volume | MAD / IF | No | Yes | **YES** | Primary workload indicator. |
| `claim_count` | Volume | MAD / IF | No | Yes | **YES** | Secondary workload indicator. |
| `unique_beneficiary_count` | Volume | MAD / IF | No | Yes | **YES** | Measures distinct patient flow. |
| `unique_provider_count` | Volume | MAD / IF | No | Yes | **YES** | Measures distinct provider flow. |
| `median_days_supply` | Dist | MAD / IF | No | Yes | **YES** | Shift in drug dispensing. |
| `median_rx_cost` | Dist | MAD / IF | No | Yes | **YES** | Shift in drug costs. |
| `median_claim_amount` | Dist | MAD / IF | No | Yes | **YES** | Shift in claim payments. |
| `claim_pde_ratio` | Cross | IF | No | Yes | **YES** | Measures pipeline decoupling. |
| `cross_dataset_mismatch_rate`| Cross | IF | No | Yes | **YES** | Normalized mismatch metric. |
| `volume_change_pct` | Temp | MAD / IF | No | Yes | **YES** | Day-over-day volatility. |
| `null_rate` | DQ | DQ | No | Constant | **YES** | Currently 0 (Clean baseline). |
| `duplicate_rate` | DQ | DQ | No | Constant | **YES** | Currently 0 (Clean baseline). |
| `claims_null_rate` | DQ | DQ | No | Constant | **YES** | Currently 0 (Clean baseline). |
| `dq_violation_rate` | DQ | DQ | No | Constant | **YES** | Currently 0 (Clean baseline). |
| `processing_duration` | Ops | MAD / IF | No | Yes | **YES** | Simulated from volume. |
| `throughput` | Ops | MAD / IF | No | Yes | **YES** | Simulated from volume. |
| `failure_rate` | Ops | DQ / IF | No | Constant | **YES** | Simulated from DQ rates. |
| `backlog` | Ops | MAD / IF | No | Yes | **YES** | Simulated from volume. |

**Conclusion**: All 18 numeric columns are suitable. The 0-variance DQ features are retained because they serve as the baseline for the upcoming anomaly injection phase.
