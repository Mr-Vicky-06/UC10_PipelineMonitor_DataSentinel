# 05 Isolation Forest Feature Matrix

Because raw healthcare records should not be fed directly into Isolation Forest, we construct a batch/window-level feature vector. For this MVP, because the datasets are static annual files, we must simulate "batches" (e.g., chunking the Part D file into 365 daily ingestion files).

## 1. Quality & Content Features

| Feature | Definition | Source | Direct/Derived/Simulated | Data type | Expected anomaly | Detector |
|---|---|---|---|---|---|---|
| `record_count` | Total rows ingested in the batch | All Datasets | Derived | Integer | Drop in volume | IF / Stat |
| `unique_provider_count`| Distinct NPIs in the batch | Part D | Derived | Integer | Sudden drop or spike | IF |
| `missing_rate_npi` | % of rows missing NPI | Part D | Derived | Float (0-1) | Schema break / missingness | IF |
| `duplicate_rate` | % of rows failing uniqueness | All Datasets | Derived | Float (0-1) | Double-ingestion of data | IF |
| `dq_violation_rate` | Overall % of rows failing any DQ rule | All Datasets | Derived | Float (0-1) | Upstream data corruption | IF |

## 2. Statistical / Distribution Features

| Feature | Definition | Source | Direct/Derived/Simulated | Data type | Expected anomaly | Detector |
|---|---|---|---|---|---|---|
| `median_tot_claims` | Median `Tot_Clms` in the batch | Part D | Derived | Float | Sudden shift in prescription volume | IF |
| `sum_drug_cost` | Total `Tot_Drug_Cst` in the batch | Part D | Derived | Float | Drastic change in financial totals | IF |
| `metal_level_dist_shift`| PSI or KS-test stat for `MetalLevel` proportions | Plan PUF | Derived | Float | Shift in plan tier distribution | IF |

## 3. Operational Telemetry Features (Simulated)

Because public static datasets lack operational telemetry, these must be simulated by the processing pipeline.

| Feature | Definition | Source | Direct/Derived/Simulated | Data type | Expected anomaly | Detector |
|---|---|---|---|---|---|---|
| `processing_duration` | Time taken to process the batch (ms) | Pipeline | Simulated | Integer | Massive slowdown | IF |
| `throughput` | Records processed per second | Pipeline | Simulated | Float | Performance degradation | IF |
| `failure_rate` | % of records failing fatal validation | Pipeline | Simulated | Float (0-1) | High rejection rate | IF |
| `retry_rate` | % of records requiring retry | Pipeline | Simulated | Float (0-1) | Downstream API timeout | IF |
| `backlog` | Count of records waiting in queue | Pipeline | Simulated | Integer | System backup | IF |
