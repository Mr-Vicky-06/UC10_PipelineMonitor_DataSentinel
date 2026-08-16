---
name: pipeline-development
description: Guides the implementation of the System 1 Representative Healthcare Pipeline according to DataSentinal standards.
---
# Pipeline Development Skill

## Purpose
Ensures pipeline stages are developed sequentially, adhering to the approved technology stack and phase boundaries.

## When to use
- When implementing ingestion, validation, cleaning, transformation, feature engineering, or business rules for the pipeline.
- When orchestrating or adding telemetry to the pipeline.

## Inputs
- Current pipeline stage being implemented.

## Expected outputs
- Code implementing the specified stage using approved technologies (Polars, Pandera, Airflow/Dagster, OpenTelemetry).

## Constraints
- Pipeline development must proceed sequentially (e.g., Ingestion -> Validation -> Cleaning). Do not skip stages without understanding dependencies.
- Pipeline logic must be separate from DataSentinal (System 2) monitoring logic.

## Validation
- Verify that code uses the approved tech stack.

## Examples
- When asked to build validation, agent uses Pandera instead of a custom Python loop, adhering to `TECHNOLOGY_STACK.md`.
