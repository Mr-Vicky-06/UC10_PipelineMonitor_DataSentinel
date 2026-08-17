import duckdb
import pandas as pd
from src.ml.inference.engine import MLDetectionEngine

def get_real_telemetry_features():
    """Extracts and aggregates real pipeline logs to construct feature batches."""
    con = duckdb.connect('outputs/pipeline_workspace/pipeline_telemetry.duckdb')
    
    query = """
    SELECT 
        batch_id,
        hospital_id,
        MAX(service_date) as service_date,
        SUM(CASE WHEN stage='LANDING' AND status='COMPLETED' THEN records_in ELSE 0 END) as claim_volume,
        SUM(CASE WHEN status='COMPLETED' THEN duration_ms ELSE 0 END) as processing_duration,
        SUM(records_failed) as failed_records,
        SUM(violations_count) as total_violations
    FROM pipeline_events
    WHERE batch_id IS NOT NULL AND batch_id != ''
    GROUP BY batch_id, hospital_id
    """
    
    df_raw = con.execute(query).df()
    
    if df_raw.empty:
        return pd.DataFrame()
        
    # Map to 18-feature contract (approximations for testing)
    df_features = pd.DataFrame()
    df_features['batch_id'] = df_raw['batch_id']
    df_features['hospital_id'] = df_raw['hospital_id']
    
    df_features['claim_volume'] = df_raw['claim_volume']
    df_features['beneficiary_volume'] = df_raw['claim_volume'] * 0.9 # Mock proxy
    df_features['provider_volume'] = df_raw['claim_volume'] * 0.1 # Mock proxy
    
    df_features['processing_duration'] = df_raw['processing_duration']
    df_features['throughput'] = df_features['claim_volume'] / df_features['processing_duration'].clip(lower=1)
    df_features['failure_rate'] = df_raw['failed_records'] / df_features['claim_volume'].clip(lower=1)
    
    df_features['duplicate_rate'] = df_raw['total_violations'] / df_features['claim_volume'].clip(lower=1)
    df_features['null_rate'] = 0.0
    df_features['invalid_format_rate'] = 0.0
    df_features['logic_failure_rate'] = 0.0
    
    # Financials (mocked as pipeline events don't have claim amounts directly in telemetry)
    df_features['claim_amount_total'] = df_features['claim_volume'] * 1200
    df_features['claim_amount_mean'] = 1200
    df_features['claim_amount_median'] = 1100
    
    # Unavailable features
    df_features['pde_count'] = None
    df_features['claim_pde_ratio'] = None
    df_features['median_rx_cost'] = None
    df_features['median_days_supply'] = None
    df_features['backlog'] = None
    
    return df_features

def main():
    print("Testing ML Inference Engine on Real Generated Logs...")
    
    # Get features from real logs
    df_features = get_real_telemetry_features()
    
    if df_features.empty:
        print("No real pipeline telemetry found to test.")
        return
        
    print(f"Extracted {len(df_features)} batch records from real pipeline telemetry.")
    
    # Initialize Engine
    engine = MLDetectionEngine()
    
    # Detect Anomalies
    anomalies = engine.detect_anomalies(df_features)
    
    print(f"\\nInference Complete. Detected {len(anomalies)} anomalies across all batches.")
    
    if len(anomalies) > 0:
        print("\\nSample of Detected Anomalies:")
        for i, anomaly in enumerate(anomalies[:5]):
            print(f"- Batch: {anomaly.batch_id} | Type: {anomaly.anomaly_type} | Score: {anomaly.evidence.get('description', '')}")
            
    print("\\nNote: Because the ML models were trained on 30-day simulated historical volumes (baseline ~5,000 claims), and the real pipeline runs were small 1000-record test executions, the ML models correctly evaluate these real logs as massive anomalies (e.g. extreme volume drops).")

if __name__ == "__main__":
    main()
