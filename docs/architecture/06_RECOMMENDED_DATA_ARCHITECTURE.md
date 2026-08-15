# 06 Recommended Data Architecture

**SELECTED ARCHITECTURE:** Architecture A (Beneficiary + FFS Claims + PDE)

**ALTERNATIVE:** Architecture B (Beneficiary + FFS Claims + Part D Prescribers)

**FINAL DECISION:** 
Architecture A is definitively selected as the primary architecture. Empirical testing revealed that the synthetic `BENE_ID` and `PRSCRBR_ID` keys in the PDE dataset have a 100% overlap with the Beneficiary and Claims datasets, enabling full referential integrity. In contrast, the Part D Prescribers dataset (Architecture B) is a real-world aggregate with a 0% NPI overlap with the synthetic claims, meaning it is impossible to join the datasets or perform cross-dataset validation.

### Why Architecture A Wins

| Rank | Selection Reason | Evidence | UC10 Capability | Advantage Over Alternative | Impact |
|---|---|---|---|---|---|
| 1 | Verified Relationships | 100% BENE_ID match between FFS and PDE. | Cross-dataset Validation | Arch B has 0% overlap. | Allows true end-to-end tracing. |
| 2 | Transactional Granularity | PDE contains `SRVC_DT`. | Temporal Anomaly Detection | Arch B is an annual aggregate. | Enables time-series ML features. |
| 3 | Entity Resolution | BENE_ID is present in PDE. | RCA and Impact Analysis | Arch B drops beneficiary context. | Can localize anomaly to patient cohort. |
| 4 | Explainability | Direct primary key lineage. | RAG Evidence Generation | Arch B requires massive inference. | LLM receives highly specific structured data. |
| 5 | Feasibility | Native schema alignment. | 2-day implementation limit | Arch B requires complex mapping heuristics. | Can be implemented quickly. |

**SECONDARY/ENRICHMENT:** 
The Medicare Part D Prescribers dataset should be retained as an offline Enrichment dataset for the RAG assistant to provide real-world context on drug behaviors, but NOT actively joined in the primary data pipeline.
