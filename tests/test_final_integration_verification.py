"""
Comprehensive 12-case integration verification script for Schema Validation -> Data Cleaning boundary.
"""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

import pandas as pd

from src.cleaning import (
    CleaningStatus,
    DataCleaner,
    clean_dataset,
    load_cleaning_config_by_name,
)
from src.validation import ValidationStatus, validate_dataset


def get_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


class TestFinalIntegrationVerification(unittest.TestCase):
    def test_case_01_completely_valid_claims_batch(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B2"],
                "CLM_ID": ["C1", "C2"],
                "CLM_LINE_NUM": ["1", "1"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["2022-09-17", "2022-09-17"],
                "CLM_THRU_DT": ["2022-09-17", "2022-09-17"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["111.01", "222.02"],
            }
        )
        res = clean_dataset("claims", df, run_schema_validation=True)
        self.assertTrue(res.passed)
        self.assertEqual(res.report.status, CleaningStatus.SUCCESS)
        self.assertEqual(len(res.cleaned_df), 2)

    def test_case_02_missing_mandatory_column(self):
        df = pd.DataFrame(
            {
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["2022-09-17"],
                "CLM_THRU_DT": ["2022-09-17"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["111.01"],
            }
        )
        res = clean_dataset("claims", df, run_schema_validation=True)
        self.assertFalse(res.passed)
        self.assertEqual(res.report.status, CleaningStatus.FAILED)
        self.assertEqual(len(res.cleaned_df), 0)

    def test_case_03_mandatory_null_value(self):
        df = pd.DataFrame(
            {
                "BENE_ID": [""],
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["2022-09-17"],
                "CLM_THRU_DT": ["2022-09-17"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["111.01"],
            }
        )
        res = clean_dataset("claims", df, run_schema_validation=True)
        self.assertFalse(res.passed)
        self.assertEqual(res.report.status, CleaningStatus.FAILED)

    def test_case_04_invalid_date_format(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1"],
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["2022-99-99"],
                "CLM_THRU_DT": ["2022-09-17"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["111.01"],
            }
        )
        res = clean_dataset("claims", df, run_schema_validation=True)
        self.assertFalse(res.passed)
        self.assertEqual(res.report.status, CleaningStatus.FAILED)

    def test_case_05_invalid_numeric_value(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1"],
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["2022-09-17"],
                "CLM_THRU_DT": ["2022-09-17"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["INVALID_AMT"],
            }
        )
        res = clean_dataset("claims", df, run_schema_validation=True)
        self.assertFalse(res.passed)
        self.assertEqual(res.report.status, CleaningStatus.FAILED)

    def test_case_06_duplicate_claim_id_and_line_num(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B1"],
                "CLM_ID": ["C1", "C1"],
                "CLM_LINE_NUM": ["1", "1"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["2022-09-17", "2022-09-17"],
                "CLM_THRU_DT": ["2022-09-17", "2022-09-17"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["111.01", "222.02"],
            }
        )
        res = clean_dataset("claims", df, run_schema_validation=True)
        self.assertFalse(res.passed)
        self.assertEqual(res.report.status, CleaningStatus.FAILED)

    def test_case_07_repeated_claim_id_different_line(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B1"],
                "CLM_ID": ["C1", "C1"],
                "CLM_LINE_NUM": ["1", "2"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["2022-09-17", "2022-09-17"],
                "CLM_THRU_DT": ["2022-09-17", "2022-09-17"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["111.01", "222.02"],
            }
        )
        res = clean_dataset("claims", df, run_schema_validation=True)
        self.assertTrue(res.passed)
        self.assertEqual(len(res.cleaned_df), 2)
        self.assertEqual(list(res.cleaned_df["CLM_LINE_NUM"]), ["1", "2"])

    def test_case_08_dirty_but_structurally_valid_data(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["  B1  "],
                "CLM_ID": ["  C1  "],
                "CLM_LINE_NUM": [" 1 "],
                "NCH_CLM_TYPE_CD": [" 60 "],
                "CLM_FROM_DT": [" 17-Sep-2022 "],
                "CLM_THRU_DT": [" 17-Sep-2022 "],
                "PRVDR_NUM": [" 030115 "],
                "CLM_PMT_AMT": [" 1,234.50 "],
            }
        )
        res = clean_dataset("claims", df, run_schema_validation=True)
        self.assertTrue(res.passed)
        row = res.cleaned_df.iloc[0]
        self.assertEqual(row["CLM_FROM_DT"], "2022-09-17")
        self.assertEqual(row["CLM_PMT_AMT"], "1234.50")
        self.assertEqual(row["PRVDR_NUM"], "030115")

    def test_case_09_intentional_anomaly_unknown_status(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["AUTH_001"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": [" unknown_status "],
            }
        )
        config = load_cleaning_config_by_name("authorization")
        cleaner = DataCleaner(config)
        res = cleaner.clean(df)
        self.assertEqual(res.cleaned_df["AUTH_STATUS_CD"].iloc[0], "UNKNOWN_STATUS")

    def test_case_10_rows_changed_vs_cell_metrics(self):
        df = pd.DataFrame(
            {
                "BENE_ID": [" B1 ", "B2"],
                "CLM_ID": [" C1 ", "C2"],
                "CLM_LINE_NUM": ["1", "1"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": [" 17-Sep-2022 ", "2022-09-17"],
                "CLM_THRU_DT": ["2022-09-17", "2022-09-17"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": [" 1,234.50 ", "200.00"],
            }
        )
        config = load_cleaning_config_by_name("claims")
        cleaner = DataCleaner(config)
        res = cleaner.clean(df)
        m = res.report.metrics
        self.assertEqual(m.rows_changed, 1)
        self.assertGreaterEqual(m.whitespace_cells_normalized, 4)
        self.assertEqual(m.date_cells_normalized, 1)
        self.assertEqual(m.numeric_cells_normalized, 1)

    def test_case_11_source_master_data_hash_preservation(self):
        base = Path(__file__).resolve().parent.parent / "master_data" / "master_data"
        if not base.exists():
            base = Path(r"D:\UC10_Data_Quality_Pipeline\master_data")

        test_files = [
            base / "authorization/authorization_linked.csv",
            base / "batches/run_20260816_141418/hospital_A/batch_20150316.csv",
            base / "claims/claims_master.csv",
        ]
        h_before = {str(f): get_sha256(f) for f in test_files if f.exists()}
        for f in test_files:
            if f.exists():
                ds = "authorization" if "authorization" in str(f) else "claims"
                clean_dataset(ds, f, run_schema_validation=False)
        h_after = {str(f): get_sha256(f) for f in test_files if f.exists()}
        for k in h_before:
            self.assertEqual(h_before[k], h_after[k], f"Hash changed for {k}")

    def test_case_12_no_output_in_data_or_master_data(self):
        # Verify that cleaning outputs are written strictly to pipeline_output or specified paths
        base = Path(__file__).resolve().parent.parent
        data_dir = base / "data"
        master_data_dir = base / "master_data"

        # Record file count and mtimes before
        files_before = set(data_dir.rglob("*")) if data_dir.exists() else set()
        files_before.update(master_data_dir.rglob("*") if master_data_dir.exists() else set())

        # Execute cleaning with default output_base_dir
        batch_sample = master_data_dir / "master_data" / "batches" / "run_20260816_141418" / "hospital_A" / "batch_20150316.csv"
        if batch_sample.exists():
            clean_dataset("claims", batch_sample, run_schema_validation=True)

        # Record file count after
        files_after = set(data_dir.rglob("*")) if data_dir.exists() else set()
        files_after.update(master_data_dir.rglob("*") if master_data_dir.exists() else set())

        new_files = files_after - files_before
        self.assertEqual(len(new_files), 0, f"New files were written to data/ or master_data/: {new_files}")


if __name__ == "__main__":
    unittest.main()
