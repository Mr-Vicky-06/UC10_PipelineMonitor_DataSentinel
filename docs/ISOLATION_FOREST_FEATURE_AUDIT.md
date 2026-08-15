# Isolation Forest Feature Audit

This document reviews all candidate features before they are passed to the Isolation Forest model. No categorical identifiers, IDs, or raw metadata enter the model.

## Core Behavioral Features

| Feature | Included? | Reason | Type | Risk |
|---|---|---|---|---|
| `pde_count` | Yes | Core pharmacy volume metric | Numeric | None |
| `claim_count` | Yes | Core medical volume metric | Numeric | None |
| `unique_beneficiary_count` | Yes | Cardinality check for medical claims | Numeric | None |
| `unique_provider_count` | Yes | Cardinality check for pharmacy | Numeric | None |
| `median_days_supply` | Yes | Pharmacy distribution behavior | Numeric | Low (can be noisy) |
| `median_rx_cost` | Yes | Pharmacy financial distribution | Numeric | Low |
| `median_claim_amount` | Yes | Medical financial distribution | Numeric | Low (high variance) |
| `claim_pde_ratio` | Yes | Cross-dataset relationship | Numeric | None |
| `cross_dataset_mismatch_rate` | Yes | Cross-dataset referential integrity | Numeric | None |
| `volume_change_pct` | Yes | Velocity of volume changes | Numeric | Low |
| `null_rate` | Yes | PDE missingness metric | Numeric | None |
| `duplicate_rate` | Yes | PDE duplicate metric | Numeric | None |
| `claims_null_rate` | Yes | Claim missingness metric | Numeric | None |
| `dq_violation_rate` | Yes | Aggregated DQ rules failure | Numeric | None |

## Simulated Operational Features

**Important Disclaimer**: The following features are SIMULATED for the purpose of the MVP. In a production environment, these would be captured from Airflow/Dataproc telemetry. Currently, they are deterministic calculations based partially on volume metrics and applied random noise.

| Feature | Included? | Reason | Type | Risk |
|---|---|---|---|---|
| `processing_duration` | Yes | Time to process batch | Numeric | Moderate (Simulated) |
| `throughput` | Yes | Rows processed per second | Numeric | Moderate (Simulated) |
| `failure_rate` | Yes | Percentage of failed jobs/rows | Numeric | Moderate (Simulated) |
| `backlog` | Yes | Queued unprocessed records | Numeric | Moderate (Simulated) |

## Excluded Features
- `BENE_ID`, `CLM_ID`, `NPI`, `PRVDR_ID`: Excluded. Raw identifiers must never enter the Isolation Forest.
- `feature_date`: Excluded. Used strictly for temporal splitting and result joining.
- `anomaly_label` / `injected_anomaly`: Excluded. Isolation Forest is unsupervised and cannot see ground truth labels.
