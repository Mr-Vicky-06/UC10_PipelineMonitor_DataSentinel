# PROJECT PROTOTYPE OPERATIONAL RUNBOOKS

## DATA QUALITY RUNBOOK

**Target Anomaly Types:** DATA_QUALITY
**Owner:** Data Governance / Platform Team

### Overview
This runbook applies when deterministic data quality expectations fail during ingestion. This includes referential integrity failures, null values in mandatory fields, and duplicate row detection.

### Expected Impact
Data quality violations can directly corrupt downstream reporting, ML model inputs, and SLA calculations. 

### Recommended Remediation Steps
1. **Quarantine:** Verify that the affected batch has been moved to the dead-letter queue or quarantine bucket.
2. **Upstream Investigation:** Check the source system (e.g., FFS claims ingestion, PDE extract) for formatting changes or missing extract files.
3. **Data Profiling:** Run the anomaly dataset against the `profiling` module to identify if the null/duplicate rate is isolated to a specific provider or date range.
4. **Resubmission:** Once the upstream issue is resolved or a hotfix is applied to the ingestion layer, trigger a pipeline backfill for the affected `window_date`.
