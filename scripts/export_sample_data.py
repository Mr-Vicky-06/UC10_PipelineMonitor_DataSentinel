"""
Exports standalone CSV sample files for manual inspection and testing.
"""

from pathlib import Path
import sys

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.demo_data_quality_test import create_sample_test_data

def export_samples():
    sample_dir = _project_root / "sample_data"
    sample_dir.mkdir(parents=True, exist_ok=True)

    claims_df, auth_df, hm_df = create_sample_test_data()

    claims_path = sample_dir / "sample_claims_with_anomalies.csv"
    auth_path = sample_dir / "sample_authorization.csv"
    hm_path = sample_dir / "sample_hospital_mapping.csv"

    claims_df.to_csv(claims_path, index=False)
    auth_df.to_csv(auth_path, index=False)
    hm_df.to_csv(hm_path, index=False)

    print(f"Sample test files created successfully in: {sample_dir.resolve()}")
    print(f"  1. {claims_path.name} ({len(claims_df)} rows)")
    print(f"  2. {auth_path.name} ({len(auth_df)} rows)")
    print(f"  3. {hm_path.name} ({len(hm_df)} rows)")

if __name__ == "__main__":
    export_samples()
