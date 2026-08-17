import duckdb
import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split

def generate_workload_scale(base_df, scale):
    df = base_df.copy()
    multiplier = scale / max(df['claim_volume'].mean(), 1)
    df['claim_volume'] = df['claim_volume'] * multiplier
    df['processing_duration'] = df['processing_duration'] * (multiplier ** 0.8)
    df['throughput'] = df['claim_volume'] / df['processing_duration'].clip(lower=1)
    df['claim_amount_mean'] = 100 + np.random.normal(0, 10, len(df))
    df['failure_rate'] = df.get('failed_records', 0) / df['claim_volume'].clip(lower=1)
    return df

def generate_data():
    print("=== GENERATING ACCEPTANCE DATA ===")
    
    con = duckdb.connect('outputs/pipeline_workspace/pipeline_telemetry.duckdb')
    query = """
    SELECT 
        batch_id,
        hospital_id,
        MAX(timestamp) as timestamp,
        SUM(CASE WHEN stage='INGESTION' AND status='COMPLETED' THEN records_in ELSE 0 END) as claim_volume,
        SUM(CASE WHEN status='COMPLETED' THEN duration_ms ELSE 0 END) as processing_duration,
        SUM(records_failed) as failed_records
    FROM pipeline_events
    WHERE batch_id IS NOT NULL AND batch_id != ''
    GROUP BY batch_id, hospital_id
    """
    df_raw = con.execute(query).df()
    df_raw['throughput'] = df_raw['claim_volume'] / df_raw['processing_duration'].clip(lower=1)
    df_raw['failure_rate'] = df_raw['failed_records'] / df_raw['claim_volume'].clip(lower=1)
    df_raw.fillna(0, inplace=True)
    
    # Base split (Deterministic)
    train_raw, test_raw = train_test_split(df_raw, test_size=0.4, random_state=42)
    val_raw, test_raw = train_test_split(test_raw, test_size=0.5, random_state=42)
    
    scales = [100, 500, 1000, 5000]
    
    # Create TRAIN
    train_dfs = []
    for scale in scales:
        train_dfs.append(generate_workload_scale(train_raw, scale))
    train_df = pd.concat(train_dfs, ignore_index=True)
    train_df['is_anomaly'] = 0
    train_df['anomaly_type'] = 'none'
    train_df['scale'] = np.repeat(scales, len(train_raw))
    
    # Create VALIDATION
    val_dfs = []
    for scale in scales:
        df_norm = generate_workload_scale(val_raw, scale)
        df_norm['is_anomaly'] = 0
        df_norm['anomaly_type'] = 'none'
        df_norm['scale'] = scale
        val_dfs.append(df_norm)
    val_df = pd.concat(val_dfs, ignore_index=True)
    
    # Create TEST
    test_dfs = []
    for scale in scales:
        df_norm = generate_workload_scale(test_raw, scale)
        df_norm['is_anomaly'] = 0
        df_norm['anomaly_type'] = 'none'
        df_norm['scale'] = scale
        test_dfs.append(df_norm)
        
        # Inject Volume Drop
        df_drop = df_norm.copy()
        df_drop['claim_volume'] = df_drop['claim_volume'] * 0.1
        df_drop['is_anomaly'] = 1
        df_drop['anomaly_type'] = 'volume_drop'
        test_dfs.append(df_drop)
        
        # Inject Volume Spike
        df_spike = df_norm.copy()
        df_spike['claim_volume'] = df_spike['claim_volume'] * 10
        df_spike['is_anomaly'] = 1
        df_spike['anomaly_type'] = 'volume_spike'
        test_dfs.append(df_spike)
        
        # Inject Operational Latency Spike
        df_lat = df_norm.copy()
        df_lat['processing_duration'] = df_lat['processing_duration'] * 50
        df_lat['throughput'] = df_lat['claim_volume'] / df_lat['processing_duration'].clip(lower=1)
        df_lat['is_anomaly'] = 1
        df_lat['anomaly_type'] = 'latency_spike'
        test_dfs.append(df_lat)
        
        # Inject Distribution Shift
        df_dist = df_norm.copy()
        df_dist['claim_amount_mean'] = df_dist['claim_amount_mean'] * 3 # Significant shift
        df_dist['is_anomaly'] = 1
        df_dist['anomaly_type'] = 'distribution_shift'
        test_dfs.append(df_dist)
        
    test_df = pd.concat(test_dfs, ignore_index=True)
    
    os.makedirs('outputs/ml/acceptance/data', exist_ok=True)
    train_df.to_csv('outputs/ml/acceptance/data/train.csv', index=False)
    val_df.to_csv('outputs/ml/acceptance/data/validation.csv', index=False)
    test_df.to_csv('outputs/ml/acceptance/data/test.csv', index=False)
    
    print(f"Train size: {len(train_df)} (Anomalies: {train_df['is_anomaly'].sum()})")
    print(f"Val size: {len(val_df)} (Anomalies: {val_df['is_anomaly'].sum()})")
    print(f"Test size: {len(test_df)} (Anomalies: {test_df['is_anomaly'].sum()})")

if __name__ == "__main__":
    generate_data()
