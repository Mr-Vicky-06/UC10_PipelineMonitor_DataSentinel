# DATASENTINEL PRESENTATION ASSET MANIFEST

This manifest provides Claude (or any AI presentation generator) with the exact files required to construct a highly technical, accurate, and fact-based presentation for DataSentinel. 

---

## 1. PRIMARY SOURCE OF TRUTH (MANDATORY)

**File**: `outputs/presentation/DATASENTINEL_PRESENTATION_SOURCE_OF_TRUTH.md`
**Usage**: This is the absolute primary asset. Claude MUST use this file to extract the Executive Summary, the final integration status, the 18-Feature contract, the exact test counts (218/218), and the ML/RAG validation results. If any other document contradicts this file, THIS file takes precedence.

---

## 2. PIPELINE & ORCHESTRATION DETAILS

**File**: `FINAL_PIPELINE_END_TO_END_VALIDATION_REPORT.md`
**Usage**: Use this to construct a slide on "Pipeline Scale & Idempotency." It contains the exact breakdown of how the 1,000 test records moved through the 7 stages without loss, and how Business Rules generated exactly 3,603 Data Quality violations without crashing the pipeline.

---

## 3. OBSERVABILITY & TELEMETRY ARCHITECTURE

**File**: `PHASE_F_TELEMETRY_FINAL_REPORT.md`
**Usage**: Use this to explain the "DuckDB Telemetry Engine." Highlight the Fail-Open JSONL mechanism, the `pipeline_events` schema, and how Data Quality failures are strictly segregated from Operational Failures.

**File**: `TELEMETRY_ARCHITECTURE_CURRENT_STATE.md`
**Usage**: Use this to extract any necessary Mermaid diagrams or structural overviews of how the Telemetry logger integrates with the Orchestrator.

---

## 4. AI/ML DETECTION ENGINE

**File**: `PHASE_4_2_FINAL_ML_ACCEPTANCE_GATE_REPORT.md`
**Usage**: Use this to build the "Intelligence Layer" slides. Detail the exact models used (EWMA, Isolation Forest), their high precision/low false-positive rates, and explicitly note that they are approved as "Secondary Novelty Detectors" rather than primary rule engines due to low recall.

**File**: `AI_ML_FEATURE_CONTRACT_REPORT.md`
**Usage**: Use this to build a visual table representing the 18-Feature Contract, showcasing exactly which features are active (13) and which are unavailable (5).

---

## 5. RAG & ROOT CAUSE ANALYSIS ENGINE

**File**: `PHASE_5A_REAL_EVIDENCE_VALIDATION_REPORT.md`
**Usage**: Use this to build the "RAG/RCA Engine" slide. Highlight the deterministic SQL retrieval method, the 100% hallucination resistance, and the Near-Zero latency for fetching live DuckDB telemetry. Emphasize that the RAG engine is a *read-only consumer*, not an anomaly detector.

---

## 6. GROUND TRUTH & DATA INTEGRITY

**File**: `MASTER_DATA_IMPACT_ANALYSIS.md`
**Usage**: Use this to explain the "Master Data Ecosystem." Detail the 100,000 deterministic `claims_master.csv` records, the simulated anomalies, and why SHA-256 immutability is the cornerstone of the regression suite.

---

## PRESENTATION GENERATION RULES FOR CLAUDE:
1. **No Hallucination**: Do not estimate metrics. Do not round 218 tests to 200. Do not round 5.82s latency.
2. **No Vaporware**: Do not design slides for Kubernetes, Airflow, or Vector Databases. They do not exist in this architecture.
3. **No Frontend**: Do not show UI mockups. The UI is explicitly blocked pending the Alert Gate.
4. **Tone**: Highly technical, evidence-based, data-engineering focused.
