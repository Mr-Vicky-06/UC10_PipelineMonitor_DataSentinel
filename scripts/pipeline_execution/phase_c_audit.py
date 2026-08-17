import pandas as pd
from pathlib import Path
import json

def audit():
    results = {}

    # 1. Reference Schemas
    ref_dir = Path('outputs/reference_data')
    for ref_file in ref_dir.glob('synthetic_*.csv'):
        df = pd.read_csv(ref_file, sep='|', nrows=5)
        results[ref_file.name] = list(df.columns)
        
    if (ref_dir / "reference_metadata.json").exists():
        with open(ref_dir / "reference_metadata.json") as f:
            results["reference_metadata.json"] = json.load(f)

    # 2. Claims schema (from Transformation)
    from src.pipeline.transformation import HealthcareTransformer
    transformer = HealthcareTransformer()
    df_claim_master = pd.read_csv('master_data/claims/claims_master.csv', sep='|', dtype=str, nrows=5)
    transformed_batch, _ = transformer.transform_claims(df_claim_master)
    results["transformed_claims"] = list(transformed_batch.columns)

    # 3. Authorization Schema
    df_auth = pd.read_csv('master_data/authorization/authorization_linked.csv', sep='|', nrows=5)
    results["authorization_linked.csv"] = list(df_auth.columns)

    # 4. Hospital Mapping
    df_hosp = pd.read_csv('master_data/reference/hospital_mapping.csv', sep='|', nrows=5)
    results["hospital_mapping.csv"] = list(df_hosp.columns)

    with open('scratch/phase_c_audit_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    audit()
