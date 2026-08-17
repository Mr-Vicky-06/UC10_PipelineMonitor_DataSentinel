import pandas as pd
import numpy as np
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

def get_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def setup_directories():
    out_dir = Path("outputs/business_rules/evaluation/phase_c")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def generate_evaluation_data():
    np.random.seed(42)
    out_dir = setup_directories()
    
    # Store pre-execution hashes
    claims_master_path = "master_data/claims/claims_master.csv"
    auth_master_path = "master_data/authorization/authorization_linked.csv"
    pre_hashes = {
        "claims_master": get_file_hash(claims_master_path),
        "auth_master": get_file_hash(auth_master_path)
    }

    # Load master claims to act as a template
    df_master = pd.read_csv(claims_master_path, sep="|", dtype=str)
    
    # Load all reference datasets
    ref_dir = Path("outputs/reference_data")
    icds = set(pd.read_csv(ref_dir / "synthetic_icd_reference.csv", dtype=str)['ICD_CODE'].dropna())
    hcpcs = set(pd.read_csv(ref_dir / "synthetic_hcpcs_reference.csv", dtype=str)['HCPCS_CD'].dropna())
    benes = set(pd.read_csv(ref_dir / "synthetic_beneficiary_reference.csv", dtype=str)['BENE_ID'].dropna())
    providers = set(pd.read_csv(ref_dir / "synthetic_provider_reference.csv", dtype=str)['PRVDR_NUM'].dropna())
    
    df_auth = pd.read_csv(auth_master_path, dtype=str)
    
    # Process dates
    df_auth['AUTH_EFF_DT_pd'] = pd.to_datetime(df_auth['AUTH_EFF_DT'], format="%Y%m%d")
    df_auth['AUTH_EXP_DT_pd'] = pd.to_datetime(df_auth['AUTH_EXP_DT'], format="%Y%m%d")
    
    # Filter unambiguous, valid auths for the clean set
    auth_counts = df_auth.groupby(['BENE_ID', 'HCPCS_CD']).size().reset_index(name='count')
    single_auth_keys = auth_counts[auth_counts['count'] == 1]
    
    df_auth_clean = pd.merge(df_auth, single_auth_keys, on=['BENE_ID', 'HCPCS_CD'])
    df_auth_clean = df_auth_clean[df_auth_clean['AUTH_STATUS_CD'] == 'APPROVED']
    
    # Pre-compute existing auth keys for SCENARIO 5
    existing_auth_keys = set(zip(df_auth['BENE_ID'], df_auth['HCPCS_CD']))
    
    df_sample = pd.DataFrame(index=range(1000), columns=df_master.columns)
    
    # Give them deterministic IDs
    df_sample['CLM_ID'] = [f"EVAL_CLM_C2_{str(i+1).zfill(6)}" for i in range(1000)]
    df_sample['CLM_LINE_NUM'] = "1"
    
    ground_truth = []
    
    # ---------------------------------------------------------
    # 1. Clean Records (0 to 699)
    # ---------------------------------------------------------
    clean_auth_samples = df_auth_clean.sample(n=700, random_state=42).to_dict('records')
    for i in range(700):
        auth_rec = clean_auth_samples[i]
        df_sample.loc[i, 'BENE_ID'] = auth_rec['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = auth_rec['HCPCS_CD']
        df_sample.loc[i, 'PRNCPAL_DGNS_CD'] = list(icds)[i % len(icds)]
        df_sample.loc[i, 'PRVDR_NUM'] = list(providers)[i % len(providers)]
        
        eff = auth_rec['AUTH_EFF_DT_pd']
        df_sample.loc[i, 'CLM_FROM_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = (eff + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df_sample.loc[i, 'ADMTN_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_ADMSN_DT'] = eff.strftime("%Y-%m-%d")
        df_sample.loc[i, 'NCH_BENE_DSCHRG_DT'] = (eff + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
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
    # ---------------------------------------------------------
    idx = 700
    
    def reset_to_clean(i):
        auth_rec = clean_auth_samples[i % 700]
        df_sample.loc[i, 'BENE_ID'] = auth_rec['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = auth_rec['HCPCS_CD']
        df_sample.loc[i, 'PRNCPAL_DGNS_CD'] = list(icds)[i % len(icds)]
        df_sample.loc[i, 'PRVDR_NUM'] = list(providers)[i % len(providers)]
        eff = auth_rec['AUTH_EFF_DT_pd']
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
        inv_icd = f"INV_ICD_{i}"
        assert inv_icd not in icds
        df_sample.loc[i, 'PRNCPAL_DGNS_CD'] = inv_icd
        add_gt(i, "INVALID_ICD", r1="FAIL")
    idx += 30
    
    # 2. Invalid HCPCS (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        inv_hcpcs = f"INV_HCP_{i}"
        assert inv_hcpcs not in hcpcs
        df_sample.loc[i, 'HCPCS_CD'] = inv_hcpcs
        add_gt(i, "INVALID_HCPCS", r2="FAIL", a1="NO_AUTHORIZATION")
    idx += 30
    
    # 3. Invalid Beneficiary (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        inv_bene = f"INV_BEN_{i}"
        assert inv_bene not in benes
        df_sample.loc[i, 'BENE_ID'] = inv_bene
        add_gt(i, "INVALID_BENE", r3="FAIL", a1="NO_AUTHORIZATION")
    idx += 30
    
    # 4. Invalid Provider (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        inv_prv = f"INV_PRV_{i}"
        assert inv_prv not in providers
        df_sample.loc[i, 'PRVDR_NUM'] = inv_prv
        add_gt(i, "INVALID_PROVIDER", r4="FAIL")
    idx += 30
    
    # 5. Missing Authorization Candidate (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        bene = df_sample.loc[i, 'BENE_ID']
        hcpcs_cand = list(hcpcs)[(i+100) % len(hcpcs)]
        while (bene, hcpcs_cand) in existing_auth_keys:
            hcpcs_cand = list(hcpcs)[np.random.randint(len(hcpcs))]
        assert (bene, hcpcs_cand) not in existing_auth_keys
        
        df_sample.loc[i, 'HCPCS_CD'] = hcpcs_cand
        add_gt(i, "MISSING_AUTH", a1="NO_AUTHORIZATION")
    idx += 30
    
    # Helper to check if any OTHER auth is valid on a date
    def has_other_valid_auth(bene, hcpcs, dt, exclude_auth_id=None):
        subset = df_auth[(df_auth['BENE_ID'] == bene) & (df_auth['HCPCS_CD'] == hcpcs)]
        for _, row in subset.iterrows():
            if row['AUTH_ID'] == exclude_auth_id: continue
            if row['AUTH_STATUS_CD'] != 'APPROVED': continue
            e = row['AUTH_EFF_DT_pd']
            x = row['AUTH_EXP_DT_pd']
            if pd.notna(e) and pd.notna(x) and e <= dt <= x:
                return True
        return False
        
    # 6. Expired Authorization (30) -> CLM_FROM_DT > AUTH_EXP_DT
    # Note: BR-AUTH-001 currently assigns EXPIRED_AUTHORIZATION for both expired and not-yet-effective.
    for i in range(idx, idx+30):
        auth_rec = clean_auth_samples[i % len(clean_auth_samples)]
        reset_to_clean(i)
        df_sample.loc[i, 'BENE_ID'] = auth_rec['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = auth_rec['HCPCS_CD']
        exp = auth_rec['AUTH_EXP_DT_pd']
        dt = exp + pd.Timedelta(days=10)
        
        assert not has_other_valid_auth(auth_rec['BENE_ID'], auth_rec['HCPCS_CD'], dt)
        
        df_sample.loc[i, 'CLM_FROM_DT'] = dt.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = df_sample.loc[i, 'CLM_FROM_DT']
        # Use Boundary condition for one of them
        if i == idx:
            df_sample.loc[i, 'CLM_FROM_DT'] = exp.strftime("%Y-%m-%d")
            df_sample.loc[i, 'CLM_THRU_DT'] = exp.strftime("%Y-%m-%d")
            # If CLM_FROM_DT == AUTH_EXP_DT, it is INCLUSIVE, so it is AUTHORIZED
            add_gt(i, "BOUNDARY_EXACT_EXP", a1="AUTHORIZED")
        elif i == idx + 1:
            dt_after = exp + pd.Timedelta(days=1)
            df_sample.loc[i, 'CLM_FROM_DT'] = dt_after.strftime("%Y-%m-%d")
            df_sample.loc[i, 'CLM_THRU_DT'] = dt_after.strftime("%Y-%m-%d")
            assert not has_other_valid_auth(auth_rec['BENE_ID'], auth_rec['HCPCS_CD'], dt_after)
            add_gt(i, "BOUNDARY_AFTER_EXP", a1="EXPIRED_AUTHORIZATION")
        else:
            add_gt(i, "EXPIRED_AUTH", a1="EXPIRED_AUTHORIZATION")
    idx += 30
    
    # 7. Not Yet Effective (30) -> CLM_FROM_DT < AUTH_EFF_DT
    for i in range(idx, idx+30):
        auth_rec = clean_auth_samples[(i+50) % len(clean_auth_samples)]
        reset_to_clean(i)
        df_sample.loc[i, 'BENE_ID'] = auth_rec['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = auth_rec['HCPCS_CD']
        eff = auth_rec['AUTH_EFF_DT_pd']
        dt = eff - pd.Timedelta(days=10)
        
        assert not has_other_valid_auth(auth_rec['BENE_ID'], auth_rec['HCPCS_CD'], dt)
        
        df_sample.loc[i, 'CLM_FROM_DT'] = dt.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = df_sample.loc[i, 'CLM_FROM_DT']
        
        if i == idx:
            df_sample.loc[i, 'CLM_FROM_DT'] = eff.strftime("%Y-%m-%d")
            df_sample.loc[i, 'CLM_THRU_DT'] = eff.strftime("%Y-%m-%d")
            add_gt(i, "BOUNDARY_EXACT_EFF", a1="AUTHORIZED")
        elif i == idx + 1:
            dt_before = eff - pd.Timedelta(days=1)
            df_sample.loc[i, 'CLM_FROM_DT'] = dt_before.strftime("%Y-%m-%d")
            df_sample.loc[i, 'CLM_THRU_DT'] = dt_before.strftime("%Y-%m-%d")
            assert not has_other_valid_auth(auth_rec['BENE_ID'], auth_rec['HCPCS_CD'], dt_before)
            add_gt(i, "BOUNDARY_BEFORE_EFF", a1="EXPIRED_AUTHORIZATION") # Production rule maps this to EXPIRED_AUTHORIZATION
        else:
            add_gt(i, "NOT_YET_EFFECTIVE", a1="EXPIRED_AUTHORIZATION")
    idx += 30
    
    # 8. Invalid Auth Status (DENIED) (30)
    denied_auths = df_auth[df_auth['AUTH_STATUS_CD'] == 'DENIED'].to_dict('records')
    valid_denied_found = 0
    denied_idx = 0
    while valid_denied_found < 30 and denied_idx < len(denied_auths):
        auth_rec = denied_auths[denied_idx]
        denied_idx += 1
        
        dt = auth_rec['AUTH_EFF_DT_pd'] + pd.Timedelta(days=1)
        # Verify no APPROVED auth active at this time
        if not has_other_valid_auth(auth_rec['BENE_ID'], auth_rec['HCPCS_CD'], dt):
            i = idx + valid_denied_found
            reset_to_clean(i)
            df_sample.loc[i, 'BENE_ID'] = auth_rec['BENE_ID']
            df_sample.loc[i, 'HCPCS_CD'] = auth_rec['HCPCS_CD']
            df_sample.loc[i, 'CLM_FROM_DT'] = dt.strftime("%Y-%m-%d")
            df_sample.loc[i, 'CLM_THRU_DT'] = dt.strftime("%Y-%m-%d")
            add_gt(i, "INVALID_AUTH_STATUS", a1="INVALID_STATUS")
            valid_denied_found += 1
            
    assert valid_denied_found == 30, "Not enough pure denied scenarios found"
    idx += 30
    
    # 9. Ambiguous Auth (30)
    # Find bene+hcpcs combos with multiple approved auths that actually overlap
    ambig_groups = df_auth[df_auth['AUTH_STATUS_CD'] == 'APPROVED'].groupby(['BENE_ID', 'HCPCS_CD'])
    ambig_pairs = []
    
    for (bene, hcpcs), group in ambig_groups:
        if len(group) < 2: continue
        
        # Check all pairs in this group for an overlap
        recs = group.to_dict('records')
        for a in range(len(recs)):
            for b in range(a+1, len(recs)):
                r1 = recs[a]
                r2 = recs[b]
                eff1 = r1['AUTH_EFF_DT_pd']
                exp1 = r1['AUTH_EXP_DT_pd']
                eff2 = r2['AUTH_EFF_DT_pd']
                exp2 = r2['AUTH_EXP_DT_pd']
                
                overlap_start = max(eff1, eff2)
                overlap_end = min(exp1, exp2)
                
                if overlap_start <= overlap_end:
                    ambig_pairs.append({
                        'BENE_ID': bene, 'HCPCS_CD': hcpcs,
                        'overlap_start': overlap_start, 'overlap_end': overlap_end
                    })
                    break # Found one overlap for this group
            if len(ambig_pairs) >= 30: break
        if len(ambig_pairs) >= 30: break
        
    assert len(ambig_pairs) == 30, f"Found only {len(ambig_pairs)} truly overlapping ambiguous auths"
    
    for count, pair in enumerate(ambig_pairs):
        i = idx + count
        reset_to_clean(i)
        df_sample.loc[i, 'BENE_ID'] = pair['BENE_ID']
        df_sample.loc[i, 'HCPCS_CD'] = pair['HCPCS_CD']
        dt = pair['overlap_start'] # guaranteed to be inside both
        
        # Mathematically verify both are valid on dt
        subset = df_auth[(df_auth['BENE_ID'] == pair['BENE_ID']) & (df_auth['HCPCS_CD'] == pair['HCPCS_CD']) & (df_auth['AUTH_STATUS_CD'] == 'APPROVED')]
        active_count = 0
        for _, row in subset.iterrows():
            if row['AUTH_EFF_DT_pd'] <= dt <= row['AUTH_EXP_DT_pd']:
                active_count += 1
        assert active_count >= 2, f"Failed ambiguity math check for {pair['BENE_ID']} {pair['HCPCS_CD']}"
        
        df_sample.loc[i, 'CLM_FROM_DT'] = dt.strftime("%Y-%m-%d")
        df_sample.loc[i, 'CLM_THRU_DT'] = dt.strftime("%Y-%m-%d")
        add_gt(i, "AMBIGUOUS_AUTH", a1="AMBIGUOUS_AUTH")
    idx += 30
    
    # 10. Missing All Inputs (30)
    for i in range(idx, idx+30):
        reset_to_clean(i)
        df_sample.loc[i, 'PRNCPAL_DGNS_CD'] = ""
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
    
    with open(out_dir / "pre_hashes.json", "w") as f:
        json.dump(pre_hashes, f)
        
    print("Generation complete")

if __name__ == "__main__":
    generate_evaluation_data()
