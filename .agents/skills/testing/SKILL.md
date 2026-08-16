---
name: testing
description: Guides testing strategies and methodologies for the DataSentinal and UC10 Pipeline systems.
---
# Testing Skill

## Purpose
Ensures rigorous verification of pipeline and anomaly detection components.

## When to use
- When writing unit, integration, or system tests.
- When evaluating the hybrid anomaly detection logic against ground truth scenarios.

## Inputs
- Component to be tested.

## Expected outputs
- Test code implemented using Pytest (per `TECHNOLOGY_STACK.md`).
- Validation reports.

## Constraints
- Pipeline tests must use the synthetic scenarios from `master_data/` as deterministic fixtures.
- Do not invent synthetic data inside the test scripts; use the generated master data.

## Validation
- Verify all tests pass locally and follow the arrange-act-assert pattern.

## Examples
- Agent writes a Pytest fixture that loads a predefined "MISSING authorization" scenario from `master_data/scenarios/` to test a validation rule.
