# 08 Dataset → UC10 Capability Matrix

| UC10 Capability | Required Information | Dataset | Actual Field(s) | Direct / Derived / Simulated | Supported? | Limitations |
|---|---|---|---|---|---|---|
| Schema Validation | Data types, nullability | All | All columns | Direct | GREEN | Strongest capability using standard tools. |
| Completeness | Null counts | All | All columns | Direct | GREEN | Highly effective. |
| Validity | Domain constraints | All | `StateCode`, numeric aggregates | Direct | GREEN | Can test >0 constraints. |
| Uniqueness | Primary Keys | All | NPI/Drug, PlanId | Direct | GREEN | Requires understanding composite keys. |
| Referential Integrity | Foreign Keys | PUF Files | `PlanID_2026` -> `StandardComponentId` | Direct | GREEN | Supported by PUF structure. |
| Cross-dataset Validation | Inter-domain keys | Part D <-> PUF | N/A | Direct | RED | Part D and ACA PUF do not intersect. |
| Volume Anomaly | Record counts over time | All | N/A | Simulated | YELLOW | Datasets are static annual files; must simulate batches. |
| Distribution Anomaly | Value proportions over time| All | `Tot_Clms`, `MetalLevel` | Simulated | YELLOW | Must simulate time-series batches. |
| Multivariate ML (IF) | Pipeline metrics | Pipeline | `duration`, `throughput` | Simulated | YELLOW | Telemetry must be generated artificially. |
| RCA | Anomaly locality | All | DQ Logs, Batch IDs | Derived | YELLOW | Can localize to stage, but lacks real causal logs. |
| Impact Analysis | Downstream dependency | PUF Files | Crosswalk -> Plan Attributes | Derived | YELLOW | Can show downstream table impact. |
| SLA Risk | Workload, Processing rate | Pipeline | `ETA` | Simulated | YELLOW | Purely a function of the experimental harness. |
| RAG | Documentation | All | PDFs, Codebooks | Direct | GREEN | Can retrieve definitions and methodology. |
