---
name: pipeline-development
description: Guides the implementation of the System 1 Representative Healthcare Pipeline according to DataSentinal standards.
---
# Pipeline Development Skill

## Purpose
Ensures pipeline stages are developed and executed sequentially, adhering to the approved technology stack and phase boundaries. The pipeline is fully orchestrated from Phase A (Landing) through Phase E (Orchestration).

## When to use
- When implementing, testing, or executing ingestion, validation, cleaning, transformation, feature engineering, or business rules for the pipeline.
- When orchestrating or monitoring telemetry for the pipeline.
- When running end-to-end pipeline validation.

## Architecture
- **Phase A (Landing):** Secure, immutable data ingestion boundary.
- **Phase B (Business Rules):** Data quality constraints (BR-FIN, BR-REF).
- **Phase C (Transformation):** DuckDB/Pandas translation logic, resolving schema changes.
- **Phase D (Integration):** Feature Engineering structure preparation.
- **Phase E (Orchestration):** `PipelineOrchestrator` runs all stages sequentially (Landing -> Ingestion -> Validation -> Cleaning -> Transformation -> Business Rules -> Storage), capturing comprehensive run metrics via `PipelineTelemetryLogger`.

## Execution
To run the full end-to-end validation on 1,000 deterministic records, use the provided script:
```bash
python scripts/pipeline_execution/run_final_e2e_validation.py
```
This script tests idempotency, schema validations, failsafe mechanisms (telemetry fail-open), and records outcomes into `outputs/pipeline_workspace/`.

## Inputs
- Current pipeline stage being implemented or executed.

## Expected outputs
- Code implementing the specified stage using approved technologies (Polars, Pandera, DuckDB, Python).
- Telemetry events logged accurately in `outputs/pipeline_workspace/pipeline_telemetry.duckdb`

## Constraints
- Pipeline development must proceed sequentially (e.g., Ingestion -> Validation -> Cleaning). Do not skip stages without understanding dependencies.
- Pipeline logic must be separate from DataSentinal (System 2) monitoring logic.
- Pipeline execution must preserve the `(CLM_ID, CLM_LINE_NUM)` claim-line grain.

## Validation
- Verify that code uses the approved tech stack.
- Verify telemetry captures paired STARTED and COMPLETED events with valid `correlation_id` and `run_id`.

## Examples
- When asked to build validation, agent uses Pandera instead of a custom Python loop, adhering to `TECHNOLOGY_STACK.md`.
- When modifying the pipeline, agent uses `PipelineOrchestrator` to ensure stages are orchestrated sequentially.
