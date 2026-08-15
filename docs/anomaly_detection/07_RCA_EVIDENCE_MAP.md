# 07 Root Cause Analysis (RCA) Evidence Map

This map dictates how observed anomalies correlate to probable root causes based on available evidence.

## DIRECT EVIDENCE (High Certainty)
When a DQ Rule is violated, the dataset and field are known exactly.
- **Observation:** `Prscrbr_NPI` missing rate > 0.
- **Stage Identification:** Validation Stage.
- **Probable Cause:** Upstream data ingestion issue or schema change dropping the NPI column.
- **Impact Estimation:** Exact number of rows missing NPI can be quantified.

## INFERENCE (Probable Cause)
When Cross-Dataset relationships fail.
- **Observation:** High rate of `PlanID_2026` in Crosswalk not found in Plan Attributes.
- **Stage Identification:** Referential Integrity Stage.
- **Probable Cause:** The Plan Attributes file is stale (out of date) relative to the Crosswalk file.
- **Impact Estimation:** Downstream systems relying on Plan Attributes for crosswalked plans will fail.

## HYPOTHESIS (Correlation, Not Causation)
When Multivariate / Operational features are anomalous.
- **Observation:** Isolation Forest flags batch due to high `retry_rate` and high `processing_duration`.
- **Stage Identification:** Processing / API integration stage.
- **Probable Cause:** (Hypothesis) Downstream database or API is experiencing latency/throttling.
- **Impact Estimation:** Can estimate SLA breach risk, but cannot definitively prove *why* the database is slow without database-side logs.

*Note: Never claim causal certainty from Isolation Forest or operational correlation alone.*
