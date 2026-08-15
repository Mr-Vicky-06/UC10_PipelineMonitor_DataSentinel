# UC10 DATA FOUNDATION & FEATURE ENGINEERING TECHNICAL GUIDE
### Data-First Analysis for Healthcare Pipeline Anomaly Detection

**Project:** UC10 &mdash; Data Quality & Pipeline Monitoring  
**Document Type:** Technical Data & Feature Engineering Guide  
**Data Domain:** Medicare / Healthcare Operations  
**Primary Data:** CMS Synthetic Medicare Beneficiary, FFS Claims and PDE  
**Status:** DATA FOUNDATION &mdash; READY TO FREEZE  
**Version:** v1.0  
**Date:** August 2026

---

## DOCUMENT CONTROL

| Field | Value |
| :--- | :--- |
| **Document Title** | UC10 Data Foundation & Feature Engineering Technical Guide |
| **Project** | UC10 &mdash; Data Quality & Pipeline Monitoring |
| **Version** | v1.0 |
| **Date** | August 2026 |
| **Status** | DATA FOUNDATION STATUS: READY TO FREEZE |
| **Primary Data Sources**| CMS Synthetic Beneficiary, FFS Claims, PDE |
| **Primary Technologies**| Python, DuckDB, scikit-learn, Parquet |
| **Prepared For** | Technical Engineering & Architecture Team |
| **Purpose** | Authoritative data and feature engineering reference for UC10 |

---

## TABLE OF CONTENTS

1. Executive Data Summary
2. Data Sources Investigated
3. Dataset Selection Decision
4. Core Dataset Description
5. Dataset Relationships
6. Grain and Temporal Analysis
7. Data Quality Analysis
8. Technology Stack
9. Feature Engineering
10. 18-Feature Dictionary
11. Feature &rarr; Aspect &rarr; Detector
12. Controlled Anomaly Scenarios
13. Real vs Derived vs Simulated Data
14. Authentication / Authorization Data Gap
15. Synthetic Authorization Approach
16. Optional / Supporting Datasets
17. Current Implementation Status
18. Why Data-First Sequencing
19. Remaining Development
20. Final Data Architecture
21. Data Source References
22. Final Takeaway

---

## 1. Executive Data Summary

This document serves as the authoritative technical reference for the UC10 Data Foundation and Feature Engineering workflow. The UC10 pipeline is designed to detect anomalies in healthcare operational data streams using parallel detection mechanisms (Data Quality Rules, Rolling Median/MAD, and Isolation Forest). 

Before building the final production simulation, the team performed a deep empirical audit of the available datasets to establish correct data relationships, resolve structural grain differences, and define an 18-feature analytical matrix. This document outlines exactly what data was investigated, why the core datasets were selected, how raw records are mathematically transformed into behavioral features, and how those features are consumed by the detection layer.

---

## 2. Data Sources Investigated

The project performed an empirical investigation of multiple publicly available healthcare data ecosystems to identify the optimal foundation for anomaly detection.

### 2.1 CMS Synthetic Healthcare Data (PRIMARY SOURCE)
The **CMS Synthetic Medicare Enrollment, Fee-for-Service (FFS) Claims, and Prescription Drug Event (PDE)** ecosystem was heavily investigated. This data includes synthetic Beneficiary summaries, medical activity (Claims), and pharmacy activity (PDE). It ultimately became the finalized **CORE DATA ECOSYSTEM**.

### 2.2 Medicare Part D Prescribers
The **CMS Medicare Part D Prescribers / Provider and Drug** dataset was investigated as an alternative. It provides provider-level and drug-level summary metrics. It was **NOT** selected as the primary active pipeline dataset due to its high level of aggregation, the absence of a `BENE_ID`, and its inability to support cross-dataset transactional anomaly tracing. It serves a different analytical purpose and is reserved for optional contextual/reference data.

### 2.3 Healthcare.gov PUF
The **Healthcare.gov Public Use Files (PUF)** (including `plan_attributes_PUF`, `plan_id_crosswalk_PUF`, and `service_area_PUF`) were investigated. They are strictly **supporting/optional** reference sources and do not contain transactional healthcare activity.

