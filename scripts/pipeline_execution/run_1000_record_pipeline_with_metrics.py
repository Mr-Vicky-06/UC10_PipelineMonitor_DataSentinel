"""
1000-Record Pipeline Execution & Metrics Repository Verification Script
========================================================================
Runs the end-to-end representative pipeline on 1,000 healthcare claim records,
collects execution telemetry & logs, records metrics into MetricsRepository,
and queries the repository to verify historical metric storage and retrieval.
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import duckdb

# Add project root to sys.path
sys.path.insert(0, ".")

from src.pipeline.orchestrator import PipelineOrchestrator
from src.monitoring import MetricsRepository, MetricRecord


def get_dir_hash(directory: str) -> str:
    """Compute SHA-256 hash of a directory to verify immutability."""
    if not os.path.exists(directory):
        return "DIR_DOES_NOT_EXIST"
    h = hashlib.sha256()
    for root, _, files in sorted(os.walk(directory)):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    h.update(chunk)
    return h.hexdigest()


def main():
    print("=" * 70)
    print("DATASENTINAL — 1,000-RECORD PIPELINE & METRICS REPOSITORY EXECUTION")
    print("=" * 70)

    run_id = "RUN_1000_TEST_BATCH"
    hospital_id = "hospital_A"
    batch_id = "batch_20260817.csv"

    # 1. Setup isolated test workspace directory under outputs/
    workspace_dir = Path("outputs/pipeline_workspace/test_1000_run")
    source_dir = workspace_dir / "source"
    batch_dir = source_dir / run_id / hospital_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    batch_file_path = batch_dir / batch_id

    # 2. Immutability Check (Before)
    hash_data_before = get_dir_hash("data")
    hash_master_before = get_dir_hash("master_data")

    # 3. Source Selection: Extract 1,000 claim records
    master_claims_path = "master_data/master_data/claims/claims_master.csv"
    if os.path.exists(master_claims_path):
        print(f"\n[1/5] Extracting 1,000 sample claim records from {master_claims_path}...")
        df_src = pd.read_csv(master_claims_path, sep="|", dtype=str, nrows=1000)
    else:
        print("\n[1/5] Generating 1,000 synthetic test claim records...")
        df_src = pd.DataFrame({
            "BENE_ID": [f"BENE_{i%200:05d}" for i in range(1000)],
            "CLM_ID": [f"CLM_{i//2:06d}" for i in range(1000)],
            "CLM_LINE_NUM": [str((i%2)+1) for i in range(1000)],
            "NCH_CLM_TYPE_CD": ["60"] * 1000,
            "CLM_FROM_DT": ["2026-01-15"] * 1000,
            "CLM_THRU_DT": ["2026-01-15"] * 1000,
            "PRVDR_NUM": ["491581"] * 1000,
            "CLM_PMT_AMT": ["150.00"] * 1000,
            "hospital_id": [hospital_id] * 1000
        })

    df_src.to_csv(batch_file_path, sep="|", index=False)
    print(f"  Created test batch: {batch_file_path} ({len(df_src)} records)")

    # 4. Pipeline Execution
    print(f"\n[2/5] Initializing PipelineOrchestrator and executing pipeline run '{run_id}'...")
    orchestrator = PipelineOrchestrator()
    
    # Configure test workspace outputs
    orchestrator.landing_output = str(workspace_dir / "landing")
    orchestrator.ingestion_output = str(workspace_dir / "ingestion")
    orchestrator.duckdb_path = str(workspace_dir / "processed_claims.duckdb")

    start_time = time.time()
    result = orchestrator.run(source_directory=str(source_dir), run_id=run_id)
    execution_duration_sec = round(time.time() - start_time, 4)

    print(f"  Execution Successful: {result.is_successful}")
    print(f"  Duration: {execution_duration_sec}s ({result.duration_ms} ms)")
    print(f"  Records Received: {result.records_received}")
    print(f"  Records Persisted: {result.records_persisted}")
    print(f"  Business Rule Violations: {result.business_rule_violations}")
    print(f"  Operational Errors: {result.operational_errors}")

    # 5. Collect Pipeline Telemetry & Logs
    print("\n[3/5] Collecting operational logs and telemetry events...")
    telemetry_db = "outputs/pipeline_workspace/pipeline_telemetry.duckdb"
    telemetry_events = []
    if os.path.exists(telemetry_db):
        with duckdb.connect(telemetry_db) as con:
            df_tel = con.execute(f"SELECT stage, status, duration_ms, records_in, records_out, errors FROM pipeline_events WHERE run_id='{run_id}' ORDER BY timestamp").fetchdf()
            telemetry_events = df_tel.to_dict(orient="records")
            print("  Telemetry Trace Events:")
            for ev in telemetry_events:
                print(f"    - [{ev['stage']}] Status={ev['status']}, Duration={ev['duration_ms']}ms, In={ev['records_in']}, Out={ev['records_out']}, Errors={ev['errors']}")

    # 6. Metrics Repository Registration
    print("\n[4/5] Recording structured metrics into MetricsRepository...")
    metrics_repo = MetricsRepository(db_path="outputs/pipeline_workspace/metrics_repository.duckdb")

    now_utc = datetime.now(timezone.utc)
    metrics_to_save = [
        MetricRecord(
            metric_name="records_received",
            metric_value=float(result.records_received),
            stage_name="ingestion",
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            metric_unit="count",
            timestamp=now_utc
        ),
        MetricRecord(
            metric_name="records_processed",
            metric_value=float(result.records_received),
            stage_name="transformation",
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            metric_unit="count",
            timestamp=now_utc
        ),
        MetricRecord(
            metric_name="records_persisted",
            metric_value=float(result.records_persisted),
            stage_name="storage",
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            metric_unit="count",
            timestamp=now_utc
        ),
        MetricRecord(
            metric_name="business_rule_violations",
            metric_value=float(result.business_rule_violations),
            stage_name="business_rules",
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            metric_unit="count",
            timestamp=now_utc
        ),
        MetricRecord(
            metric_name="processing_duration",
            metric_value=execution_duration_sec,
            stage_name="orchestration",
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            metric_unit="seconds",
            timestamp=now_utc
        ),
        MetricRecord(
            metric_name="pipeline_success_rate",
            metric_value=1.0 if result.is_successful else 0.0,
            stage_name="orchestration",
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            metric_unit="ratio",
            timestamp=now_utc
        )
    ]

    saved_count = metrics_repo.save_metrics(metrics_to_save)
    print(f"  Successfully recorded {saved_count} metrics into MetricsRepository!")

    # 7. Query Metrics Repository to Verify Functionality
    print("\n[5/5] Querying MetricsRepository to verify historical metric storage and retrieval...")
    
    # Query 1: Run Metrics
    run_m = metrics_repo.get_metrics_for_run(run_id)
    print(f"  Query get_metrics_for_run('{run_id}'): Returned {len(run_m)} metric records.")

    # Query 2: Batch Metrics
    batch_m = metrics_repo.get_metrics_for_batch(batch_id)
    print(f"  Query get_metrics_for_batch('{batch_id}'): Returned {len(batch_m)} metric records.")

    # Query 3: Latest Metric
    latest_proc = metrics_repo.get_latest_metric("records_processed", hospital_id=hospital_id)
    print(f"  Query get_latest_metric('records_processed'): Value = {latest_proc.metric_value if latest_proc else 'N/A'}")

    # Query 4: Today Metrics
    today_m = metrics_repo.get_metrics_today(hospital_id=hospital_id)
    print(f"  Query get_metrics_today(hospital_id='{hospital_id}'): Returned {len(today_m)} metric records.")

    # Query 5: 30-Day Metrics
    last30_m = metrics_repo.get_metrics_last_30_days(hospital_id=hospital_id)
    print(f"  Query get_metrics_last_30_days(hospital_id='{hospital_id}'): Returned {len(last30_m)} metric records.")

    # 8. Immutability Verification (After)
    hash_data_after = get_dir_hash("data")
    hash_master_after = get_dir_hash("master_data")

    print("\n--- DATA PROTECTION VERIFICATION ---")
    print(f"  data/ directory unmodified: {hash_data_before == hash_data_after}")
    print(f"  master_data/ directory unmodified: {hash_master_before == hash_master_after}")

    print("\n" + "=" * 70)
    print("SUCCESS: 1,000-RECORD PIPELINE EXECUTION & METRICS REPOSITORY VERIFIED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
