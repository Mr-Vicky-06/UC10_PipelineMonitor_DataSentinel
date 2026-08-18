import pandas as pd
import numpy as np
import os

def generate_datasets():
    df = pd.read_csv("outputs/ml/v3/telemetry_features.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 80/20 chronological split
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    eval_df = df.iloc[split_idx:].copy()
    
    # We will use eval_df as our controlled normal workloads
    eval_df['is_anomalous'] = 0
    eval_df['injected_anomaly_type'] = 'NONE'
    
    # Let's create anomalous copies of eval_df
    anom_dfs = []
    
    for i, row in eval_df.iterrows():
        # 1. 50% Volume Drop
        row_drop = row.copy()
        row_drop['claim_volume'] *= 0.5
        row_drop['records_in'] *= 0.5
        row_drop['throughput'] *= 0.5 # Since duration stays the same, throughput drops
        row_drop['normalized_volume_zscore'] = (row_drop['claim_volume'] - row_drop['hospital_vol_mean']) / row_drop['hospital_vol_std']
        row_drop['is_anomalous'] = 1
        row_drop['injected_anomaly_type'] = 'VOLUME_DROP_50'
        anom_dfs.append(pd.DataFrame([row_drop]))
        
        # 2. 100% Volume Spike
        row_spike = row.copy()
        row_spike['claim_volume'] *= 2.0
        row_spike['records_in'] *= 2.0
        row_spike['throughput'] *= 2.0
        row_spike['normalized_volume_zscore'] = (row_spike['claim_volume'] - row_spike['hospital_vol_mean']) / row_spike['hospital_vol_std']
        row_spike['is_anomalous'] = 1
        row_spike['injected_anomaly_type'] = 'VOLUME_SPIKE_100'
        anom_dfs.append(pd.DataFrame([row_spike]))
        
        # 3. Latency Degradation (5x slower)
        row_lat = row.copy()
        row_lat['duration_ms'] *= 5.0
        row_lat['processing_duration'] *= 5.0
        row_lat['throughput'] = row_lat['records_in'] / (row_lat['processing_duration'] / 1000.0) if row_lat['processing_duration'] > 0 else 0
        row_lat['is_anomalous'] = 1
        row_lat['injected_anomaly_type'] = 'LATENCY_SPIKE'
        anom_dfs.append(pd.DataFrame([row_lat]))
        
        # 4. Failure Rate Increase
        row_fail = row.copy()
        row_fail['failure_rate'] = 0.15 # 15% failure rate
        row_fail['is_anomalous'] = 1
        row_fail['injected_anomaly_type'] = 'FAILURE_SPIKE'
        anom_dfs.append(pd.DataFrame([row_fail]))
        
    eval_anom_df = pd.concat(anom_dfs, ignore_index=True)
    
    # Save datasets
    train_df.to_csv("outputs/ml/v3/telemetry_train.csv", index=False)
    eval_df.to_csv("outputs/ml/v3/telemetry_eval_normal.csv", index=False)
    eval_anom_df.to_csv("outputs/ml/v3/telemetry_eval_anomalous.csv", index=False)
    
    print(f"Train (Real): {len(train_df)} rows")
    print(f"Eval Normal (Derived): {len(eval_df)} rows")
    print(f"Eval Anomalous (Derived): {len(eval_anom_df)} rows")
    
if __name__ == "__main__":
    generate_datasets()
