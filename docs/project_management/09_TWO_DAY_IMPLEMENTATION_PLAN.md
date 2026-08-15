# 09 Two-Day Implementation Plan

## Day 1: Foundation & Data Quality (Hours 1-8)
- **T+0:00** Initialize DuckDB instance to point to `DataBase/Beneficiary`, `DataBase/Claims/inpatient`, and `DataBase/pde.csv` using zero-copy Parquet/CSV reading.
- **T+2:00** Build lightweight python Pipeline Harness that iterates through the data in simulated "daily" batches (grouping by `SRVC_DT`).
- **T+4:00** Implement Great Expectations / SQL-based Rule Engine for DQ Checks (Nulls, Referential Integrity on `BENE_ID`).
- **T+6:00** Implement Statistical baseline module (Rolling Median + MAD on batch volume).

## Day 2: ML, RAG & UI (Hours 9-16)
- **T+8:00** Train `scikit-learn` Isolation Forest on pipeline metadata features (`volume`, `duration`, `dq_failure_rate`).
- **T+10:00** Build Evidence Fusion layer (Python dictionary/JSON merging DQ + Stats + ML into one Event).
- **T+12:00** Implement SLA risk calculator and simple RCA heuristics (Decision tree mapping DQ rules to stages).
- **T+14:00** Connect RAG pipeline: Send structured Anomaly Event JSON to LLM prompt alongside standard operating procedures.
- **T+16:00** Finalize Streamlit UI for hackathon demonstration.