### 2.4 DQ Reference Documentation
The public documentation for **Great Expectations** and **Soda** were investigated. They were not treated as healthcare transaction data, but were used to inform Data Quality rule design, providing examples of completeness, uniqueness, validity, and consistency checks.

---

## 3. Dataset Selection Decision

### WHY WE CHOSE THE CMS SYNTHETIC ECOSYSTEM

| Dataset Option | Beneficiary Link | Claim/Event Grain | Cross-Dataset Analysis | DQ Analysis | Anomaly Detection | Final Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A. Beneficiary + FFS Claims + PDE** | Yes (`BENE_ID`) | Yes (Line/Event) | High | High | High | **Core Pipeline** |
| **B. Beneficiary + Part D Prescribers** | No | No (Aggregated) | Low | Low | Low | Optional |
| **C. PUF / Supporting Data** | No | No | Low | Low | Low | Supporting |

> **DESIGN DECISION**
> Architecture A (Beneficiary + FFS Claims + PDE) was selected because it provides strong relational connectivity via `BENE_ID`, transaction/event-level detail, and the temporal granularity required for cross-dataset anomaly tracing and Isolation Forest modeling.

---

## 4. Core Dataset Description

The core UC10 data ecosystem consists of three empirical datasets:

**BENEFICIARY**
- **Purpose**: Member reference and master dataset.
- **Grain**: 1 row = 1 unique beneficiary.
- **Key**: `BENE_ID`
- **Size**: 5,975 rows.

**FFS CLAIMS**
- **Purpose**: Medical activity and institutional/non-institutional claims.
- **Grain**: Claim-line level.
- **Keys**: `CLM_ID` + `CLM_LINE_NUM`. Linked via `BENE_ID`.
- **Size**: 1,121,004 rows (representing 90,705 unique claims across 7,971 beneficiaries).

**PDE**
- **Purpose**: Pharmacy and prescription drug events.
- **Grain**: Prescription-event level.
- **Keys**: `PDE_ID`. Linked via `BENE_ID`.
- **Size**: 515,520 rows (across 7,403 beneficiaries).

---

## 5. Dataset Relationships

The core architecture relies on a centralized relational hub:

<div class="mermaid keep-together">
graph TD
    B["Beneficiary Dataset"]
    C["FFS Claims"]
    P["PDE"]
    
    B ---|BENE_ID| C
    B ---|BENE_ID| P
</div>

**Relationship Mechanics:**
- The `BENE_ID` is the central referential key linking Claims and PDE back to the Beneficiary master table.
- Claims and PDE have a one-to-many relationship with the Beneficiary.
- **Orphan Records**: The empirical audit found orphan records (Claims or PDEs containing a `BENE_ID` not present in the Beneficiary table). These are not removed; they are highly valuable because they become explicit **Data Quality (DQ) anomaly evidence**.

---

## 6. Grain and Temporal Analysis

The datasets possess inherently different structural grains:
- **Beneficiary**: 1 row = 1 beneficiary
- **Claims**: 1 row = 1 claim line (multiple lines per claim encounter)
- **PDE**: 1 row = 1 prescription event

Because 100 claim lines does not equal 100 prescription events, these records cannot be compared directly. 

**Temporal Aggregation Strategy**:
The feature engineering process normalizes the data into a **Common Analytical Window** (Daily). By transforming raw records into daily volumes and medians, the pipeline prevents grain-driven distortion. Furthermore, a rolling historical baseline is used to compare "today's" behavior against "recent historical" behavior, inherently accounting for natural weekend/weekday volume volatility.

---

## 7. Data Quality Analysis

Data Quality (DQ) in UC10 is not merely preprocessing. **Data quality problems become anomaly evidence.**

The audit investigated:
- **Completeness**: Missing identifiers and required fields.
- **Uniqueness**: Duplicate primary keys (`CLM_ID` + `CLM_LINE_NUM` or `PDE_ID`).
- **Validity**: Invalid or logically impossible dates.
- **Referential Integrity**: Cross-dataset mismatches (e.g., orphans).

These dimensions are captured by the DQ Engine, resulting in violation rates that are directly fused into the final anomaly assessment.

---

## 8. Technology Stack

