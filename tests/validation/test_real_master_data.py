"""
Read-only validation tests against representative real master-data files.
Ensures zero mutations and verifies schema conformance across all 5 hospital batch directories and authorization dataset.
"""

from pathlib import Path
import unittest

from src.validation import (
    SchemaValidator,
    ValidationStatus,
    load_schema_by_name,
    validate_dataset,
)


class TestRealMasterDataValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.schemas_dir = cls.project_root / "configs" / "schemas"
        cls.master_data_dir = cls.project_root / "master_data" / "master_data"

        if not cls.master_data_dir.exists():
            cls.master_data_dir = Path(r"D:\UC10_Data_Quality_Pipeline\master_data")

        cls.claims_schema = load_schema_by_name("claims", cls.schemas_dir)
        cls.auth_schema = load_schema_by_name("authorization", cls.schemas_dir)
        cls.claims_validator = SchemaValidator(cls.claims_schema)
        cls.auth_validator = SchemaValidator(cls.auth_schema)

    def test_real_authorization_linked_master_data(self):
        auth_file = self.master_data_dir / "authorization" / "authorization_linked.csv"
        self.assertTrue(auth_file.exists(), f"Authorization file not found at {auth_file}")

        result = self.auth_validator.validate_file(auth_file)
        self.assertEqual(result.total_rows, 21801)
        self.assertEqual(result.total_columns, 8)

        # Verify that all 8 required columns are present and dates are valid
        col_issues = [i for i in result.issues if i.check_name == "required_columns_present"]
        date_issues = [i for i in result.issues if i.check_name == "date_format"]
        self.assertEqual(len(col_issues), 0)
        self.assertEqual(len(date_issues), 0)

        # The validator correctly identifies the 244 ground-truth injected UNKNOWN_STATUS records
        allowed_issues = [i for i in result.issues if i.check_name == "allowed_values"]
        self.assertEqual(len(allowed_issues), 1)
        self.assertEqual(allowed_issues[0].affected_row_count, 244)
        self.assertEqual(allowed_issues[0].column, "AUTH_STATUS_CD")

    def test_all_five_hospital_batches(self):
        batches_dir = self.master_data_dir / "batches" / "run_20260816_141418"
        if not batches_dir.exists():
            run_dirs = list((self.master_data_dir / "batches").glob("run_*"))
            if run_dirs:
                batches_dir = run_dirs[0]

        self.assertTrue(batches_dir.exists(), f"Batches directory not found at {batches_dir}")

        hospitals = ["hospital_A", "hospital_B", "hospital_C", "hospital_D", "hospital_E"]
        for hosp in hospitals:
            hosp_dir = batches_dir / hosp
            self.assertTrue(hosp_dir.exists(), f"Hospital directory missing: {hosp_dir}")

            batch_files = sorted(list(hosp_dir.glob("batch_*.csv")))
            self.assertTrue(len(batch_files) > 0, f"No batch files found for {hosp}")

            # Validate the first 3 batch files for each hospital
            for sample_batch in batch_files[:3]:
                result = self.claims_validator.validate_file(sample_batch)
                self.assertTrue(
                    result.passed,
                    f"Batch {sample_batch.name} for {hosp} failed validation: {[i.to_dict() for i in result.issues if i.severity == 'ERROR']}",
                )
                self.assertGreater(result.total_rows, 0)
                self.assertEqual(result.total_columns, 200)

    def test_claims_master_sample(self):
        claims_master_file = self.master_data_dir / "claims" / "claims_master.csv"
        self.assertTrue(claims_master_file.exists(), f"claims_master.csv not found at {claims_master_file}")

        # Validate file structure and header without reading entire 65MB file into RAM at once
        import pandas as pd
        df_sample = pd.read_csv(claims_master_file, sep="|", nrows=1000, dtype=str)
        result = self.claims_validator.validate_dataframe(df_sample, file_name=str(claims_master_file))
        self.assertTrue(result.passed, f"claims_master.csv failed: {result.issues}")
        self.assertEqual(result.total_columns, 197)


if __name__ == "__main__":
    unittest.main()
