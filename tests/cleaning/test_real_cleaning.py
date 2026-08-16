"""
Real Master Data Integration Test for Data Cleaning Module.
Verifies end-to-end cleaning on master files, report generation, ground-truth preservation,
and read-only data safety.
"""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.cleaning import (
    CleaningStatus,
    clean_dataset,
    load_cleaning_config_by_name,
)


class TestRealMasterDataCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.master_data_dir = cls.project_root / "master_data" / "master_data"
        if not cls.master_data_dir.exists():
            cls.master_data_dir = Path(r"D:\UC10_Data_Quality_Pipeline\master_data")

    def _get_sha256(self, filepath: Path) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def test_real_hospital_batches_cleaning(self):
        batches_dir = self.master_data_dir / "batches" / "run_20260816_141418"
        if not batches_dir.exists():
            run_dirs = list((self.master_data_dir / "batches").glob("run_*"))
            if run_dirs:
                batches_dir = run_dirs[0]

        self.assertTrue(batches_dir.exists(), f"Batches dir not found at {batches_dir}")

        with tempfile.TemporaryDirectory() as temp_out_dir:
            temp_path = Path(temp_out_dir)

            hospitals = ["hospital_A", "hospital_B", "hospital_C", "hospital_D", "hospital_E"]
            for hosp in hospitals:
                hosp_dir = batches_dir / hosp
                batch_files = sorted(list(hosp_dir.glob("batch_*.csv")))
                self.assertTrue(len(batch_files) > 0, f"No batch files for {hosp}")

                sample_batch = batch_files[0]
                hash_before = self._get_sha256(sample_batch)

                out_file = temp_path / f"cleaned_{hosp}_{sample_batch.name}"
                rep_file = temp_path / f"report_{hosp}_{sample_batch.stem}.json"

                result = clean_dataset(
                    dataset="claims",
                    input_path_or_df=sample_batch,
                    output_path=out_file,
                    report_path=rep_file,
                    run_schema_validation=True,
                )

                self.assertTrue(result.passed)
                self.assertTrue(out_file.exists())
                self.assertTrue(rep_file.exists())
                self.assertGreater(result.report.metrics.output_rows, 0)

                # Check metrics structure
                rep_dict = result.report.to_dict()
                self.assertIn("whitespace_cells_normalized", rep_dict["metrics"])
                self.assertIn("date_cells_normalized", rep_dict["metrics"])

                # Verify SHA256 unchanged
                hash_after = self._get_sha256(sample_batch)
                self.assertEqual(hash_before, hash_after)

    def test_real_authorization_linked_cleaning(self):
        auth_file = self.master_data_dir / "authorization" / "authorization_linked.csv"
        self.assertTrue(auth_file.exists(), f"Authorization file not found at {auth_file}")

        hash_before = self._get_sha256(auth_file)

        with tempfile.TemporaryDirectory() as temp_out_dir:
            temp_path = Path(temp_out_dir)
            out_file = temp_path / "cleaned_auth.csv"
            rep_file = temp_path / "report_auth.json"

            result = clean_dataset(
                dataset="authorization",
                input_path_or_df=auth_file,
                output_path=out_file,
                report_path=rep_file,
                run_schema_validation=False,  # Evaluate cleaning on full 21k records with ground-truth anomalies
            )

            self.assertTrue(result.passed)
            self.assertEqual(result.report.metrics.input_rows, 21801)
            self.assertEqual(result.report.metrics.output_rows, 21801)
            self.assertTrue(out_file.exists())
            self.assertTrue(rep_file.exists())

            # Verify ground-truth unknown status preserved
            df_cleaned = pd.read_csv(out_file)
            unknown_count = (df_cleaned["AUTH_STATUS_CD"] == "UNKNOWN_STATUS").sum()
            self.assertEqual(unknown_count, 244)

            # Verify date formatted to canonical YYYY-MM-DD
            sample_date = df_cleaned["AUTH_EFF_DT"].iloc[0]
            self.assertRegex(str(sample_date), r"^\d{4}-\d{2}-\d{2}$")

            # Check explicit cell metrics
            self.assertEqual(result.report.metrics.date_cells_normalized, 43602)

        hash_after = self._get_sha256(auth_file)
        self.assertEqual(hash_before, hash_after)


if __name__ == "__main__":
    unittest.main()