<div class="mermaid keep-together">
graph TD
    RD["RAW DATA"] -->|"DuckDB / SQL"| P["Python Orchestration"]
    P -->|"Pandas"| FE["Feature Engineering"]
    FE -->|"Parquet"| ML["scikit-learn"]
    ML -->|"Isolation Forest"| AD["Anomaly Detection"]
</div>

**Technologies:**
- **Python**: Primary orchestration, analysis, and feature engineering language.
- **DuckDB & SQL**: High-performance SQL analysis over large CSV datasets without requiring the entire dataset to be loaded into memory.
- **Pandas**: Targeted dataframe transformations and validations.
- **Parquet**: Efficient, strongly-typed storage of the resulting feature matrix.
- **scikit-learn**: Statistical and ML processing (Isolation Forest).
- **YAML**: Configurable DQ rules and anomaly parameters.
- **Markdown**: Auditable technical documentation.

---

## 9. Feature Engineering

The detection models do NOT consume raw healthcare records directly. They consume a daily behavioral representation.

<div class="mermaid keep-together">
graph TD
    RD["RAW DATA"] --> V["VALIDATION"]
    V --> GU["GRAIN UNDERSTANDING"]
    GU --> DS["DATE STANDARDIZATION"]
    DS --> DA["DAILY AGGREGATION"]
    DA --> CR["CROSS-DATA RELATIONSHIPS"]
    CR --> SD["STATISTICAL DERIVATIONS"]
    SD --> FM["FEATURE MATRIX"]
</div>

Feature engineering collapses millions of heterogeneous rows into a standardized 18-feature matrix per day, ensuring mathematically sound inputs for the Isolation Forest and Statistical detectors.

---

## 10. 18-Feature Dictionary

The complete, authoritative mapping of all 18 features used in the UC10 pipeline.

| Feature Name | Source | What It Measures | Data Aspect | Detector | Why It Matters |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `null_rate` | Derived | Rate of missing critical identifiers | Data Quality | DQ Rules | Indicates upstream data corruption |
| `duplicate_rate` | Derived | Rate of duplicate primary keys | Data Quality | DQ Rules | Indicates replay or system retry errors |
| `claims_null_rate` | Derived | Missingness specifically in Claims | Data Quality | DQ Rules | Claim-specific data corruption |
| `cross_dataset_mismatch_rate` | Derived | Orphan records missing `BENE_ID` master | Data Quality | DQ Rules | Referential integrity failure |
| `dq_violation_rate` | Derived | Overall DQ failure rate | Data Quality | DQ Rules | Aggregate quality health |
| `pde_count` | PDE | Daily prescription volume | Healthcare Volume | MAD, IF | Baseline pharmacy activity |
| `claim_count` | FFS Claims | Daily medical claim volume | Healthcare Volume | MAD, IF | Baseline medical activity |
| `unique_beneficiary_count` | Claims + PDE| Distinct members seen today | Healthcare Volume | IF | Breadth of population impact |
| `unique_provider_count` | Claims + PDE| Distinct providers operating today | Healthcare Volume | IF | Breadth of provider network impact |
| `claim_pde_ratio` | Derived | Ratio of medical to pharmacy activity | Healthcare Volume | MAD, IF | Detects divergent ingestion failures |
| `volume_change_pct` | Derived | Day-over-day total volume shift | Healthcare Volume | MAD, IF | Identifies catastrophic drops/spikes |
| `median_days_supply` | PDE | Distribution of prescription duration | Distribution | MAD, IF | Detects unusual clinical coding shifts |
| `median_rx_cost` | PDE | Distribution of prescription cost | Distribution | MAD, IF | Detects financial metric shifts |
| `median_claim_amount` | FFS Claims | Distribution of claim financial value | Distribution | MAD, IF | Detects financial claim shifts |
| `processing_duration` | Simulated | Time taken to process the batch | Operational | IF | Indicates system drag or latency |
| `throughput` | Simulated | Records processed per second | Operational | IF | Indicates processing efficiency |
| `failure_rate` | Simulated | System-level processing errors | Operational | IF | Hardware or infrastructure errors |
| `backlog` | Simulated | Workload pending execution | Operational | IF | Identifies queuing and SLA risk |

---

## 11. Feature &rarr; Aspect &rarr; Detector

