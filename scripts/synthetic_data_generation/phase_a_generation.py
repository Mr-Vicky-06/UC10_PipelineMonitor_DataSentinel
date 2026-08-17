import pandas as pd
import hashlib
import json
import os
from datetime import datetime

CLAIMS_FILE = "master_data/claims/claims_master.csv"
AUTH_FILE = "master_data/authorization/authorization_linked.csv"
HOSPITAL_MAPPING_FILE = "master_data/reference/hospital_mapping.csv"

OUT_DIR = "outputs/reference_data"
TEST_DIR = "tests/fixtures/business_rules"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

def hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("Hashing source files before operations...")
    hash_claims_before = hash_file(CLAIMS_FILE)
    hash_auth_before = hash_file(AUTH_FILE)
    hash_hosp_before = hash_file(HOSPITAL_MAPPING_FILE)

    print("Reading datasets...")
    df_claims = pd.read_csv(CLAIMS_FILE, sep='|', dtype=str)
    df_auths = pd.read_csv(AUTH_FILE, dtype=str)
    df_hosp = pd.read_csv(HOSPITAL_MAPPING_FILE, dtype=str)

    # 1. Beneficiary Reference
    print("Generating Beneficiary Reference...")
    benes = df_claims[['BENE_ID']].dropna().drop_duplicates()
    benes.to_csv(f"{OUT_DIR}/synthetic_beneficiary_reference.csv", index=False)

    # 2. Provider Reference
    print("Generating Provider Reference...")
    # Extract unique PRVDR_NUM and check if ORG_NPI_NUM is consistently populated
    prvdr_cols = ['PRVDR_NUM', 'ORG_NPI_NUM']
    providers = df_claims[prvdr_cols].dropna(subset=['PRVDR_NUM']).drop_duplicates()
    
    # Check if a single PRVDR_NUM has multiple NPIs or missing NPIs
    # In many synthetic datasets, it might just be the same.
    providers = providers.groupby('PRVDR_NUM').first().reset_index()
    providers = providers.merge(df_hosp, on='PRVDR_NUM', how='left')
    providers.to_csv(f"{OUT_DIR}/synthetic_provider_reference.csv", index=False)

    # 3. HCPCS Reference
    print("Generating HCPCS Reference...")
    hcpcs = df_claims[['HCPCS_CD']].dropna().drop_duplicates()
    hcpcs['DESCRIPTION'] = "Synthetic HCPCS Description"
    hcpcs.to_csv(f"{OUT_DIR}/synthetic_hcpcs_reference.csv", index=False)

    # 4. ICD Reference
    print("Generating ICD Reference...")
    icd_cols = [c for c in df_claims.columns if 'ICD_DGNS' in c or 'ICD_PRCDR' in c or 'DGNS_CD' in c]
    icd_series = pd.concat([df_claims[c] for c in icd_cols]).dropna().unique()
    icd_df = pd.DataFrame({'ICD_CODE': icd_series})
    icd_df['DESCRIPTION'] = "Synthetic ICD Description"
    icd_df.to_csv(f"{OUT_DIR}/synthetic_icd_reference.csv", index=False)

    # 5. Authorization Relationship Analysis
    print("Analyzing Authorization Relationship...")
    # Need to match Claims to Auths on BENE_ID + HCPCS_CD
    # We will evaluate: AUTH_EFF_DT <= CLM_FROM_DT <= AUTH_EXP_DT
    # Auth dates format in CSV (e.g. 20190724), Claim dates format (17-Sep-2022)
    
    # Parse dates
    df_auths['AUTH_EFF_DT_parsed'] = pd.to_datetime(df_auths['AUTH_EFF_DT'], format='%Y%m%d', errors='coerce')
    df_auths['AUTH_EXP_DT_parsed'] = pd.to_datetime(df_auths['AUTH_EXP_DT'], format='%Y%m%d', errors='coerce')
    df_claims['CLM_FROM_DT_parsed'] = pd.to_datetime(df_claims['CLM_FROM_DT'], format='%d-%b-%Y', errors='coerce')

    # Providers: Auth has PRF_PHYSN_NPI, Claims has AT_PHYSN_NPI etc.
    # We will just evaluate PRF_PHYSN_NPI vs ORG_NPI_NUM for now as a check
    
    analysis_results = {
        "claims_total": len(df_claims),
        "claims_with_zero_candidates": 0,
        "claims_with_one_candidate": 0,
        "claims_with_multiple_candidates": 0,
        "claims_with_date_valid_auth": 0,
        "claims_with_date_invalid_auth": 0,
        "claims_with_provider_compatible_auth": 0,
        "claims_with_provider_mismatch": 0,
        "claims_with_ambiguous_auth": 0
    }

    # Doing a merge to find candidates
    merged = df_claims[['CLM_ID', 'BENE_ID', 'HCPCS_CD', 'CLM_FROM_DT_parsed', 'ORG_NPI_NUM']].merge(
        df_auths[['AUTH_ID', 'BENE_ID', 'HCPCS_CD', 'AUTH_EFF_DT_parsed', 'AUTH_EXP_DT_parsed', 'PRF_PHYSN_NPI']],
        on=['BENE_ID', 'HCPCS_CD'],
        how='left'
    )
    
    # Group by CLM_ID to analyze
    grouped = merged.groupby('CLM_ID')
    
    for clm_id, group in grouped:
        if group['AUTH_ID'].isna().all():
            analysis_results["claims_with_zero_candidates"] += 1
            continue
        
        cands = group.dropna(subset=['AUTH_ID'])
        num_cands = len(cands)
        
        if num_cands == 1:
            analysis_results["claims_with_one_candidate"] += 1
        else:
            analysis_results["claims_with_multiple_candidates"] += 1
            
        # Date check
        date_valid = cands[(cands['CLM_FROM_DT_parsed'] >= cands['AUTH_EFF_DT_parsed']) & 
                           (cands['CLM_FROM_DT_parsed'] <= cands['AUTH_EXP_DT_parsed'])]
        
        if len(date_valid) > 0:
            analysis_results["claims_with_date_valid_auth"] += 1
        else:
            analysis_results["claims_with_date_invalid_auth"] += 1
            
        # Provider check (Comparing PRF_PHYSN_NPI to ORG_NPI_NUM or others if needed)
        # Assuming ORG_NPI_NUM is our main proxy for provider for now
        prv_valid = cands[cands['ORG_NPI_NUM'] == cands['PRF_PHYSN_NPI']]
        if len(prv_valid) > 0:
            analysis_results["claims_with_provider_compatible_auth"] += 1
        else:
            analysis_results["claims_with_provider_mismatch"] += 1
            
        # Ambiguous auth check: multiple date-valid auths
        if len(date_valid) > 1:
            analysis_results["claims_with_ambiguous_auth"] += 1
            
    with open(f"{OUT_DIR}/authorization_analysis.json", 'w') as f:
        json.dump(analysis_results, f, indent=4)
        
    print("Authorization Analysis Results:")
    print(json.dumps(analysis_results, indent=2))

    # 6. Metadata
    print("Generating Metadata...")
    metadata = {
        "synthetic_beneficiary_reference.csv": {
            "source": CLAIMS_FILE,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "row_count": len(benes),
            "column_count": len(benes.columns),
            "source_fields_used": ["BENE_ID"],
            "is_authoritative": False,
            "generation_method": "Extracted unique BENE_ID",
            "relationship_keys": ["BENE_ID"]
        },
        "synthetic_provider_reference.csv": {
            "source": CLAIMS_FILE,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "row_count": len(providers),
            "column_count": len(providers.columns),
            "source_fields_used": ["PRVDR_NUM", "ORG_NPI_NUM"],
            "is_authoritative": False,
            "generation_method": "Extracted unique PRVDR_NUM and merged with hospital_mapping",
            "relationship_keys": ["PRVDR_NUM", "ORG_NPI_NUM"]
        },
        "synthetic_hcpcs_reference.csv": {
            "source": CLAIMS_FILE,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "row_count": len(hcpcs),
            "column_count": len(hcpcs.columns),
            "source_fields_used": ["HCPCS_CD"],
            "is_authoritative": False,
            "generation_method": "Extracted unique HCPCS_CD",
            "relationship_keys": ["HCPCS_CD"]
        },
        "synthetic_icd_reference.csv": {
            "source": CLAIMS_FILE,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "row_count": len(icd_df),
            "column_count": len(icd_df.columns),
            "source_fields_used": icd_cols,
            "is_authoritative": False,
            "generation_method": "Extracted unique codes from all ICD/DGNS/PRCDR columns",
            "relationship_keys": ["ICD_CODE"]
        }
    }
    
    with open(f"{OUT_DIR}/reference_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=4)

    # 7. Generate Negative Test Fixtures
    print("Generating Negative Test Fixtures...")
    pd.DataFrame({"BENE_ID": ["SYN_BENE_UNKNOWN", "SYN_BENE_INVALID"]}).to_csv(f"{TEST_DIR}/invalid_beneficiaries.csv", index=False)
    pd.DataFrame({"PRVDR_NUM": ["999999", "000000"]}).to_csv(f"{TEST_DIR}/invalid_providers.csv", index=False)
    pd.DataFrame({"HCPCS_CD": ["UNKNOWN", "INVLD"]}).to_csv(f"{TEST_DIR}/invalid_hcpcs_codes.csv", index=False)
    pd.DataFrame({"ICD_CODE": ["UNKNOWN", "INVLD"]}).to_csv(f"{TEST_DIR}/invalid_icd_codes.csv", index=False)

    # 8. Hash verification
    print("Hashing source files after operations...")
    hash_claims_after = hash_file(CLAIMS_FILE)
    hash_auth_after = hash_file(AUTH_FILE)
    hash_hosp_after = hash_file(HOSPITAL_MAPPING_FILE)

    assert hash_claims_before == hash_claims_after, "CLAIMS FILE CHANGED!"
    assert hash_auth_before == hash_auth_after, "AUTH FILE CHANGED!"
    assert hash_hosp_before == hash_hosp_after, "HOSPITAL MAPPING CHANGED!"
    print("Hash verification passed. Files are identical.")

if __name__ == "__main__":
    main()
