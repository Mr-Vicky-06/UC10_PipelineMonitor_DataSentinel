# UC10 Final Feature Contract

This is the authoritative feature contract bridging raw data, anomaly detection, and RAG components.

## 1. Feature Definitions

| Final Feature Name | Source | Formula | Meaning | Primary Detector | Real/Simulated |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `claim_count` | FFS Claims | `count(CLM_ID)` per day | Daily FFS claim volume | MAD, IF | Real |
| `pde_count` | PDE | `count(PDE_ID)` per day | Daily prescription volume | MAD, IF | Real |
| `unique_beneficiary_count` | Claims + PDE | `count(distinct BENE_ID)` | Number of unique members seen today | IF | Real |
| `unique_provider_count` | Claims + PDE | `count(distinct PRVDR_NPI)` | Number of unique providers | IF | Real |
| `claim_pde_ratio` | Derived | `claim_count / pde_count` | Ratio of medical to pharmacy activity | MAD, IF | Derived |
| `null_rate` | Derived | `count(null PKs) / total` | Rate of missing critical identifiers | DQ Engine | Derived |
| `duplicate_rate` | Derived | `count(duplicate PKs) / total` | Rate of duplicate records | DQ Engine | Derived |
| `dq_violation_rate` | Derived | `count(dq_fails) / total` | Overall DQ failure rate | DQ Engine | Derived |
| `processing_duration` | Simulated | `f(volume) + noise` | Total time to process batch | IF, SLA | Simulated |
| `throughput` | Simulated | `volume / duration` | Records processed per second | IF, SLA | Simulated |
| `backlog` | Simulated | `accumulated_unprocessed` | Workload pending execution | SLA | Simulated |

## 2. Redundancy & Correlation Analysis
- `claim_count` and `pde_count` are highly correlated. This is **useful** because when they diverge (e.g., claims arrive but PDE fails), it flags an ingestion anomaly.
- `processing_duration` and `volume` are mathematically dependent in the simulated proxy. This is an **acceptable** limitation for the prototype, but must be replaced with true execution telemetry in production.