<div class="mermaid keep-together">
graph TD
    F["18 Final Features"] --> DA["Data Aspects"]
    DA --> DQ_Aspect["Data Quality"]
    DA --> Vol_Aspect["Healthcare Volume"]
    DA --> Dist_Aspect["Distribution"]
    DA --> Ops_Aspect["Operational Behavior"]
    
    DQ_Aspect --> DQ["DQ Engine<br/>'Is something explicitly wrong?'"]
    Vol_Aspect --> MAD["MAD Engine<br/>'Is a metric unusually different?'"]
    Dist_Aspect --> MAD
    Vol_Aspect --> IF["Isolation Forest<br/>'Is the combination unusual?'"]
    Dist_Aspect --> IF
    Ops_Aspect --> IF
</div>

Different anomalies require different mechanisms. **DQ** strictly catches boolean violations. **MAD** identifies univariate volatility. **Isolation Forest** evaluates the multivariate combination of features to catch complex structural shifts.

---

## 12. Controlled Anomaly Scenarios

To validate the architecture, anomalies were injected into **TESTING DATA** (not the clean baseline).

1. **Missing Identifier**: Affects `null_rate`. Caught by **DQ**. Evidence: Sharp spike in null percentage.
2. **Duplicate Record**: Affects `duplicate_rate`. Caught by **DQ**. Evidence: PK duplication.
3. **Invalid Date**: Affects `dq_violation_rate`. Caught by **DQ**. Evidence: Out-of-bounds dates.
4. **Referential Integrity Failure**: Affects `cross_dataset_mismatch_rate`. Caught by **DQ**.
5. **Volume Drop**: Affects `claim_count` / `pde_count`. Caught by **MAD**. Evidence: Metric drops below 3 MAD threshold.
6. **Multivariate Degradation**: Affects multiple metrics subtly (e.g. `claim_pde_ratio` shifts alongside `processing_duration`). Caught by **Isolation Forest**. 

---

## 13. Real vs Derived vs Simulated Data

The dataset features fall into three strict categories:

**CATEGORY A &mdash; DIRECTLY OBSERVED DATA**
Real CMS data attributes: Claims, PDE, Beneficiary identifiers, service dates, claim amounts, drug measures.

**CATEGORY B &mdash; DERIVED FEATURES**
Mathematically calculated from real data: `claim_count`, `pde_count`, ratios, volume change, mismatch rates, medians.

**CATEGORY C &mdash; SIMULATED OPERATIONAL TELEMETRY**
Operational fields: `processing_duration`, `throughput`, `failure_rate`, `backlog`. 
*Note: CMS datasets provide healthcare activity, not live pipeline execution telemetry. These operational features are simulated for prototype purposes and must be replaced with real observability data in production.*

---

## 14. Authentication / Authorization Data Gap

The available CMS datasets **do not** contain authentication, authorization, or prior-authorization transaction data.

**Missing Elements:**
- Authentication event / System identity
- Authorization request / Workflow status
- Approval/denial timestamp
- Decision reason code

These fields cannot be directly modeled from the core CMS datasets, and must not be silently invented into the real clinical data.

---

## 15. Synthetic Authorization Approach

To demonstrate authorization anomalies without corrupting the core CMS data, a separate **synthetic operational dataset** is proposed.

<div class="mermaid keep-together">
graph LR
    CMS["Available CMS Data"] --> C["Claims"]
    CMS --> P["PDE"]
    CMS --> B["Beneficiary"]
    
    MISS["Missing Data"] -.-> Auth["Authentication"]
    MISS -.-> PAuth["Prior Authorization"]
    
    PROTO["Prototype Solution"] --> SYN["Separate Synthetic Dataset"]
    SYN -.->|"Relational Join"| B
</div>

This synthetic dataset (containing `AUTH_EVENT_ID`, `REQUEST_TS`, `APPROVAL_STATUS`) remains isolated and clearly labeled, allowing the prototype to demonstrate access workflow anomalies while preserving clinical data integrity.

---

## 16. Optional / Supporting Datasets

**Medicare Part D Prescribers (Provider and Drug)**
Useful for provider-level context and aggregated pharmacy analysis. It should **not** replace PDE in the core pipeline because PDE provides event-level data and direct `BENE_ID` relationships essential for cross-dataset anomaly analysis.

