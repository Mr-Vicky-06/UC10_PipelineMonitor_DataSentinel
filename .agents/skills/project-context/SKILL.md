---
name: project-context
description: Enforces the DataSentinal shared project context, architecture, and constraints for agents.
---
# Project Context Skill

## Purpose
Ensures the agent understands the overall system architecture and the strict constraints governing the DataSentinal and UC10 Pipeline systems.

## When to use
- When initiating a new task or joining a new branch.
- When you need to understand the boundary between System 1 (Pipeline) and System 2 (DataSentinal).
- Before proposing any architectural changes.

## Inputs
- Current task or branch name.

## Expected outputs
- Agent explicitly acknowledges the project context, phase boundaries, and rules.

## Constraints
- The `data/` directory is strictly immutable. Never modify it.
- Master data lives in `master_data/`.
- Must check `DECISIONS.md` before making architectural changes.

## Validation
- Ensure no data modification commands target the `data/` directory.

## Examples
- User asks to clean raw data. Agent refuses and instructs that cleaning happens in the pipeline using master data, leaving `data/` intact.
