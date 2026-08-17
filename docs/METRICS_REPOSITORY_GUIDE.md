# DataSentinal — Metrics Repository Guide

## Overview
The **Metrics Repository** is a dedicated, isolated component of the DataSentinal Monitoring System (Layer 2). It provides structured, persistent historical storage and querying capabilities for pipeline, data quality, transformation, and operational observability metrics.

---

## Key Responsibilities

### What It Stores
- **Pipeline Metrics:** `records_received`, `records_processed`, `records_rejected`, `records_failed`, `processing_duration`, `pipeline_success_rate`
- **Batch Metrics:** `batch_records`, `batch_processing_time`, `batch_status`, `batch_failure_count`
- **Data Quality Metrics:** `null_count`, `duplicate_count`, `invalid_date_count`, `invalid_code_count`, `schema_error_count`
- **Observability Metrics:** `freshness_seconds`, `processing_latency`, `volume_change`, `schema_change_count`
- **Transformation Metrics:** `transformation_records_in`, `transformation_records_out`, `transformation_error_count`, `transformation_duration`

### What It Does NOT Do
- It does **NOT** calculate metrics (upstream engines pass metric measurements).
- It does **NOT** perform anomaly detection or RCA (AI/ML Detection Engine responsibility).
- It does **NOT** modify or transform raw healthcare datasets in `data/` or `master_data/`.

---

## Architecture & Module Structure

```
src/
└── monitoring/
    ├── __init__.py
    ├── models.py                # MetricRecord dataclass & MetricsRepositoryError
    └── metrics_repository.py    # MetricsRepository class
tests/
└── monitoring/
    ├── test_metrics_repository.py   # Unit test suite (20 scenarios)
    └── test_metrics_integration.py  # Integration test suite
```

---

## Database Technology & Configuration

- **Database Backend:** DuckDB / ANSI SQL compliant embedded store (configurable to PostgreSQL connection URL via `METRICS_DB_PATH` or `DATABASE_URL` environment variables).
- **Default Database Path:** `outputs/pipeline_workspace/metrics_repository.duckdb`
- **In-Memory Testing:** `:memory:`

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS metrics (
    metric_id VARCHAR PRIMARY KEY,
    timestamp TIMESTAMP,
    run_id VARCHAR,
    batch_id VARCHAR,
    hospital_id VARCHAR,
    stage_name VARCHAR,
    metric_name VARCHAR,
    metric_value DOUBLE,
    metric_unit VARCHAR,
    status VARCHAR,
    source VARCHAR,
    dimensions VARCHAR  -- JSON string of flexible dimension tags
);

-- Performance Indexes
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX idx_metrics_run_batch ON metrics(run_id, batch_id);
CREATE INDEX idx_metrics_lookup ON metrics(hospital_id, stage_name, metric_name);
```

---

## Repository API Methods

| Method | Description |
|--------|-------------|
| `initialize_schema()` | Creates database tables and indexes if missing |
| `save_metric(metric)` | Persists a single `MetricRecord` |
| `save_metrics(metrics)` | Bulk persists a list of `MetricRecord` items in one transaction |
| `get_latest_metric(metric_name, ...)` | Retrieves the most recent `MetricRecord` |
| `get_metrics_for_run(run_id)` | Retrieves all metrics for a given execution run |
| `get_metrics_for_batch(batch_id)` | Retrieves all metrics for a given batch |
| `get_metrics_for_stage(stage_name)` | Retrieves all metrics for a pipeline stage |
| `get_metrics_since(start_time, ...)` | Queries metrics recorded since a given timestamp |
| `get_daily_metrics(target_date, ...)` | Queries metrics for a specific calendar day |
| `get_historical_metrics(start_time, end_time, ...)` | Queries metrics within a timestamp range |
| `get_metrics_today(...)` | Convenience window for today's metrics |
| `get_metrics_yesterday(...)` | Convenience window for yesterday's metrics |
| `get_metrics_last_30_days(...)` | Convenience window for the last 30 days |
| `get_metrics_last_6_months(...)` | Convenience window for the last 6 months (180 days) |
| `health_check()` | Verifies database connectivity and health |

---

## Integration Contract

Upstream engines (Data Quality Engine, Telemetry Logger, Observability Engine) interact with `MetricsRepository` as follows:

```python
from src.monitoring import MetricsRepository, MetricRecord

repo = MetricsRepository()

# 1. Store a Metric
record = MetricRecord(
    metric_name="records_processed",
    metric_value=1000.0,
    stage_name="transformation",
    run_id="RUN_20260817_001",
    batch_id="batch_20260817",
    hospital_id="hospital_A",
    metric_unit="count"
)
repo.save_metric(record)

# 2. Query Historical Metrics for AI/ML Anomaly Detection
historical_metrics = repo.get_metrics_last_30_days(hospital_id="hospital_A")
```

---

## How to Run Tests

```bash
# Run Unit Tests (20 Scenarios)
python -m unittest tests.monitoring.test_metrics_repository -v

# Run Integration Tests
python -m unittest tests.monitoring.test_metrics_integration -v
```
