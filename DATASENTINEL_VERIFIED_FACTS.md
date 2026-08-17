# DataSentinel — Verified Facts

## Project Overview
* **Project Name:** DataSentinel
* **Current Architecture:** Local-first Python + Pandas + DuckDB

## Pipeline Architecture
* **Pipeline Stages:**
  1. Landing
  2. Ingestion
  3. Validation
  4. Cleaning
  5. Transformation
  6. Business Rules
  7. Storage

## Persistence & Storage
* **Persistence Engine:** DuckDB
* **Processed Claims Database:** `outputs/pipeline_workspace/processed_claims.duckdb`
* **Telemetry Database:** `outputs/pipeline_workspace/pipeline_telemetry.duckdb`

## Database Schemas & Granularity
* **Telemetry Table:** `pipeline_events`
* **Business Result Table:** `rule_results`
* **Claim Table:** `processed_claims`
* **Claim Grain:** `CLM_ID` + `CLM_LINE_NUM`

## Telemetry System
* **Core Concept:** Every major pipeline stage emits structured events.
* **Telemetry States:** `STARTED`, `COMPLETED`, `FAILED`
* **Telemetry Identifiers:** `run_id`, `correlation_id`
* **Fail-Open Design:** Telemetry failure must not stop core pipeline execution.
* **Separation of Concerns:** Operational Error is strictly separate from business/data-quality violations.

## Data Quality & Validation
* **Source Data:** `data/raw/claims/inpatient.csv`
* **Immutable Sources:** `data/` and `master_data/` must never be altered by the pipeline.

## Performance & Testing Metrics
* **Final Regression Suite:**
  * 132 collected
  * 132 passed
  * 0 failed
  * 0 skipped
  * 0 errors
* **Real Data Test:**
  * 1,000 claim lines processed
  * 1,000 persisted
  * 0 duplicate claim grains
* **Adversarial Test:**
  * 100 total records tested
  * 30 clean records
  * 70 intentionally defective records
  * 8 distinct defect categories
* **Adversarial Rule Performance:**
  * Precision = 1.00
  * Recall = 1.00
  * F1 Score = 1.00 (for all validated rules)

## Future Roadmap (Next Phases)
* Monitoring Dashboard
* Anomaly Detection
* RCA (Root Cause Analysis) / RAG
* SLA Prediction
* Advanced Intelligence
