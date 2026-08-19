import os
import sqlite3
import duckdb
import pandas as pd

# Paths
WORKSPACE_DIR = r"d:\UC10_Data_Quality_Pipeline\outputs\pipeline_workspace"
TELEMETRY_DB = os.path.join(WORKSPACE_DIR, "pipeline_telemetry.duckdb")
OUTPUTS_DIR = r"d:\UC10_Data_Quality_Pipeline\outputs"
ANALYTICS_DB = os.path.join(OUTPUTS_DIR, "analytics.sqlite3")

def build_analytics_layer():
    print(f"Connecting to authoritative telemetry: {TELEMETRY_DB}")
    if not os.path.exists(TELEMETRY_DB):
        print("ERROR: Telemetry database not found!")
        return
        
    con_duck = duckdb.connect(TELEMETRY_DB, read_only=True)
    
    # We will build exactly the analytics required for D0-B:
    # 1. pipeline_runs_analytics
    # 2. pipeline_stage_metrics
    # 3. pipeline_events_analytics
    
    # Query 1: pipeline_events_analytics (straight copy for granular panels)
    print("Extracting pipeline events...")
    df_events = con_duck.execute("SELECT * FROM pipeline_events").df()
    
    # Query 2: pipeline_runs_analytics
    # Aggregate to run level. We use deterministic chronological derivation.
    print("Aggregating pipeline runs...")
    query_runs = """
    WITH RankedEvents AS (
        SELECT 
            run_id,
            status,
            timestamp,
            duration_ms,
            ROW_NUMBER() OVER (PARTITION BY run_id ORDER BY timestamp DESC) as rn
        FROM pipeline_events
    ),
    LatestState AS (
        SELECT run_id, status, timestamp as last_event_time
        FROM RankedEvents
        WHERE rn = 1
    ),
    AggregatedMetrics AS (
        SELECT 
            run_id,
            MIN(timestamp) as start_time,
            SUM(COALESCE(duration_ms, 0)) as total_duration_ms,
            MAX(COALESCE(records_in, 0)) as total_records,
            SUM(COALESCE(records_failed, 0)) as total_failures
        FROM pipeline_events
        GROUP BY run_id
    )
    SELECT 
        ls.run_id,
        ls.status,
        am.start_time,
        ls.last_event_time,
        am.total_duration_ms,
        am.total_records,
        am.total_failures
    FROM LatestState ls
    JOIN AggregatedMetrics am ON ls.run_id = am.run_id
    """
    df_runs = con_duck.execute(query_runs).df()
    
    # Query 3: pipeline_stage_metrics
    print("Aggregating stage metrics...")
    query_stages = """
    SELECT 
        stage,
        COUNT(DISTINCT run_id) as run_count,
        SUM(COALESCE(duration_ms, 0)) as total_duration_ms,
        AVG(COALESCE(duration_ms, 0)) as avg_duration_ms,
        SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failure_count
    FROM pipeline_events
    GROUP BY stage
    """
    df_stages = con_duck.execute(query_stages).df()
    
    # Write to SQLite
    print(f"Connecting to analytics serving layer: {ANALYTICS_DB}")
    # Remove existing to ensure clean projection
    if os.path.exists(ANALYTICS_DB):
        os.remove(ANALYTICS_DB)
        
    con_sqlite = sqlite3.connect(ANALYTICS_DB)
    
    # Normalize timestamps to UNIX epoch (seconds) for Grafana frser-sqlite-datasource
    if 'timestamp' in df_events.columns:
        df_events['timestamp'] = pd.to_datetime(df_events['timestamp']).astype('int64') // 10**9
        
    if 'start_time' in df_runs.columns:
        df_runs['start_time'] = pd.to_datetime(df_runs['start_time']).astype('int64') // 10**9
    if 'last_event_time' in df_runs.columns:
        df_runs['last_event_time'] = pd.to_datetime(df_runs['last_event_time']).astype('int64') // 10**9

    print("Writing pipeline_events_analytics...")
    df_events.to_sql("pipeline_events_analytics", con_sqlite, index=False)
    
    print("Writing pipeline_runs_analytics...")
    df_runs.to_sql("pipeline_runs_analytics", con_sqlite, index=False)
    
    print("Writing pipeline_stage_metrics...")
    df_stages.to_sql("pipeline_stage_metrics", con_sqlite, index=False)
    
    con_sqlite.close()
    con_duck.close()
    print("Analytics Serving Layer successfully projected!")

if __name__ == "__main__":
    build_analytics_layer()
