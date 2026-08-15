# 07 UC10 Minimum Data Model

To satisfy the 2-day constraint while supporting Architecture A, we propose the following DuckDB / Parquet-based schema:

## Source Tables (Read-Only)
- `beneficiary` (BENE_ID PK)
- `claims_ffs` (CLM_ID PK, BENE_ID FK)
- `pde_events` (PDE_ID PK, BENE_ID FK)

## Pipeline State Tables
- `pipeline_metrics` (batch_id PK, timestamp, volume, duration_ms, error_rate)
- `dq_results` (rule_id, batch_id, record_id, column, violation_type)

## Anomaly Tables
- `anomaly_events` (event_id PK, batch_id, detector_type, severity, score, feature_json)
- `rca_results` (event_id FK, root_cause_category, impact_scope)
