import pandas as pd
import json
import os

claims_path = "master_data/claims/claims_master.csv"
auth_path = "master_data/authorization/authorization_linked.csv"

def analyze_claims():
    print("Reading claims...")
    df_claims = pd.read_csv(claims_path, sep='|', dtype=str, usecols=[
        "CLM_ID", "BENE_ID", "PRVDR_NUM", "HCPCS_CD", "ICD_DGNS_CD1"
    ])
    
    distinct_bene = df_claims["BENE_ID"].dropna().unique()
    distinct_prvdr = df_claims["PRVDR_NUM"].dropna().unique()
    distinct_hcpcs = df_claims["HCPCS_CD"].dropna().unique()
    distinct_icd = df_claims["ICD_DGNS_CD1"].dropna().unique()
    
    print(f"Total Claims: {len(df_claims)}")
    print(f"Distinct BENE_ID: {len(distinct_bene)}")
    print(f"Distinct PRVDR_NUM: {len(distinct_prvdr)}")
    print(f"Distinct HCPCS_CD: {len(distinct_hcpcs)}")
    print(f"Distinct ICD_DGNS_CD1: {len(distinct_icd)}")
    
    print("\nSample HCPCS:", distinct_hcpcs[:10].tolist())
    print("Sample ICD_DGNS_CD1:", distinct_icd[:10].tolist())
    
    return df_claims, distinct_bene, distinct_prvdr, distinct_hcpcs, distinct_icd

def analyze_auths(df_claims):
    print("\nReading auths...")
    df_auths = pd.read_csv(auth_path, dtype=str)
    
    print(f"Total Auths: {len(df_auths)}")
    print("Auth columns:", df_auths.columns.tolist())
    
    # Check what join key exists.
    # We have AUTH_ID, BENE_ID, PRF_PHYSN_NPI, HCPCS_CD in auths.
    # Claims has BENE_ID, PRVDR_NUM, HCPCS_CD.
    # Do we have AUTH_ID in claims? No, we used specific columns. Let's check full columns.
    df_claims_full = pd.read_csv(claims_path, sep='|', nrows=1)
    print("\nDo we have AUTH_ID in claims?", "AUTH_ID" in df_claims_full.columns)
    
    # Let's check the overlap of BENE_ID
    auth_benes = df_auths["BENE_ID"].dropna().unique()
    overlap_benes = set(auth_benes).intersection(set(df_claims["BENE_ID"].dropna().unique()))
    print(f"Auth BENE_ID overlap with Claims BENE_ID: {len(overlap_benes)} out of {len(auth_benes)} auth benes")
    
    # Check overlap of HCPCS_CD
    auth_hcpcs = df_auths["HCPCS_CD"].dropna().unique()
    overlap_hcpcs = set(auth_hcpcs).intersection(set(df_claims["HCPCS_CD"].dropna().unique()))
    print(f"Auth HCPCS_CD overlap with Claims HCPCS_CD: {len(overlap_hcpcs)} out of {len(auth_hcpcs)} auth HCPCS")

    # Are there any BENE_ID + HCPCS_CD matches?
    claims_key = df_claims["BENE_ID"] + "_" + df_claims["HCPCS_CD"]
    auths_key = df_auths["BENE_ID"] + "_" + df_auths["HCPCS_CD"]
    overlap_keys = set(auths_key).intersection(set(claims_key))
    print(f"Auth (BENE+HCPCS) overlap with Claims: {len(overlap_keys)} unique combinations")

if __name__ == "__main__":
    df_c, *_ = analyze_claims()
    analyze_auths(df_c)
