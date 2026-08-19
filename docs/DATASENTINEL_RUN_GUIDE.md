# DataSentinel — Step-by-Step Run Guide

> **Complete terminal commands to run the 50,000-record pipeline, monitoring system, and live dashboard visualization end-to-end.**

---

## Prerequisites

| Requirement   | Version    | Check Command                 |
|---------------|------------|-------------------------------|
| Python        | 3.11+      | `python --version`            |
| Node.js       | 18+        | `node --version`              |
| npm           | 9+         | `npm --version`               |
| pip packages  | see below  | `pip list`                    |
| Git           | any        | `git --version`               |

---

## Table of Contents

1. [Install Python Dependencies](#step-1-install-python-dependencies)
2. [Install Frontend Dependencies](#step-2-install-frontend-dependencies)
3. [Run the 50,000-Record Pipeline](#step-3-run-the-50000-record-pipeline)
4. [Build the Analytics Serving Layer](#step-4-build-the-analytics-serving-layer)
5. [Start the Alert Engine (FastAPI Backend)](#step-5-start-the-alert-engine-fastapi-backend)
6. [Start the DataSentinel Dashboard (Next.js Frontend)](#step-6-start-the-datasentinel-dashboard-nextjs-frontend)
7. [Open the Live Dashboard](#step-7-open-the-live-dashboard)
8. [Verify the System](#step-8-verify-the-system)
9. [Shut Down](#step-9-shut-down)

---

## Step 1: Install Python Dependencies

> **WHAT**: Install all Python packages required by the pipeline, ML models, and backend.

Open a terminal at the project root:

```powershell
cd D:\UC10_Data_Quality_Pipeline
```

Install the core pipeline dependencies:

```powershell
pip install pandas duckdb pyarrow pyyaml scikit-learn scipy numpy
```

Install the alert-engine backend dependencies:

```powershell
pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic httpx websockets sendgrid
```

### Verification

```powershell
python -c "import pandas, duckdb, pyarrow, sklearn, scipy; print('All Python dependencies OK')"
```

**Expected Output:**
```
All Python dependencies OK
```

---

## Step 2: Install Frontend Dependencies

> **WHAT**: Install Node.js packages for the Next.js DataSentinel dashboard.

```powershell
cd D:\UC10_Data_Quality_Pipeline\frontend
npm install
```

### Verification

```powershell
npm ls next
```

**Expected Output:**
```
frontend@0.1.0
└── next@15.x.x
```

```powershell
cd D:\UC10_Data_Quality_Pipeline
```

---

## Step 3: Run the 50,000-Record Pipeline

> **WHAT**: Execute the full end-to-end healthcare claims pipeline with 50,000 records from raw data.
>
> **WHY**: This processes inpatient claims through all 6 pipeline stages: Landing → Ingestion → Data Quality/Cleaning → Transformation → Business Rules → DuckDB Storage + Telemetry.
>
> **INPUT**: `data/raw/claims/inpatient.csv` (first 50,000 rows — read-only, never modified)

```powershell
cd D:\UC10_Data_Quality_Pipeline
$env:PYTHONPATH = "."
python scripts/pipeline_execution/run_50k_data_pipeline.py
```

### Expected Output

```
======================================================================
DATASENTINEL 50,000 RECORD PIPELINE EXECUTION & TELEMETRY FUSION
======================================================================

[1/6] Reading 50,000 rows from raw data: data/raw/claims/inpatient.csv...
-> Successfully loaded 50,000 records.

[2/6] Executing Landing Stage...
-> Landed 1 batch(es).

[3/6] Executing Ingestion Stage...
-> Ingested 1 batch(es).

[4/6] Executing Data Quality Rules & Data Cleaning Engine...
-> Cleaning complete. 50,000 records validated. DQ Violations: 2189

[5/6] Executing Healthcare Claims Transformation...
-> Standardized 50,000 records to canonical schema.

[6/6] Executing Business Rules Engine & Telemetry Fusion Store...

======================================================================
SUCCESS: Processed 50,000 records in ~XX.XX seconds!
Throughput: X,XXX.XX rows/sec
======================================================================
```

> **NOTE**: This step takes approximately 2–4 minutes depending on your hardware. The DuckDB databases are written to `outputs/pipeline_workspace/`.

### Artifacts Created

| File                                               | Purpose                            |
|----------------------------------------------------|------------------------------------|
| `outputs/pipeline_workspace/processed_claims.duckdb` | Processed claims + rule results   |
| `outputs/pipeline_workspace/pipeline_telemetry.duckdb` | Pipeline telemetry events       |
| `outputs/pipeline_workspace/run_50k/`              | Intermediate landing/ingestion data |

---

## Step 4: Build the Analytics Serving Layer

> **WHAT**: Convert DuckDB telemetry into an SQLite analytics database that the Next.js dashboard reads.
>
> **WHY**: The frontend API routes read from `outputs/analytics.sqlite3`. This step materializes pipeline_runs, stage metrics, and event data.

```powershell
cd D:\UC10_Data_Quality_Pipeline
$env:PYTHONPATH = "."
python scripts/build_analytics_serving_layer.py
```

### Expected Output

```
Connecting to authoritative telemetry: ...\pipeline_telemetry.duckdb
Extracting pipeline events...
Aggregating pipeline runs...
Aggregating stage metrics...
Writing analytics database to: ...\outputs\analytics.sqlite3
Analytics serving layer built successfully!
```

### Artifacts Created

| File                          | Purpose                                            |
|-------------------------------|----------------------------------------------------|
| `outputs/analytics.sqlite3`  | Dashboard-ready analytics (runs, stages, events)   |

---

## Step 5: Start the Alert Engine (FastAPI Backend)

> **WHAT**: Launch the FastAPI alert engine that provides REST APIs for alert management and email dispatch.
>
> **WHY**: This backend serves the `/api/alerts` endpoints and manages the alert lifecycle (create, acknowledge, resolve, email via SendGrid).

**Open a NEW terminal (Terminal 2):**

```powershell
cd D:\UC10_Data_Quality_Pipeline\alert-engine
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Expected Output

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Verification

Open a browser or use curl:

```powershell
curl http://localhost:8000/docs
```

This should return the FastAPI Swagger UI HTML.

> **IMPORTANT**: Keep this terminal running. Do NOT close it.

---

## Step 6: Start the DataSentinel Dashboard (Next.js Frontend)

> **WHAT**: Launch the Next.js development server that renders the DataSentinel Operations Center and RAG Intelligence workspace.
>
> **WHY**: This is the live monitoring dashboard with real-time pipeline visualization.

**Open a NEW terminal (Terminal 3):**

```powershell
cd D:\UC10_Data_Quality_Pipeline\frontend
npm run dev
```

### Expected Output

```
  ▲ Next.js 15.x.x
  - Local:        http://localhost:3000
  - Environments: .env.local

 ✓ Starting...
 ✓ Ready in Xs
```

> **IMPORTANT**: Keep this terminal running. Do NOT close it.

---

## Step 7: Open the Live Dashboard

> **WHAT**: Access the DataSentinel Operations Center in your browser.

Open your web browser and navigate to:

```
http://localhost:3000
```

### Dashboard Pages

| URL                          | Page                      | Description                                |
|------------------------------|---------------------------|--------------------------------------------|
| `http://localhost:3000`      | Operations Center         | Live pipeline monitoring, KPIs, charts     |
| `http://localhost:3000/rag`  | RAG Intelligence          | AI-assisted investigation & evidence packs |

### What You Should See

**Operations Center:**
- **KPI Cards**: Active Runs, Failed Runs, Active Anomalies, Open Incidents, SLA %
- **Pipeline Execution Ring**: Visual stage-by-stage pipeline progress
- **Monitoring Charts**: Volume trends, DQ violation rates, processing throughput
- **Pipeline Runs Table**: Historical run data with status, duration, record counts
- **Incident Intelligence Panel**: Correlated incident summaries

**RAG Intelligence:**
- **Investigation Console**: Historical RAG analysis logs
- **Evidence Pack Viewer**: Deterministic evidence chains for root cause analysis

---

## Step 8: Verify the System

### 8a. Verify Pipeline Data in DuckDB

```powershell
cd D:\UC10_Data_Quality_Pipeline
python -c "import duckdb; con = duckdb.connect('outputs/pipeline_workspace/pipeline_telemetry.duckdb', read_only=True); print(con.execute('SELECT run_id, stage, status, records_in, records_out, duration_ms FROM pipeline_events ORDER BY timestamp DESC LIMIT 10').df().to_string()); con.close()"
```

### 8b. Verify Analytics Layer

```powershell
python -c "import sqlite3; con = sqlite3.connect('outputs/analytics.sqlite3'); cursor = con.cursor(); tables = cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall(); print('Tables:', [t[0] for t in tables]); [print(f'  {t[0]}: {cursor.execute(f\"SELECT COUNT(*) FROM {t[0]}\").fetchone()[0]} rows') for t in tables]; con.close()"
```

### 8c. Verify Alert Engine API

```powershell
curl http://localhost:8000/api/alerts
```

### 8d. Verify Dashboard is Serving

```powershell
curl -s http://localhost:3000 | Select-String "DataSentinel"
```

---

## Step 9: Shut Down

When you are done with the demonstration:

1. **Terminal 3 (Frontend)**: Press `Ctrl+C` to stop the Next.js server.
2. **Terminal 2 (Alert Engine)**: Press `Ctrl+C` to stop the FastAPI server.
3. **Terminal 1 (Pipeline)**: Already completed (one-shot execution).

---

## Quick Reference — All Commands in Order

```powershell
# === TERMINAL 1: Pipeline & Analytics ===
cd D:\UC10_Data_Quality_Pipeline
$env:PYTHONPATH = "."

# Step 1: Install dependencies
pip install pandas duckdb pyarrow pyyaml scikit-learn scipy numpy
pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic httpx websockets sendgrid

# Step 2: Install frontend dependencies
cd frontend && npm install && cd ..

# Step 3: Run 50K pipeline
python scripts/pipeline_execution/run_50k_data_pipeline.py

# Step 4: Build analytics layer
python scripts/build_analytics_serving_layer.py

# === TERMINAL 2: Alert Engine Backend ===
cd D:\UC10_Data_Quality_Pipeline\alert-engine
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# === TERMINAL 3: Dashboard Frontend ===
cd D:\UC10_Data_Quality_Pipeline\frontend
npm run dev

# === BROWSER ===
# Open http://localhost:3000
```

---

## Troubleshooting

| Issue                                    | Solution                                                    |
|------------------------------------------|-------------------------------------------------------------|
| `ModuleNotFoundError: No module named 'xxx'` | Run `pip install xxx`                                   |
| Port 3000 already in use                 | `npx kill-port 3000` or use `npm run dev -- -p 3001`       |
| Port 8000 already in use                 | `npx kill-port 8000` or change port in uvicorn command      |
| DuckDB file not found                   | Re-run Step 3 (pipeline execution)                          |
| analytics.sqlite3 not found             | Re-run Step 4 (build analytics layer)                       |
| Frontend shows empty dashboard          | Ensure Step 4 completed successfully before starting frontend |
| Pipeline fails at Stage 6               | Check `outputs/pipeline_workspace/` directory exists         |
| `PYTHONPATH` errors                     | Ensure you set `$env:PYTHONPATH = "."` before running scripts |

---

> **Document Version**: 1.0  
> **Last Updated**: 2026-08-19  
> **Project**: DataSentinel / UC10 Data Quality Pipeline
