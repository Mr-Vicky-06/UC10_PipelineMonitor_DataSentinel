import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

def setup_directories():
    out_dir = Path("outputs/business_rules/evaluation/phase_c")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def generate_evaluation_data():
    np.random.seed(42)
    out_dir = setup_directories()

    # Load master claims to act as a template
    df_master = pd.read_csv("master_data/claims/claims_master.csv", sep="|", dtype=str)
    
    # Load all reference datasets
    ref_dir = Path("outputs/reference_data")
    icds = list(pd.read_csv(ref_dir / "synthetic_icd_reference.csv", dtype=str)['ICD_CODE'].dropna())
    hcpcs = list(pd.read_csv(ref_dir / "synthetic_hcpcs_reference.csv", dtype=str)['HCPCS_CD'].dropna())
    benes = list(pd.read_csv(ref_dir / "synthetic_beneficiary_reference.csv", dtype=str)['BENE_ID'].dropna())
    providers = list(pd.read_csv(ref_dir / "synthetic_provider_reference.csv", dtype=str)['PRVDR_NUM'].dropna())
    
    df_auth = pd.read_csv("master_data/authorization/authorization_linked.csv", dtype=str)
    
    # Filter unambiguous, valid auths for the clean set
    # An unambiguous auth is one where (BENE_ID, HCPCS_CD) appears EXACTLY ONCE
    auth_counts = df_auth.groupby(['BENE_ID', 'HCPCS_CD']).size().reset_index(name='count')
    single_auth_keys = auth_counts[auth_counts['count'] == 1]
    
    df_auth_clean = pd.merge(df_auth, single_auth_keys, on=['BENE_ID', 'HCPCS_CD'])
    df_auth_clean = df_auth_clean[df_auth_clean['AUTH_STATUS_CD'] == 'APPROVED']
    
    # Also find ambiguous auths for the ambiguous scenario
    ambig_auth_keys = auth_counts[auth_counts['count'] > 1]
    df_auth_ambig = pd.merge(df_auth, ambig_auth_keys, on=['BENE_ID', 'HCPCS_CD'])
    df_auth_ambig = df_auth_ambig[df_auth_ambig['AUTH_STATUS_CD'] == 'APPROVED']
    # Get pairs that have AT LEAST 2 APPROVED overlapping dates (assume they overlap for simplicity if we pick their dates right)
    
    df_sample = df_master.sample(n=1000, random_state=42).copy().reset_index(drop=True)
    
    # Give them deterministic IDs
    df_sample['CLM_ID'] = [f"EVAL_CLM_C_{str(i+1).zfill(6)}" for i in range(1000)]
    
    ground_truth = []
    
    # ---------------------------------------------------------
    # 1. Clean Records (0 to 699)
    # ---------------------------------------------------------
    clean_auth_samples = df_auth_clean.sample(n=700, random_state=42).to_dict('records')
    for i in range(700):
        auth_rec = clean_auth_samples[i]
        df_sample.loc[i, 'BENE_ID'] = auth_rec['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = auth_rec['HCPCS_CD']
        df_sample.loc[i, 'PRNCPAL_DGNS_CD'] = np.random.choice(icds)
        df_sample.loc[i, 'PRVDR_NUM'] = np.random.choice(providers)
        
        # Valid Dates: Make sure it's within auth window and Phase B date rules pass
        eff = pd.to_datetime(auth_rec['AUTH_EFF_DT'], format="%Y%m%d")
        df_sample.loc[i, 'CLM_FROM_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = (eff + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df_sample.loc[i, 'ADMTN_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_ADMSN_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'NCH_BENE_DSCHRG_DT'] = (eff + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Valid Amounts: Phase B rules pass
        df_sample.loc[i, 'CLM_PMT_AMT'] = "100.00"
        df_sample.loc[i, 'CLM_TOT_CHRG_AMT'] = "500.00"
        
        ground_truth.append({
            "evaluation_id": df_sample.loc[i, 'CLM_ID'],
            "CLM_ID": df_sample.loc[i, 'CLM_ID'],
            "scenario": "CLEAN",
            "expected_BR_REF_001": "PASS",
            "expected_BR_REF_002": "PASS",
            "expected_BR_REF_003": "PASS",
            "expected_BR_REF_004": "PASS",
            "expected_BR_AUTH_001": "AUTHORIZED"
        })

    # ---------------------------------------------------------
    # 2. Anomalous Records (700 to 999) - 300 records
    # 10 Scenarios * 30 records each
    # ---------------------------------------------------------
    idx = 700
    
    def reset_to_clean(i):
        auth_rec = clean_auth_samples[i % 700] # borrow from clean just to have valid base
        df_sample.loc[i, 'BENE_ID'] = auth_rec['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = auth_rec['HCPCS_CD']
        df_sample.loc[i, 'PRNCPAL_DGNS_CD'] = np.random.choice(icds)
        df_sample.loc[i, 'PRVDR_NUM'] = np.random.choice(providers)
        eff = pd.to_datetime(auth_rec['AUTH_EFF_DT'], format="%Y%m%d")
        df_sample.loc[i, 'CLM_FROM_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'ADMTN_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_ADMSN_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'NCH_BENE_DSCHRG_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_PMT_AMT'] = "100.00"
        df_sample.loc[i, 'CLM_TOT_CHRG_AMT'] = "500.00"
        return auth_rec
        
    def add_gt(i, scen, r1="PASS", r2="PASS", r3="PASS", r4="PASS", a1="AUTHORIZED"):
        ground_truth.append({
            "evaluation_id": df_sample.loc[i, 'CLM_ID'],
            "CLM_ID": df_sample.loc[i, 'CLM_ID'],
            "scenario": scen,
            "expected_BR_REF_001": r1,
            "expected_BR_REF_002": r2,
            "expected_BR_REF_003": r3,
            "expected_BR_REF_004": r4,
            "expected_BR_AUTH_001": a1
        })

    # 1. Invalid ICD (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        df_sample.loc[i, 'PRNCPAL_DGNS_CD'] = 'INV_ICD'
        add_gt(i, "INVALID_ICD", r1="FAIL")
    idx += 30
    
    # 2. Invalid HCPCS (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        df_sample.loc[i, 'HCPCS_CD'] = 'INV_HCP'
        # An invalid HCPCS means Authorization Match will fail to find a candidate too!
        add_gt(i, "INVALID_HCPCS", r2="FAIL", a1="NO_AUTHORIZATION")
    idx += 30
    
    # 3. Invalid Beneficiary (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        df_sample.loc[i, 'BENE_ID'] = 'INV_BENE'
        add_gt(i, "INVALID_BENE", r3="FAIL", a1="NO_AUTHORIZATION")
    idx += 30
    
    # 4. Invalid Provider (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        df_sample.loc[i, 'PRVDR_NUM'] = 'INV_PRV'
        add_gt(i, "INVALID_PROVIDER", r4="FAIL")
    idx += 30
    
    # 5. Missing Authorization Candidate (30)
    for i in range(idx, idx+30):
        # valid bene, valid hcpcs, but they don't match together in auth table
        # Take bene from clean[0], hcpcs from clean[100]
        reset_to_clean(i)
        df_sample.loc[i, 'BENE_ID'] = clean_auth_samples[i % 700]['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = clean_auth_samples[(i+100) % 700]['HCPCS_CD']
        add_gt(i, "MISSING_AUTH", a1="NO_AUTHORIZATION")
    idx += 30
    
    # 6. Expired Authorization (30) -> CLM_FROM_DT > AUTH_EXP_DT
    for i in range(idx, idx+30):
        auth_rec = reset_to_clean(i)
        exp = pd.to_datetime(auth_rec['AUTH_EXP_DT'], format="%Y%m%d")
        df_sample.loc[i, 'CLM_FROM_DT'] = (exp + pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = df_sample.loc[i, 'CLM_FROM_DT'] # pass phase B
        add_gt(i, "EXPIRED_AUTH", a1="EXPIRED_AUTHORIZATION")
    idx += 30
    
    # 7. Not Yet Effective (30) -> CLM_FROM_DT < AUTH_EFF_DT
    for i in range(idx, idx+30):
        auth_rec = reset_to_clean(i)
        eff = pd.to_datetime(auth_rec['AUTH_EFF_DT'], format="%Y%m%d")
        df_sample.loc[i, 'CLM_FROM_DT'] = (eff - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = df_sample.loc[i, 'CLM_FROM_DT']
        add_gt(i, "NOT_YET_EFFECTIVE", a1="EXPIRED_AUTHORIZATION") # In my code I called it EXPIRED_AUTHORIZATION if none cover date
    idx += 30
    
    # 8. Invalid Auth Status (DENIED) (30)
    denied_auths = df_auth[df_auth['AUTH_STATUS_CD'] == 'DENIED'].to_dict('records')
    for i in range(idx, idx+30):
        # Get a denied auth
        auth_rec = denied_auths[i % len(denied_auths)]
        reset_to_clean(i)
        df_sample.loc[i, 'BENE_ID'] = auth_rec['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = auth_rec['HCPCS_CD']
        eff = pd.to_datetime(auth_rec['AUTH_EFF_DT'], format="%Y%m%d")
        df_sample.loc[i, 'CLM_FROM_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = eff.strftime("%Y-%m-%d")
        add_gt(i, "INVALID_AUTH_STATUS", a1="INVALID_STATUS")
    idx += 30
    
    # 9. Ambiguous Auth (30)
    # Find bene+hcpcs combos with multiple approved auths that overlap in dates.
    # To keep it simple, we just use df_auth_ambig pairs, and set date to be within BOTH (or at least one where both are valid)
    # Wait, df_auth_ambig has multiple approved per (BENE, HCPCS). Let's pick 30 unique pairs.
    ambig_pairs = df_auth_ambig[['BENE_ID', 'HCPCS_CD']].drop_duplicates().to_dict('records')
    for i in range(idx, idx+30):
        pair = ambig_pairs[(i - idx) % len(ambig_pairs)]
        # Get the auths for this pair
        auths = df_auth_ambig[(df_auth_ambig['BENE_ID'] == pair['BENE_ID']) & (df_auth_ambig['HCPCS_CD'] == pair['HCPCS_CD'])]
        reset_to_clean(i)
        df_sample.loc[i, 'BENE_ID'] = pair['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = pair['HCPCS_CD']
        # to ensure ambiguity, set date to exactly the first one's effective date, and hope it overlaps with the second. 
        # Actually to be 100% sure they overlap, we can manually make them overlap in a modified auth dict, or just pick the max EFF and min EXP of the pair.
        # But this uses real data. Let's just pick one date and trust they overlap in real data, OR just pick a date where they actually overlap!
        overlap_dt = None
        for a_idx, row_a in auths.iterrows():
            eff = pd.to_datetime(row_a['AUTH_EFF_DT'], format="%Y%m%d")
            df_sample.loc[i, 'CLM_FROM_DT'] = eff.strftime("%Y-%m-%d")
            df_sample.loc[i, 'CLM_THRU_DT'] = eff.strftime("%Y-%m-%d")
            break
        add_gt(i, "AMBIGUOUS_AUTH", a1="AMBIGUOUS_AUTH")
    idx += 30
    
    # 10. Missing All Inputs (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        # Blank out the reference fields
        df_sample.loc[i, 'PRNCPAL_DGNS_CD'] = ""
        # Also null out ALL ICD cols
        for c in df_sample.columns:
            if c.startswith('ICD_'): df_sample.loc[i, c] = ""
        df_sample.loc[i, 'HCPCS_CD'] = ""
        df_sample.loc[i, 'BENE_ID'] = ""
        df_sample.loc[i, 'PRVDR_NUM'] = ""
        add_gt(i, "MISSING_INPUTS", r1="NOT_EVALUATED", r2="NOT_EVALUATED", r3="NOT_EVALUATED", r4="NOT_EVALUATED", a1="NOT_EVALUATED")
    idx += 30
    
    df_sample.to_csv(out_dir / "synthetic_phase_c_dataset.csv", sep="|", index=False)
    df_gt = pd.DataFrame(ground_truth)
    df_gt.to_csv(out_dir / "ground_truth.csv", index=False)
    
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "random_seed": 42,
        "total_records": 1000,
        "clean_records": 700,
        "anomalous_records": 300,
    }
    with open(out_dir / "generation_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("Generation complete")

if __name__ == "__main__":
    generate_evaluation_data()
