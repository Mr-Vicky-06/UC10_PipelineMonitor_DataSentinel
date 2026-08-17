import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta

def setup_directories():
    out_dir = Path("outputs/business_rules/evaluation/phase_b")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def generate_evaluation_data():
    np.random.seed(42)
    out_dir = setup_directories()

    # Load 1000 records from master
    df_master = pd.read_csv("master_data/claims/claims_master.csv", sep="|", dtype=str)
    
    df_sample = df_master.sample(n=1050, random_state=42).copy()
    
    df_sample['CLM_FROM_DT'] = '2026-01-01'
    df_sample['CLM_THRU_DT'] = '2026-01-10'
    df_sample['ADMTN_DT'] = '2026-01-01'
    df_sample['CLM_ADMSN_DT'] = '2026-01-01'
    df_sample['NCH_BENE_DSCHRG_DT'] = '2026-01-10'
    df_sample['CLM_PMT_AMT'] = '100.00'
    df_sample['CLM_TOT_CHRG_AMT'] = '500.00'

    df_sample = df_sample.head(1000).reset_index(drop=True)
    
    df_sample['CLM_ID'] = [f"EVAL_CLM_{str(i+1).zfill(6)}" for i in range(1000)]
    df_sample['BENE_ID'] = [f"EVAL_BENE_{str(i+1).zfill(6)}" for i in range(1000)]

    df_clean = df_sample.iloc[:700].copy()
    df_anom = df_sample.iloc[700:1000].copy()

    ground_truth = []

    # Clean Ground Truth
    for _, row in df_clean.iterrows():
        ground_truth.append({
            "evaluation_id": row['CLM_ID'],
            "CLM_ID": row['CLM_ID'],
            "CLM_LINE_NUM": row.get('CLM_LINE_NUM', '1'),
            "expected_BR_DATE_001": "PASS",
            "expected_BR_DATE_002": "PASS",
            "expected_BR_AMT_001": "PASS",
            "expected_BR_AMT_002": "PASS",
            "expected_violation_count": 0,
            "scenario": "CLEAN"
        })

    # Date Chronology
    idx = 0
    for i in range(idx, idx + 75):
        df_anom.loc[df_anom.index[i], 'CLM_FROM_DT'] = '2026-08-20'
        df_anom.loc[df_anom.index[i], 'CLM_THRU_DT'] = '2026-08-15'
        ground_truth.append({
            "evaluation_id": df_anom.iloc[i]['CLM_ID'],
            "CLM_ID": df_anom.iloc[i]['CLM_ID'],
            "CLM_LINE_NUM": df_anom.iloc[i].get('CLM_LINE_NUM', '1'),
            "expected_BR_DATE_001": "EXPECTED_FAIL",
            "expected_BR_DATE_002": "PASS",
            "expected_BR_AMT_001": "PASS",
            "expected_BR_AMT_002": "PASS",
            "expected_violation_count": 1,
            "scenario": "DATE_CHRONOLOGY"
        })
    idx += 75

    # Admission Discharge
    for i in range(idx, idx + 60):
        df_anom.loc[df_anom.index[i], 'ADMTN_DT'] = '2026-08-20'
        df_anom.loc[df_anom.index[i], 'CLM_ADMSN_DT'] = '2026-08-20'
        df_anom.loc[df_anom.index[i], 'NCH_BENE_DSCHRG_DT'] = '2026-08-15'
        ground_truth.append({
            "evaluation_id": df_anom.iloc[i]['CLM_ID'],
            "CLM_ID": df_anom.iloc[i]['CLM_ID'],
            "CLM_LINE_NUM": df_anom.iloc[i].get('CLM_LINE_NUM', '1'),
            "expected_BR_DATE_001": "PASS",
            "expected_BR_DATE_002": "EXPECTED_FAIL",
            "expected_BR_AMT_001": "PASS",
            "expected_BR_AMT_002": "PASS",
            "expected_violation_count": 1,
            "scenario": "ADMISSION_DISCHARGE"
        })
    idx += 60

    # Negative Amount
    for i in range(idx, idx + 75):
        if i % 2 == 0:
            df_anom.loc[df_anom.index[i], 'CLM_PMT_AMT'] = '-100.00'
        else:
            df_anom.loc[df_anom.index[i], 'CLM_TOT_CHRG_AMT'] = '-500.00'
            df_anom.loc[df_anom.index[i], 'CLM_PMT_AMT'] = '-1000.00'
        ground_truth.append({
            "evaluation_id": df_anom.iloc[i]['CLM_ID'],
            "CLM_ID": df_anom.iloc[i]['CLM_ID'],
            "CLM_LINE_NUM": df_anom.iloc[i].get('CLM_LINE_NUM', '1'),
            "expected_BR_DATE_001": "PASS",
            "expected_BR_DATE_002": "PASS",
            "expected_BR_AMT_001": "EXPECTED_FAIL",
            "expected_BR_AMT_002": "PASS",
            "expected_violation_count": 1,
            "scenario": "NEGATIVE_AMOUNT"
        })
    idx += 75

    # Payment Over Charge
    for i in range(idx, idx + 60):
        df_anom.loc[df_anom.index[i], 'CLM_PMT_AMT'] = '1000.00'
        df_anom.loc[df_anom.index[i], 'CLM_TOT_CHRG_AMT'] = '500.00'
        ground_truth.append({
            "evaluation_id": df_anom.iloc[i]['CLM_ID'],
            "CLM_ID": df_anom.iloc[i]['CLM_ID'],
            "CLM_LINE_NUM": df_anom.iloc[i].get('CLM_LINE_NUM', '1'),
            "expected_BR_DATE_001": "PASS",
            "expected_BR_DATE_002": "PASS",
            "expected_BR_AMT_001": "PASS",
            "expected_BR_AMT_002": "EXPECTED_FAIL",
            "expected_violation_count": 1,
            "scenario": "PAYMENT_OVER_CHARGE"
        })
    idx += 60

    # Multi-rule
    for i in range(idx, idx + 30):
        df_anom.loc[df_anom.index[i], 'CLM_FROM_DT'] = '2026-08-20'
        df_anom.loc[df_anom.index[i], 'CLM_THRU_DT'] = '2026-08-15'
        df_anom.loc[df_anom.index[i], 'CLM_PMT_AMT'] = '-100.00'
        ground_truth.append({
            "evaluation_id": df_anom.iloc[i]['CLM_ID'],
            "CLM_ID": df_anom.iloc[i]['CLM_ID'],
            "CLM_LINE_NUM": df_anom.iloc[i].get('CLM_LINE_NUM', '1'),
            "expected_BR_DATE_001": "EXPECTED_FAIL",
            "expected_BR_DATE_002": "PASS",
            "expected_BR_AMT_001": "EXPECTED_FAIL",
            "expected_BR_AMT_002": "PASS",
            "expected_violation_count": 2,
            "scenario": "MULTI_RULE"
        })

    df_eval = pd.concat([df_clean, df_anom], ignore_index=True)
    df_eval.to_csv(out_dir / "synthetic_phase_b_dataset.csv", sep="|", index=False)
    
    df_gt = pd.DataFrame(ground_truth)
    df_gt.to_csv(out_dir / "ground_truth.csv", index=False)

    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "random_seed": 42,
        "total_records": 1000,
        "clean_records": 700,
        "anomalous_records": 300,
        "distribution": {
            "BR-DATE-001": 75,
            "BR-DATE-002": 60,
            "BR-AMT-001": 75,
            "BR-AMT-002": 60,
            "MULTI_RULE": 30
        }
    }
    with open(out_dir / "generation_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    df_bound = df_master.sample(n=30, random_state=100).copy()
    df_bound = df_bound.reset_index(drop=True)
    df_bound['CLM_ID'] = [f"EVAL_BOUND_{str(i+1).zfill(6)}" for i in range(30)]
    
    gt_bound = []
    
    for i in range(10):
        df_bound.loc[df_bound.index[i], 'CLM_FROM_DT'] = '2026-01-01'
        df_bound.loc[df_bound.index[i], 'CLM_THRU_DT'] = '2026-01-01'
        df_bound.loc[df_bound.index[i], 'ADMTN_DT'] = '2026-01-01'
        df_bound.loc[df_bound.index[i], 'CLM_ADMSN_DT'] = '2026-01-01'
        df_bound.loc[df_bound.index[i], 'NCH_BENE_DSCHRG_DT'] = '2026-01-01'
        df_bound.loc[df_bound.index[i], 'CLM_PMT_AMT'] = '0.00'
        df_bound.loc[df_bound.index[i], 'CLM_TOT_CHRG_AMT'] = '0.00'
        gt_bound.append({
            "evaluation_id": df_bound.iloc[i]['CLM_ID'],
            "CLM_ID": df_bound.iloc[i]['CLM_ID'],
            "CLM_LINE_NUM": df_bound.iloc[i].get('CLM_LINE_NUM', '1'),
            "expected_BR_DATE_001": "PASS",
            "expected_BR_DATE_002": "PASS",
            "expected_BR_AMT_001": "PASS",
            "expected_BR_AMT_002": "PASS",
            "expected_violation_count": 0,
            "scenario": "BOUNDARY"
        })
        
    for i in range(10, 30):
        df_bound.loc[df_bound.index[i], 'CLM_FROM_DT'] = ''
        df_bound.loc[df_bound.index[i], 'CLM_THRU_DT'] = ''
        df_bound.loc[df_bound.index[i], 'ADMTN_DT'] = ''
        df_bound.loc[df_bound.index[i], 'CLM_ADMSN_DT'] = ''
        df_bound.loc[df_bound.index[i], 'NCH_BENE_DSCHRG_DT'] = ''
        df_bound.loc[df_bound.index[i], 'CLM_PMT_AMT'] = ''
        df_bound.loc[df_bound.index[i], 'CLM_TOT_CHRG_AMT'] = ''
        gt_bound.append({
            "evaluation_id": df_bound.iloc[i]['CLM_ID'],
            "CLM_ID": df_bound.iloc[i]['CLM_ID'],
            "CLM_LINE_NUM": df_bound.iloc[i].get('CLM_LINE_NUM', '1'),
            "expected_BR_DATE_001": "NOT_EVALUATED",
            "expected_BR_DATE_002": "NOT_EVALUATED",
            "expected_BR_AMT_001": "NOT_EVALUATED",
            "expected_BR_AMT_002": "NOT_EVALUATED",
            "expected_violation_count": 0,
            "scenario": "MISSING_INPUT"
        })

    df_bound.to_csv(out_dir / "synthetic_boundary_dataset.csv", sep="|", index=False)
    df_gt_bound = pd.DataFrame(gt_bound)
    df_gt_bound.to_csv(out_dir / "ground_truth_boundary.csv", index=False)

if __name__ == "__main__":
    generate_evaluation_data()
