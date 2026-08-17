import duckdb
import pandas as pd

def audit_baselines():
    con = duckdb.connect('outputs/pipeline_workspace/pipeline_telemetry.duckdb')
    
    query = """
    SELECT 
        batch_id,
        hospital_id,
        MAX(timestamp) as last_seen,
        SUM(CASE WHEN stage='INGESTION' AND status='COMPLETED' THEN records_in ELSE 0 END) as claim_volume,
        SUM(CASE WHEN status='COMPLETED' THEN duration_ms ELSE 0 END) as processing_duration,
        SUM(records_failed) as failed_records,
        SUM(violations_count) as total_violations
    FROM pipeline_events
    WHERE batch_id IS NOT NULL AND batch_id != ''
    GROUP BY batch_id, hospital_id
    """
    
    df_batches = con.execute(query).df()
    
    print("=== TELEMETRY BATCH VOLUME DISTRIBUTION ===")
    print(df_batches['claim_volume'].value_counts().sort_index())
    
    print("\n=== HOSPITAL DISTRIBUTIONS ===")
    print(df_batches.groupby('hospital_id')['claim_volume'].agg(['count', 'mean', 'min', 'max']))
    
    # Check if there are different scales.
    # From earlier audit, we saw min 0, max 100.
    
    # Print the raw telemetry summary to use in the final report
    print("\nOPERATING MODEL CONCLUSION:")
    print("The pipeline execution history consists solely of micro-batches (0-100 claims) generated during incremental development and unit testing.")
    print("There is no 5,000-claim 'production' workload in the actual duckdb telemetry yet.")
    print("Therefore, the current operating model is A PURE MICRO-BATCH TESTING WORKLOAD.")
    print("However, the intended future production workload is ~5,000 claims per batch.")
    print("To prevent 100% False Positives across scales, the ML architecture MUST BE WORKLOAD-AWARE.")
    print("We will design models that compute relative metrics (e.g. failure rate instead of absolute failed count) or use piecewise baselines.")

if __name__ == "__main__":
    audit_baselines()
