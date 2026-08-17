import pandas as pd
import numpy as np
import random
import os
import shutil
import json
from datetime import datetime
from pathlib import Path

# Set seed for determinism
random.seed(42)
np.random.seed(42)

def generate_adversarial():
    # 1. Load reference data
    ref_dir = "outputs/reference_data"
    
    icds = set(pd.read_csv(f"{ref_dir}/synthetic_icd_reference.csv", dtype=str)['ICD_CODE'].dropna())
    hcpcs = set(pd.read_csv(f"{ref_dir}/synthetic_hcpcs_reference.csv", dtype=str)['HCPCS_CD'].dropna())
    benes = set(pd.read_csv(f"{ref_dir}/synthetic_beneficiary_reference.csv", dtype=str)['BENE_ID'].dropna())
    providers = set(pd.read_csv(f"{ref_dir}/synthetic_provider_reference.csv", dtype=str)['PRVDR_NUM'].dropna())
    
    df_auth = pd.read_csv("master_data/authorization/authorization_linked.csv", dtype=str)
    
    auth_dict = {}
    for _, row in df_auth.iterrows():
        key = (row['BENE_ID'], row['HCPCS_CD'])
        if key not in auth_dict:
            auth_dict[key] = []
        auth_dict[key].append(row.to_dict())

    # 2. Independent validation function for Clean Records
    def is_clean(row):
        # 1. ICDs
        icd_cols = [c for c in row.index if c in ['PRNCPAL_DGNS_CD', 'ADMTG_DGNS_CD'] or c.startswith('ICD_DGNS_CD') or c.startswith('ICD_PRCDR_CD') or c.startswith('ICD_DGNS_E_CD')]
        for c in icd_cols:
            val = str(row[c]).strip()
            if val and val != 'nan':
                if val not in icds:
                    return False
                    
        # 2. HCPCS
        val = str(row.get('HCPCS_CD', '')).strip()
        if not val or val == 'nan' or val not in hcpcs:
            return False
            
        # 3. BENE
        val = str(row.get('BENE_ID', '')).strip()
        if not val or val == 'nan' or val not in benes:
            return False
            
        # 4. PRVDR
        val = str(row.get('PRVDR_NUM', '')).strip()
        if not val or val == 'nan' or val not in providers:
            return False
            
        # 5. Chronology
        from_dt = pd.to_datetime(row.get('CLM_FROM_DT', ''), errors='coerce')
        thru_dt = pd.to_datetime(row.get('CLM_THRU_DT', ''), errors='coerce')
        if pd.isna(from_dt) or pd.isna(thru_dt) or from_dt > thru_dt:
            return False
            
        # Admission / Discharge
        admit_col = 'CLM_ADMSN_DT' if 'CLM_ADMSN_DT' in row else 'ADMTN_DT'
        admit_dt = pd.to_datetime(row.get(admit_col, ''), errors='coerce')
        disch_dt = pd.to_datetime(row.get('NCH_BENE_DSCHRG_DT', ''), errors='coerce')
        if pd.notna(admit_dt) and pd.notna(disch_dt) and admit_dt > disch_dt:
            return False
            
        # 6. Amounts
        pmt = pd.to_numeric(row.get('CLM_PMT_AMT', ''), errors='coerce')
        chrg = pd.to_numeric(row.get('CLM_TOT_CHRG_AMT', ''), errors='coerce')
        if pd.isna(pmt) or pd.isna(chrg):
            return False
        if pmt < 0 or chrg < 0:
            return False
        if pmt > chrg:
            return False
            
        # 7. Auth
        candidates = auth_dict.get((str(row.get('BENE_ID', '')).strip(), str(row.get('HCPCS_CD', '')).strip()), [])
        if not candidates:
            return False
            
        valid_by_date = []
        for c in candidates:
            eff = pd.to_datetime(c.get('AUTH_EFF_DT'), format='%Y%m%d', errors='coerce')
            exp = pd.to_datetime(c.get('AUTH_EXP_DT'), format='%Y%m%d', errors='coerce')
            if pd.notna(eff) and pd.notna(exp) and (eff <= from_dt <= exp):
                valid_by_date.append(c)
                
        if not valid_by_date:
            return False
            
        valid_by_status = [c for c in valid_by_date if c.get('AUTH_STATUS_CD') == 'APPROVED']
        if len(valid_by_status) != 1:
            return False
            
        return True

    # 3. Read raw data and find 30 clean records
    print("Reading raw data...")
    # Load enough to find 100 base clean records to mutate
    df_raw = pd.read_csv("data/raw/claims/inpatient.csv", sep='|', dtype=str, nrows=20000)
    
    clean_pool = []
    for _, row in df_raw.iterrows():
        if is_clean(row):
            clean_pool.append(row)
        if len(clean_pool) >= 100:
            break
            
    print(f"Found {len(clean_pool)} candidate clean records.")
    if len(clean_pool) < 100:
        raise ValueError("Not enough clean records found in raw data to construct the dataset.")
        
    clean_records = clean_pool[:30]
    
    # 4. Construct 70 invalid records
    invalid_records = []
    ground_truth = []
    
    def add_gt(record, defect_category, expected_rule, is_clean_flag=False):
        ground_truth.append({
            'CLM_ID': record['CLM_ID'],
            'CLM_LINE_NUM': record.get('CLM_LINE_NUM', '1'),
            'expected_clean': is_clean_flag,
            'expected_violation_count': len(expected_rule.split(',')) if expected_rule else 0,
            'expected_rule_ids': "" if is_clean_flag else expected_rule,
            'defect_type': defect_category
        })
        
    # Clean ground truth
    for r in clean_records:
        add_gt(r, "NONE", "", is_clean_flag=True)
        
    # CATEGORY A: INVALID ICD (10 records) -> BR-REF-001
    for i in range(30, 40):
        r = clean_pool[i].copy()
        r['PRNCPAL_DGNS_CD'] = 'INVALID_ICD_999'
        invalid_records.append(r)
        add_gt(r, "CATEGORY_A_INVALID_ICD", "BR-REF-001")
        
    # CATEGORY B: INVALID HCPCS (10 records) -> BR-REF-002, BR-AUTH-001
    for i in range(40, 50):
        r = clean_pool[i].copy()
        r['HCPCS_CD'] = 'INVALID_HCPCS'
        invalid_records.append(r)
        add_gt(r, "CATEGORY_B_INVALID_HCPCS", "BR-REF-002,BR-AUTH-001")

    # CATEGORY C: INVALID BENE (10 records) -> BR-REF-003, BR-AUTH-001
    for i in range(50, 60):
        r = clean_pool[i].copy()
        r['BENE_ID'] = 'INVALID_BENE_999'
        invalid_records.append(r)
        add_gt(r, "CATEGORY_C_INVALID_BENE", "BR-REF-003,BR-AUTH-001")
        
    # CATEGORY D: INVALID PROVIDER (10 records) -> BR-REF-004
    for i in range(60, 70):
        r = clean_pool[i].copy()
        r['PRVDR_NUM'] = 'INV_PRV'
        invalid_records.append(r)
        add_gt(r, "CATEGORY_D_INVALID_PROVIDER", "BR-REF-004")
        
    # CATEGORY E: CHRONOLOGY ERROR (5 records) -> BR-DATE-001, BR-AUTH-001
    for i in range(70, 75):
        r = clean_pool[i].copy()
        r['CLM_FROM_DT'] = '2026-12-31'
        r['CLM_THRU_DT'] = '2026-01-01'
        invalid_records.append(r)
        add_gt(r, "CATEGORY_E_CHRONOLOGY", "BR-DATE-001,BR-AUTH-001")
        
    # CATEGORY F: INVALID AMOUNT (negative) (5 records) -> BR-AMT-001
    for i in range(75, 80):
        r = clean_pool[i].copy()
        r['CLM_PMT_AMT'] = '-500.00'
        invalid_records.append(r)
        add_gt(r, "CATEGORY_F_NEGATIVE_AMOUNT", "BR-AMT-001")
        
    # CATEGORY G: AUTHORIZATION DEFECT (10 records) -> BR-AUTH-001
    valid_hcpcs_list = list(hcpcs)
    for i in range(80, 85):
        r = clean_pool[i].copy()
        bene = r['BENE_ID']
        for h in valid_hcpcs_list:
            if not auth_dict.get((bene, h), []):
                r['HCPCS_CD'] = h
                break
        invalid_records.append(r)
        add_gt(r, "CATEGORY_G_MISSING_AUTH", "BR-AUTH-001")
        
    for i in range(85, 90):
        r = clean_pool[i].copy()
        r['CLM_FROM_DT'] = '2010-01-01'
        r['CLM_THRU_DT'] = '2010-01-02'
        invalid_records.append(r)
        add_gt(r, "CATEGORY_G_EXPIRED_AUTH", "BR-AUTH-001")
        
    # CATEGORY H: PAYMENT > CHARGE (10 records) -> BR-AMT-002
    for i in range(90, 100):
        r = clean_pool[i].copy()
        r['CLM_PMT_AMT'] = '5000.00'
        r['CLM_TOT_CHRG_AMT'] = '100.00'
        invalid_records.append(r)
        add_gt(r, "CATEGORY_H_PMT_GT_CHRG", "BR-AMT-002")
        
    # 5. Combine and shuffle (optional, but keep it deterministic)
    all_records = clean_records + invalid_records
    df_adv = pd.DataFrame(all_records)
    df_gt = pd.DataFrame(ground_truth)
    
    # 6. Write to output
    out_dir = Path("outputs/pipeline_workspace/adversarial_test/HOSP-ADV")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df_adv.to_csv(out_dir / "batch_20260101.csv", sep='|', index=False)
    df_gt.to_csv(out_dir.parent / "ground_truth.csv", index=False)
    
    print(f"Generated {len(df_adv)} adversarial records.")
    print(f"Saved to {out_dir / 'batch_20260101.csv'}")
    print(f"Saved ground truth to {out_dir.parent / 'ground_truth.csv'}")

if __name__ == "__main__":
    generate_adversarial()
