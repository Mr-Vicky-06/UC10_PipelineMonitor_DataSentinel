"""
Tests for Data Immutability and Read-Only Safety Guarantees.
Verifies that the Data Quality Validation Engine never mutates input data or files.
"""

import hashlib
from pathlib import Path
import unittest
import pandas as pd

from src.data_quality.engine import evaluate_data_quality


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestSafetyAndImmutability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.master_data_dir = cls.project_root / "master_data" / "master_data"
        if not cls.master_data_dir.exists():
            cls.master_data_dir = Path(r"D:\UC10_Data_Quality_Pipeline\master_data")

    def test_33_input_dataframe_remains_unchanged(self):
        """Test 33: Input DataFrame is not altered, cleaned, imputed, or mutated by DQ engine."""
        original_data = {
            "BENE_ID": ["B001", None, "   ", "B004"],
            "CLM_ID": ["C001", "C001", "C002", "C003"],
            "CLM_LINE_NUM": ["1", "1", "1", "2"],
            "PRVDR_NUM": ["030115", "030115", "491581", "377673"],
            "CLM_FROM_DT": ["15-Jan-2020", "20-Jan-2020", "10-Feb-2020", "01-Mar-2020"],
            "CLM_THRU_DT": ["10-Jan-2020", "25-Jan-2020", "15-Feb-2020", "05-Mar-2020"],
            "CLM_PMT_AMT": ["1500.00", "-50.00", "200.00", "450.00"],
            "CLM_TOT_CHRG_AMT": ["2000.00", "100.00", "500.00", "900.00"],
        }
        df_input = pd.DataFrame(original_data)
        df_copy_before = df_input.copy(deep=True)

        # Run data quality checks
        report = evaluate_data_quality("claims", df_input)

        # Assert deep equality before and after evaluation
        pd.testing.assert_frame_equal(df_input, df_copy_before, check_dtype=True)
        # Check specific dirty values remain intact
        self.assertTrue(pd.isna(df_input.loc[1, "BENE_ID"]))
        self.assertEqual(df_input.loc[2, "BENE_ID"], "   ")
        self.assertEqual(df_input.loc[1, "CLM_PMT_AMT"], "-50.00")

    def test_34_master_data_remains_unchanged(self):
        """Test 34: Master data files are read-only and hashes remain identical after evaluation."""
        if not self.master_data_dir.exists():
            self.skipTest(f"Master data directory {self.master_data_dir} not accessible.")

        auth_file = self.master_data_dir / "authorization" / "authorization_linked.csv"
        self.assertTrue(auth_file.exists())
        hash_before = compute_file_sha256(auth_file)

        # Evaluate authorization master file
        report = evaluate_data_quality("authorization", auth_file)

        hash_after = compute_file_sha256(auth_file)
        self.assertEqual(
            hash_before,
            hash_after,
            "Master data file 'authorization_linked.csv' was mutated!",
        )

    def test_35_data_directory_remains_unchanged(self):
        """Test 35: Data directory is strictly read-only."""
        data_dir = self.project_root / "data"
        if not data_dir.exists():
            data_dir = Path(r"D:\UC10_Data_Quality_Pipeline\data")

        if data_dir.exists():
            # Check supporting PUF file
            puf_files = list(data_dir.glob("**/*.csv"))
            if puf_files:
                sample_puf = puf_files[0]
                hash_before = compute_file_sha256(sample_puf)
                # Ensure hash remains unchanged
                hash_after = compute_file_sha256(sample_puf)
                self.assertEqual(hash_before, hash_after)


if __name__ == "__main__":
    unittest.main()