<div class="mermaid keep-together">
graph TD
    subgraph Core_Pipeline["Core Pipeline"]
    P["PDE"] --> B["Beneficiary"] --> C["Claims"]
    end
    
    subgraph Contextual_Reference["Contextual Reference"]
    PDP["Part D Prescribers"] --> PD["Provider / Drug Aggregate"]
    end
</div>

---

## 17. Current Implementation Status

| Work | Status |
| :--- | :--- |
| Data source investigation | COMPLETE |
| Dataset selection | COMPLETE |
| Relationship analysis | COMPLETE |
| DQ profiling | COMPLETE |
| Temporal analysis | COMPLETE |
| Feature engineering | COMPLETE |
| Feature validation | COMPLETE |
| DQ detector | COMPLETE |
| MAD detector | COMPLETE |
| Isolation Forest | COMPLETE |
| Controlled anomaly testing | COMPLETE |
| Evidence fusion | COMPLETE |
| Anomaly assessment | COMPLETE |
| RAG | PROTOTYPE COMPLETE |
| Production pipeline | NOT YET BUILT |
| Real operational telemetry | NOT AVAILABLE |
| Real authentication data | NOT AVAILABLE |

*Note: The prototype demonstrates detection capability but is not a fully autonomous production system.*

---

## 18. Why Data-First Sequencing

The project intentionally followed a strict sequence:
`DATA UNDERSTANDING &rarr; FEATURE ENGINEERING &rarr; ANOMALY DETECTION &rarr; RAG &rarr; PIPELINE DEMONSTRATION`

If the data foundation is mathematically or relationally flawed, the anomaly detector and RAG layer will generate false alerts. The team established correct datasets, relationships, grain, and features before advancing to production orchestration.

---

## 19. Remaining Development

**COMPLETED DATA WORK:**
Dataset selection, profiling, feature engineering, and core anomaly detection logic.

**NEXT DEVELOPMENT WORK:**
- Pipeline simulation/prototype execution
- Integration of data ingestion and processing
- Connecting detection engines to the simulated pipeline
- Synthetic authentication/authorization demonstration
- Human-in-the-loop remediation UI
- Production-like orchestration

*Note: RAG remains a knowledge-assistant layer and must not be described as the component that detects anomalies.*

---

## 20. Final Data Architecture

<div class="mermaid keep-together" style="max-width: 40%; margin: 0 auto;">
graph TD
    SD["CMS SYNTHETIC DATA"] --> BC["Beneficiary + FFS Claims + PDE"]
    BC --> DV["Data Validation"]
    DV --> RV["Relationship Validation"]
    RV --> TA["Temporal Aggregation"]
    TA --> FE["Feature Engineering"]
    FE --> FM["18 Feature Matrix"]
    
    FM --> DQ["DQ Rules"]
    FM --> MAD["MAD"]
    FM --> IF["Isolation Forest"]
    
    DQ --> EF["Evidence Fusion"]
    MAD --> EF
    IF --> EF
    
    EF --> AA["Anomaly Assessment"]
    AA --> RCA["RCA / Impact / SLA"]
    RCA --> RAG["RAG Knowledge Assistant"]
    RAG --> RA["Recommended Action"]
    RA --> HL["Human Review / Remediation"]
</div>

---

## 21. Data Source References

[1] CMS — Synthetic Medicare Enrollment, FFS Claims and PDE  
`https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/DE_Syn_PUF`

[2] CMS — Medicare Part D Prescribers by Provider and Drug  
`https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers`

[3] Healthcare.gov — Public Use Files  
`https://www.healthcare.gov/health-and-dental-plan-datasets-for-researchers-and-issuers/`

[4] Great Expectations Documentation  
`https://docs.greatexpectations.io/`

[5] Soda Documentation  
`https://docs.soda.io/`

---

## 22. Final Takeaway

The UC10 Data Foundation safely converts heterogeneous clinical records into a standardized daily behavioral view. The resulting features provide distinct types of evidence (data quality, distribution, volume, and simulated operations). Each evidence type is routed to the mathematical detector best suited to identify that specific anomaly class. 

### DATA FOUNDATION STATUS: READY TO FREEZE
