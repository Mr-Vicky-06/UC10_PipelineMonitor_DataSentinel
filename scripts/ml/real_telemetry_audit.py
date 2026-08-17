import duckdb
import pandas as pd
import json

def audit_real_telemetry():
    con = duckdb.connect('outputs/pipeline_workspace/pipeline_telemetry.duckdb')
    
    query = """
    SELECT 
        batch_id,
        hospital_id,
        MAX(timestamp) as last_seen,
        SUM(CASE WHEN stage='INGESTION' AND status='COMPLETED' THEN records_in ELSE 0 END) as claim_volume,
        SUM(CASE WHEN status='COMPLETED' THEN duration_ms ELSE 0 END) as processing_duration,
        SUM(records_failed) as failed_records,
        SUM(violations_count) as total_violations,
        COUNT(*) as events_in_batch
    FROM pipeline_events
    WHERE batch_id IS NOT NULL AND batch_id != ''
    GROUP BY batch_id, hospital_id
    """
    
    df_batches = con.execute(query).df()
    
    total_events = con.execute("SELECT COUNT(*) FROM pipeline_events").fetchone()[0]
    total_runs = con.execute("SELECT COUNT(DISTINCT run_id) FROM pipeline_events").fetchone()[0]
    total_batches = df_batches['batch_id'].nunique()
    total_hospitals = df_batches['hospital_id'].nunique()
    
    min_time = con.execute("SELECT MIN(timestamp) FROM pipeline_events").fetchone()[0]
    max_time = con.execute("SELECT MAX(timestamp) FROM pipeline_events").fetchone()[0]
    
    print("==================================================")
    print("HISTORICAL TELEMETRY AUDIT")
    print("==================================================")
    print(f"Total pipeline runs: {total_runs}")
    print(f"Total batches: {total_batches}")
    print(f"Total hospitals: {total_hospitals}")
    print(f"Total observations (events): {total_events}")
    print(f"Chronological range: {min_time} to {max_time}")
    print(f"Observations per run: {total_events / total_runs:.2f}" if total_runs else 0)
    print(f"Observations per hospital: {total_events / total_hospitals:.2f}" if total_hospitals else 0)
    print(f"Observations per batch: {total_events / total_batches:.2f}" if total_batches else 0)
    
    print("\nDISTRIBUTION STATISTICS (REAL OBSERVED TELEMETRY)")
    
    # Calculate derived metrics
    df_batches['throughput'] = df_batches['claim_volume'] / df_batches['processing_duration'].clip(lower=1)
    df_batches['failure_rate'] = df_batches['failed_records'] / df_batches['claim_volume'].clip(lower=1)
    df_batches['duplicate_rate'] = df_batches['total_violations'] / df_batches['claim_volume'].clip(lower=1)
    
    print("\nClaim Volume:")
    print(df_batches['claim_volume'].describe())
    
    print("\nProcessing Duration (ms):")
    print(df_batches['processing_duration'].describe())
    
    print("\nThroughput (claims/ms):")
    print(df_batches['throughput'].describe())
    
    print("\nFailure Rate:")
    print(df_batches['failure_rate'].describe())
    
    print("==================================================")
    print("BASELINE MISMATCH ANALYSIS")
    print("==================================================")
    print("SIMULATED TRAINING DISTRIBUTION expected ~5,000 claims/batch.")
    print(f"REAL OBSERVED TELEMETRY average is {df_batches['claim_volume'].mean():.2f} claims/batch.")
    print("Difference represents normal development/test workload constraints (1000 records per test file) vs simulated production-scale (5000 records).")

if __name__ == "__main__":
    audit_real_telemetry()
