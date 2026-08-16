---
name: integration
description: Guides the integration process of individual branches into the main repository branch.
---
# Integration Skill

## Purpose
Ensures safe, consistent merging of pipeline components and anomaly detection algorithms into the `main` branch.

## When to use
- When preparing a pull request or integrating local branch changes into `main`.

## Inputs
- Branch diff or PR summary.

## Expected outputs
- A structured review of changes against `AGENTS.md` and `ARCHITECTURE.md`.

## Constraints
- Integration must not happen if tests are failing.
- Ensure no integrated code violates the immutable `data/` rule or technology stack constraints.

## Validation
- Review `git diff` output to verify no unauthorized changes.

## Examples
- Agent reviews a diff and rejects integration because the developer attempted to use Kubernetes instead of Docker/Airflow, violating `TECHNOLOGY_STACK.md`.
