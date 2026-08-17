import pandas as pd
import numpy as np
import os
import json

def load_real_data(file_path: str, n_records: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Reads a chunk of real claim lines."""
    df = pd.read_csv(file_path, sep='|', nrows=n_records)
    # Ensure it's deterministic
    np.random.seed(seed)
    return df

def apply_anomalies(df: pd.DataFrame, num_anomalous: int = 300) -> tuple:
    """Applies anomalies to a subset of records."""
    df_adv = df.copy()
    
    # 700 normal, 300 anomalous
    anomalous_indices = np.random.choice(df_adv.index, size=num_anomalous, replace=False)
    
    ground_truth = []
    
    # Categories:
    # A. Extreme payment amount (60)
    # B. Negative payment (60)
    # C. Zero payment (60)
    # D. Extreme length of stay (60)
    # E. Impossible chronology (60)
    
    np.random.shuffle(anomalous_indices)
    categories = [
        ("EXTREME_AMOUNT", 60),
        ("NEGATIVE_AMOUNT", 60),
        ("ZERO_AMOUNT", 60),
        ("EXTREME_LOS", 60),
        ("IMPOSSIBLE_CHRONOLOGY", 60)
    ]
    
    start_idx = 0
    for cat_name, count in categories:
        indices = anomalous_indices[start_idx:start_idx+count]
        start_idx += count
        
        for idx in indices:
            row = df_adv.loc[idx].copy()
            orig_vals = row.to_dict()
            
            if cat_name == "EXTREME_AMOUNT":
                # Multiply PMT_AMT by 100-500
                df_adv.at[idx, 'CLM_PMT_AMT'] = float(row['CLM_PMT_AMT']) * np.random.uniform(100, 500)
            elif cat_name == "NEGATIVE_AMOUNT":
                # Negative PMT_AMT
                df_adv.at[idx, 'CLM_PMT_AMT'] = -abs(float(row['CLM_PMT_AMT']) or 1000)
            elif cat_name == "ZERO_AMOUNT":
                df_adv.at[idx, 'CLM_PMT_AMT'] = 0.0
            elif cat_name == "EXTREME_LOS":
                from_dt = pd.to_datetime(row['CLM_FROM_DT'], format='%Y%m%d', errors='coerce')
                if pd.isna(from_dt):
                    from_dt = pd.to_datetime('20230101', format='%Y%m%d')
                thru_dt = from_dt + pd.Timedelta(days=np.random.randint(1000, 2000))
                df_adv.at[idx, 'CLM_THRU_DT'] = thru_dt.strftime('%Y%m%d')
            elif cat_name == "IMPOSSIBLE_CHRONOLOGY":
                from_dt = pd.to_datetime(row['CLM_FROM_DT'], format='%Y%m%d', errors='coerce')
                if pd.isna(from_dt):
                    from_dt = pd.to_datetime('20230101', format='%Y%m%d')
                thru_dt = from_dt - pd.Timedelta(days=np.random.randint(10, 100))
                df_adv.at[idx, 'CLM_THRU_DT'] = thru_dt.strftime('%Y%m%d')
                
            mod_vals = df_adv.loc[idx].to_dict()
            
            gt_record = {
                "record_id": str(idx),
                "CLM_ID": str(row.get('CLM_ID', '')),
                "CLM_LINE_NUM": str(row.get('CLM_LINE_NUM', '')),
                "anomaly_category": cat_name,
                "original_values": json.dumps(orig_vals, default=str),
                "modified_values": json.dumps(mod_vals, default=str),
                "ground_truth_anomaly": 1
            }
            ground_truth.append(gt_record)
            
    # Add normal records to ground truth
    normal_indices = set(df_adv.index) - set(anomalous_indices)
    for idx in normal_indices:
        row = df_adv.loc[idx]
        gt_record = {
            "record_id": str(idx),
            "CLM_ID": str(row.get('CLM_ID', '')),
            "CLM_LINE_NUM": str(row.get('CLM_LINE_NUM', '')),
            "anomaly_category": "NORMAL",
            "original_values": json.dumps(row.to_dict(), default=str),
            "modified_values": json.dumps(row.to_dict(), default=str),
            "ground_truth_anomaly": 0
        }
        ground_truth.append(gt_record)
        
    df_ground_truth = pd.DataFrame(ground_truth)
    return df_adv, df_ground_truth

def main():
    source_file = "master_data/claims/claims_master.csv"
    output_dir = "outputs/ml/row_level/dataset"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading 1,000 records from {source_file}...")
    df_normal = load_real_data(source_file, n_records=1000)
    
    # Save the normal isolated dataset
    df_normal.to_csv(f"{output_dir}/claims_1000_normal.csv", index=False)
    
    print("Applying 30% controlled anomalies...")
    df_adv, df_gt = apply_anomalies(df_normal, num_anomalous=300)
    
    df_adv.to_csv(f"{output_dir}/claims_1000_adversarial.csv", index=False)
    df_gt.to_csv(f"{output_dir}/ground_truth.csv", index=False)
    
    print(f"Dataset generated in {output_dir}")
    print(f"Total adversarial records: {len(df_adv)}")
    print(f"Anomalies in ground truth: {df_gt['ground_truth_anomaly'].sum()}")
    
if __name__ == "__main__":
    main()
