import duckdb
import pandas as pd
import numpy as np
import os

def load_telemetry(db_path: str = "outputs/pipeline_workspace/pipeline_telemetry.duckdb") -> pd.DataFrame:
    """Extracts raw pipeline events from DuckDB."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Telemetry database not found at {db_path}")
        
    con = duckdb.connect(db_path)
    # Fetch relevant columns
    df = con.execute("""
        SELECT 
            run_id, hospital_id, batch_id, timestamp, stage, status, 
            duration_ms, records_in, errors 
        FROM pipeline_events
        ORDER BY timestamp ASC
    """).df()
    con.close()
    return df

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Applies workload-aware feature engineering."""
    # Ensure numerics
    df['duration_ms'] = pd.to_numeric(df['duration_ms'], errors='coerce').fillna(0)
    df['records_in'] = pd.to_numeric(df['records_in'], errors='coerce').fillna(0)
    df['errors'] = pd.to_numeric(df['errors'], errors='coerce').fillna(0)
    
    # Base features
    df['claim_volume'] = df['records_in']
    df['processing_duration'] = df['duration_ms']
    df['throughput'] = np.where(df['duration_ms'] > 0, df['records_in'] / (df['duration_ms'] / 1000.0), 0)
    df['failure_rate'] = np.where(df['records_in'] > 0, df['errors'] / df['records_in'], 0)
    
    # Workload Bands
    conditions = [
        df['claim_volume'] <= 100,
        (df['claim_volume'] > 100) & (df['claim_volume'] <= 500),
        (df['claim_volume'] > 500) & (df['claim_volume'] <= 1000),
        df['claim_volume'] > 1000
    ]
    choices = ['MICRO', 'SMALL', 'MEDIUM', 'LARGE']
    df['workload_band'] = np.select(conditions, choices, default='UNKNOWN')
    
    # Normalization (Hospital relative volume z-score)
    df['hospital_vol_mean'] = df.groupby('hospital_id')['claim_volume'].transform('mean')
    df['hospital_vol_std'] = df.groupby('hospital_id')['claim_volume'].transform('std').replace(0, 1)
    df['normalized_volume_zscore'] = (df['claim_volume'] - df['hospital_vol_mean']) / df['hospital_vol_std']
    
    return df

if __name__ == "__main__":
    raw_df = load_telemetry()
    print(f"Loaded {len(raw_df)} real telemetry records.")
    feat_df = create_features(raw_df)
    
    os.makedirs("outputs/ml/v3", exist_ok=True)
    feat_df.to_csv("outputs/ml/v3/telemetry_features.csv", index=False)
    print("Features extracted and saved to outputs/ml/v3/telemetry_features.csv")
