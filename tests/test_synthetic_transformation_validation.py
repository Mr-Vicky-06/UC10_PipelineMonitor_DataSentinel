"""
Synthetic Data Validation & Healthcare Edge-Case Test Suite
===========================================================
Validates the production HealthcareTransformer against real-world healthcare
data edge cases and advanced scaling tasks:

1. Missing / NULL values
2. Invalid & impossible dates
3. Invalid currency strings
4. Duplicate records & claim-line grain
5. Unexpected / extra columns
6. Missing required columns (raises TransformationError)
7. Very large file scalability (50,000 synthetic records)
8. CMS Part D suppression values ('*', '#') & _suppression_indicator metadata
9. NPI formats, float integers, and scientific notation
10. Unexpected input data types
11. Malformed records & non-crashing isolation
12. Multi-batch lineage traceability & unique lineage IDs
13. Structured error & rejection logging
14. TASK 1: Chunk-based large dataset processing
15. TASK 2: Preservation of '*' and '#' in _suppression_indicator field
"""

import os
import sys
import json
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0, ".")
from src.pipeline.transformation import HealthcareTransformer, TransformationError


class TestSyntheticTransformationValidation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = os.path.join("tests", "fixtures", "transformation")
        cls.claims_csv = os.path.join(cls.fixtures_dir, "synthetic_claims_input.csv")
        cls.auth_csv = os.path.join(cls.fixtures_dir, "synthetic_authorizations_input.csv")
        cls.pde_csv = os.path.join(cls.fixtures_dir, "synthetic_pde_input.csv")
        cls.transformer = HealthcareTransformer()

    # =========================================================================
    # EXISTING SYNTHETIC TESTS
    # =========================================================================

    def test_01_synthetic_claims_transformation(self):
        """Validate real HealthcareTransformer on synthetic claims dataset."""
        df_raw = pd.read_csv(self.claims_csv, sep="|")
        records_in = len(df_raw)
        self.assertEqual(records_in, 29, "Synthetic claims input fixture should contain 29 records.")

        df_out, metrics = self.transformer.transform_claims(
            df_raw, source_file=self.claims_csv, batch_id="synthetic_batch_001"
        )

        self.assertEqual(metrics["records_in"], 29)
        self.assertEqual(metrics["records_out"], 29)
        self.assertTrue(metrics["grain_preserved"])
        self.assertEqual(len(df_out), 29)

        clm_001_lines = df_out[df_out["CLM_ID"] == "TEST_CLM_001"]
        self.assertEqual(len(clm_001_lines), 3, "TEST_CLM_001 must have 3 distinct claim line records.")
        self.assertEqual(list(clm_001_lines["CLM_LINE_NUM"].astype(str)), ["1", "2", "3"])

        self.assertEqual(df_out["CLM_ID"].iloc[0], "TEST_CLM_001")
        self.assertEqual(df_out["BENE_ID"].iloc[0], "TEST_BENE_001")
        self.assertEqual(df_out["CLM_FROM_DT"].iloc[0], "2026-01-15")
        self.assertAlmostEqual(df_out["CLM_PMT_AMT"].iloc[0], 1250.50)

    def test_02_synthetic_authorizations_transformation(self):
        """Validate real HealthcareTransformer on synthetic authorizations dataset."""
        df_raw = pd.read_csv(self.auth_csv, sep="|")
        records_in = len(df_raw)
        self.assertEqual(records_in, 5)

        df_out, metrics = self.transformer.transform_authorizations(
            df_raw, source_file=self.auth_csv, batch_id="synthetic_batch_001"
        )

        self.assertEqual(metrics["records_in"], 5)
        self.assertEqual(metrics["records_out"], 5)
        self.assertEqual(df_out["AUTH_ID"].iloc[0], "TEST_AUTH_001")
        self.assertEqual(df_out["AUTH_REQ_DT"].iloc[0], "2026-01-10")

    def test_03_synthetic_pde_transformation(self):
        """Validate real HealthcareTransformer on synthetic PDE dataset."""
        df_raw = pd.read_csv(self.pde_csv, sep="|")
        records_in = len(df_raw)
        self.assertEqual(records_in, 5)

        df_out, metrics = self.transformer.transform_pde(
            df_raw, source_file=self.pde_csv, batch_id="synthetic_batch_001"
        )

        self.assertEqual(metrics["records_in"], 5)
        self.assertEqual(metrics["records_out"], 5)
        self.assertEqual(df_out["PDE_ID"].iloc[0], "TEST_PDE_001")

    # =========================================================================
    # EDGE CASE TEST SUITE (13 EDGE CASES)
    # =========================================================================

    def test_edge_case_01_missing_null_values(self):
        """1. Verify handling of NULL values in required vs optional fields without silent corruption."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C101"],
            "CLM_LINE_NUM": ["1", "2"],
            "BENE_ID": ["B01", None],
            "CLM_FROM_DT": ["20260101", None],
            "CLM_PMT_AMT": [500.0, None]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_nulls.csv", "b01")
        
        self.assertEqual(len(df_out), 2)
        self.assertIsNone(df_out["BENE_ID"].iloc[1])
        self.assertIsNone(df_out["CLM_FROM_DT"].iloc[1])
        self.assertTrue(pd.isna(df_out["CLM_PMT_AMT"].iloc[1]))

    def test_edge_case_02_invalid_dates(self):
        """2. Verify malformed and impossible dates are handled safely and logged in rejections."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C101", "C102"],
            "CLM_FROM_DT": ["2026-01-15", "2026-13-45", "INVALID_DATE_STRING"]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_dates.csv", "b02")
        
        self.assertEqual(df_out["CLM_FROM_DT"].iloc[0], "2026-01-15")
        self.assertIsNone(df_out["CLM_FROM_DT"].iloc[1])
        self.assertIsNone(df_out["CLM_FROM_DT"].iloc[2])

        rej = metrics["rejections"]
        invalid_date_rejs = [r for r in rej if r["error_type"] == "INVALID_DATE"]
        self.assertEqual(len(invalid_date_rejs), 2)

    def test_edge_case_03_invalid_currency_strings(self):
        """3. Verify valid currency strings convert correctly and invalid strings become NaN without crashing."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C101", "C102", "C103"],
            "CLM_PMT_AMT": ["$1,250.50", "1,250.50", "INVALID_CURRENCY", ""]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_curr.csv", "b03")
        
        self.assertAlmostEqual(df_out["CLM_PMT_AMT"].iloc[0], 1250.50)
        self.assertAlmostEqual(df_out["CLM_PMT_AMT"].iloc[1], 1250.50)
        self.assertTrue(pd.isna(df_out["CLM_PMT_AMT"].iloc[2]))
        self.assertTrue(pd.isna(df_out["CLM_PMT_AMT"].iloc[3]))

    def test_edge_case_04_duplicate_records(self):
        """4. Verify duplicate claim lines are preserved 1:1 to maintain claim-line grain."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C100", "C100"],
            "CLM_LINE_NUM": ["1", "1", "2"],
            "CLM_PMT_AMT": [100.0, 100.0, 200.0]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_dups.csv", "b04")
        
        self.assertEqual(metrics["records_in"], 3)
        self.assertEqual(metrics["records_out"], 3)
        self.assertTrue(metrics["grain_preserved"])

    def test_edge_case_05_unexpected_columns(self):
        """5. Verify extra/unexpected columns in input pass through safely without corrupting output schema."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100"],
            "CLM_LINE_NUM": ["1"],
            "UNEXPECTED_VENDOR_TAG": ["EXTRA_VAL_XYZ"],
            "CUSTOM_FLAG": [123]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_extra.csv", "b05")
        
        self.assertIn("UNEXPECTED_VENDOR_TAG", df_out.columns)
        self.assertIn("CUSTOM_FLAG", df_out.columns)
        self.assertEqual(df_out["UNEXPECTED_VENDOR_TAG"].iloc[0], "EXTRA_VAL_XYZ")

    def test_edge_case_06_missing_columns(self):
        """6. Verify missing mandatory required columns raises TransformationError."""
        df_input = pd.DataFrame({
            "WRONG_COLUMN_NAME": ["VAL1"]
        })
        with self.assertRaises(TransformationError):
            self.transformer.transform_claims(df_input, "test_missing.csv", "b06")

    def test_edge_case_07_very_large_files(self):
        """7. Verify scalable memory-safe execution on 50,000 synthetic records."""
        n_rows = 50000
        df_large = pd.DataFrame({
            "CLM_ID": [f"C_{i//3}" for i in range(n_rows)],
            "CLM_LINE_NUM": [str((i % 3) + 1) for i in range(n_rows)],
            "BENE_ID": [f"B_{i % 1000}" for i in range(n_rows)],
            "CLM_FROM_DT": ["20260115"] * n_rows,
            "CLM_PMT_AMT": ["$100.00"] * n_rows
        })
        
        df_out, metrics = self.transformer.transform_claims(df_large, "large_file.csv", "b07")
        self.assertEqual(metrics["records_in"], n_rows)
        self.assertEqual(metrics["records_out"], n_rows)
        self.assertTrue(metrics["grain_preserved"])

    def test_edge_case_08_cms_suppression_values(self):
        """8. Verify CMS suppression indicators ('*', '#') are NOT converted to 0.0."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C101"],
            "CLM_PMT_AMT": ["*", "#"]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_cms_supp.csv", "b08")
        
        self.assertTrue(pd.isna(df_out["CLM_PMT_AMT"].iloc[0]))
        self.assertNotEqual(df_out["CLM_PMT_AMT"].iloc[0], 0.0)
        
        rejs = [r for r in metrics["rejections"] if r["error_type"] == "CMS_SUPPRESSION"]
        self.assertEqual(len(rejs), 2)

    def test_edge_case_09_npi_formats(self):
        """9. Verify 10-digit NPIs, float representations, and scientific notation stay clean strings."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C101", "C102"],
            "AT_PHYSN_NPI": [1234567890.0, 1.23456789e9, " 1234567890 "]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_npi.csv", "b09")
        
        self.assertEqual(df_out["AT_PHYSN_NPI"].iloc[0], "1234567890")
        self.assertEqual(df_out["AT_PHYSN_NPI"].iloc[1], "1234567890")
        self.assertEqual(df_out["AT_PHYSN_NPI"].iloc[2], "1234567890")

    def test_edge_case_10_unexpected_data_types(self):
        """10. Verify unexpected data types (ints as dates, floats as IDs) convert safely."""
        df_input = pd.DataFrame({
            "CLM_ID": [1001.0, 1002.0],
            "CLM_LINE_NUM": [1, 2],
            "CLM_FROM_DT": [20260115, 20260220]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_types.csv", "b10")
        
        self.assertEqual(df_out["CLM_ID"].iloc[0], "1001")
        self.assertEqual(df_out["CLM_LINE_NUM"].iloc[0], "1")
        self.assertEqual(df_out["CLM_FROM_DT"].iloc[0], "2026-01-15")

    def test_edge_case_11_malformed_records(self):
        """11. Verify malformed records generate structured rejections without crashing batch."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C101"],
            "CLM_FROM_DT": ["2026-01-15", "BAD_DATE_9999"],
            "CLM_PMT_AMT": ["$100.00", "NOT_A_NUMBER"]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "test_malformed.csv", "b11")
        
        self.assertEqual(len(df_out), 2)
        self.assertGreater(len(metrics["rejections"]), 0)

    def test_edge_case_12_multiple_batches(self):
        """12. Verify multi-batch execution keeps unique batch_id, source_file, and record lineage IDs."""
        df_batch1 = pd.DataFrame({"CLM_ID": ["C100"]})
        df_batch2 = pd.DataFrame({"CLM_ID": ["C100"]})
        
        out1, _ = self.transformer.transform_claims(df_batch1, "file_a.csv", "batch_alpha")
        out2, _ = self.transformer.transform_claims(df_batch2, "file_b.csv", "batch_beta")
        
        self.assertEqual(out1["_batch_id"].iloc[0], "batch_alpha")
        self.assertEqual(out2["_batch_id"].iloc[0], "batch_beta")
        self.assertNotEqual(out1["_record_lineage_id"].iloc[0], out2["_record_lineage_id"].iloc[0])

    def test_edge_case_13_error_rejection_logging(self):
        """13. Verify structured rejection log contains all mandatory diagnosis fields."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100"],
            "CLM_FROM_DT": ["INVALID_DATE"]
        })
        _, metrics = self.transformer.transform_claims(df_input, "file_err.csv", "batch_err")
        
        self.assertEqual(len(metrics["rejections"]), 1)
        rej = metrics["rejections"][0]
        
        self.assertIn("batch_id", rej)
        self.assertIn("source_file", rej)
        self.assertIn("record_identifier", rej)
        self.assertIn("column", rej)
        self.assertIn("error_type", rej)
        self.assertIn("error_message", rej)
        self.assertIn("rejection_reason", rej)

    # =========================================================================
    # TASK 1 & TASK 2 SPECIFIC ENHANCED TESTS
    # =========================================================================

    def test_task1_chunked_large_file_scalability(self):
        """TASK 1: Verify chunked processing handles large datasets accurately while maintaining metrics & grain."""
        n_rows = 25000
        chunk_sz = 5000
        df_large = pd.DataFrame({
            "CLM_ID": [f"C_{i//2}" for i in range(n_rows)],
            "CLM_LINE_NUM": [str((i % 2) + 1) for i in range(n_rows)],
            "BENE_ID": [f"B_{i % 500}" for i in range(n_rows)],
            "CLM_FROM_DT": ["20260115"] * n_rows,
            "CLM_PMT_AMT": ["$150.00"] * n_rows
        })

        df_out, metrics = self.transformer.transform_claims(
            df_large, source_file="large_chunked.csv", batch_id="batch_chunk_01", chunk_size=chunk_sz
        )

        self.assertEqual(metrics["records_in"], n_rows)
        self.assertEqual(metrics["records_out"], n_rows)
        self.assertEqual(metrics["chunks_processed"], 5)
        self.assertTrue(metrics["grain_preserved"])
        self.assertIn("throughput_rec_per_sec", metrics)
        
        # Verify lineage uniqueness across chunk boundaries
        self.assertEqual(len(df_out["_record_lineage_id"].unique()), n_rows)

    def test_task2_cms_suppression_indicator_metadata(self):
        """TASK 2: Verify '*' and '#' are saved in _suppression_indicator field and numerical fields are NaN (not zero)."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C101", "C102"],
            "CLM_PMT_AMT": ["*", "#", "$500.00"]
        })
        df_out, metrics = self.transformer.transform_claims(df_input, "suppression_test.csv", "b_supp")

        self.assertIn("_suppression_indicator", df_out.columns)
        
        # Row 0 (*)
        self.assertTrue(pd.isna(df_out["CLM_PMT_AMT"].iloc[0]))
        self.assertNotEqual(df_out["CLM_PMT_AMT"].iloc[0], 0.0)
        supp0 = json.loads(df_out["_suppression_indicator"].iloc[0])
        self.assertEqual(supp0.get("CLM_PMT_AMT"), "*")

        # Row 1 (#)
        self.assertTrue(pd.isna(df_out["CLM_PMT_AMT"].iloc[1]))
        self.assertNotEqual(df_out["CLM_PMT_AMT"].iloc[1], 0.0)
        supp1 = json.loads(df_out["_suppression_indicator"].iloc[1])
        self.assertEqual(supp1.get("CLM_PMT_AMT"), "#")

        # Row 2 ($500.00)
        self.assertAlmostEqual(df_out["CLM_PMT_AMT"].iloc[2], 500.00)
        self.assertIsNone(df_out["_suppression_indicator"].iloc[2])


if __name__ == "__main__":
    unittest.main()
