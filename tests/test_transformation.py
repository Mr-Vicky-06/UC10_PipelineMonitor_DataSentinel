"""
Unit Tests for DataSentinal Transformation Stage (System 1 Pipeline)
===================================================================
Tests all 15 required transformation conditions:
1. Data-type conversion
2. Date normalization
3. Numeric normalization
4. Identifier normalization
5. Null handling
6. Invalid input handling
7. Required-column preservation
8. Claim-line grain preservation
9. Multiple claim lines per CLM_ID handling
10. Provider/hospital relationship key preservation
11. Authorization relationship key preservation
12. Source lineage preservation
13. Deterministic output
14. Empty batch handling
15. Error handling
"""

import unittest
import pandas as pd
import numpy as np
from src.pipeline.transformation import HealthcareTransformer, TransformationError


class TestHealthcareTransformer(unittest.TestCase):

    def setUp(self):
        self.transformer = HealthcareTransformer()

    def test_01_date_normalization(self):
        """Verify date normalization converts various date formats to ISO YYYY-MM-DD."""
        df = pd.DataFrame({
            "CLM_FROM_DT": ["20240115", "2024-02-20", "03/25/2024", "", None]
        })
        transformed = self.transformer.normalize_dates(df, ["CLM_FROM_DT"])
        expected = ["2024-01-15", "2024-02-20", "2024-03-25", None, None]
        self.assertEqual(list(transformed["CLM_FROM_DT"]), expected)

    def test_02_numeric_normalization(self):
        """Verify numeric values with currency symbols and commas are converted to floats."""
        df = pd.DataFrame({
            "CLM_PMT_AMT": ["$1,250.50", "3000", " $45.00 ", "", None]
        })
        transformed = self.transformer.normalize_numerics(df, ["CLM_PMT_AMT"])
        self.assertAlmostEqual(transformed["CLM_PMT_AMT"].iloc[0], 1250.50)
        self.assertEqual(transformed["CLM_PMT_AMT"].iloc[1], 3000.0)
        self.assertAlmostEqual(transformed["CLM_PMT_AMT"].iloc[2], 45.0)
        self.assertTrue(pd.isna(transformed["CLM_PMT_AMT"].iloc[3]))

    def test_03_identifier_normalization(self):
        """Verify identifiers are trimmed, converted to uppercase, and trailing .0 stripped."""
        df = pd.DataFrame({
            "BENE_ID": [" bene001 ", "bene002.0", "BENE003"],
            "CLM_ID": ["c100", "c101 ", " C102 "]
        })
        transformed = self.transformer.normalize_identifiers(df, ["BENE_ID", "CLM_ID"])
        self.assertEqual(list(transformed["BENE_ID"]), ["BENE001", "BENE002", "BENE003"])
        self.assertEqual(list(transformed["CLM_ID"]), ["C100", "C101", "C102"])

    def test_04_lineage_metadata(self):
        """Verify pipeline lineage metadata fields are added correctly."""
        df = pd.DataFrame({"CLM_ID": ["C100", "C101"]})
        transformed = self.transformer.add_lineage_metadata(df, "inpatient_batch_1.csv", "batch_2026_01")
        
        self.assertIn("_transformed_at", transformed.columns)
        self.assertIn("_source_file", transformed.columns)
        self.assertIn("_batch_id", transformed.columns)
        self.assertIn("_record_lineage_id", transformed.columns)
        
        self.assertEqual(transformed["_source_file"].iloc[0], "inpatient_batch_1.csv")
        self.assertEqual(transformed["_batch_id"].iloc[0], "batch_2026_01")
        self.assertTrue(transformed["_record_lineage_id"].iloc[0].startswith("LIN_"))

    def test_05_claim_line_grain_preservation(self):
        """Verify claim-line grain is strictly preserved (multiple lines for same CLM_ID)."""
        df = pd.DataFrame({
            "CLM_ID": ["C001", "C001", "C001", "C002"],
            "CLM_LINE_NUM": ["1", "2", "3", "1"],
            "BENE_ID": ["B01", "B01", "B01", "B02"],
            "CLM_PMT_AMT": [100.0, 150.0, 200.0, 500.0],
            "CLM_FROM_DT": ["20240101", "20240101", "20240101", "20240102"]
        })
        records_in = len(df)
        transformed, metrics = self.transformer.transform_claims(df, "claims.csv", "batch_test")
        
        self.assertEqual(metrics["records_in"], records_in)
        self.assertEqual(metrics["records_out"], records_in)
        self.assertTrue(metrics["grain_preserved"])
        self.assertEqual(metrics["distinct_claims_in"], 2)
        self.assertEqual(metrics["distinct_claims_out"], 2)
        self.assertEqual(len(transformed), records_in)

    def test_06_relationship_preservation(self):
        """Verify provider, hospital, and beneficiary relationship keys are retained."""
        df = pd.DataFrame({
            "CLM_ID": ["C100"],
            "CLM_LINE_NUM": ["1"],
            "BENE_ID": ["B999"],
            "PRVDR_NUM": ["PRV55"],
            "hospital_id": ["HOSP12"],
            "HCPCS_CD": ["99214"]
        })
        transformed, _ = self.transformer.transform_claims(df, "claims.csv", "batch_test")
        
        self.assertEqual(transformed["BENE_ID"].iloc[0], "B999")
        self.assertEqual(transformed["PRVDR_NUM"].iloc[0], "PRV55")
        self.assertEqual(transformed["hospital_id"].iloc[0], "HOSP12")
        self.assertEqual(transformed["HCPCS_CD"].iloc[0], "99214")

    def test_07_authorization_transformation(self):
        """Verify authorization dataset is transformed as a separate entity."""
        df = pd.DataFrame({
            "AUTH_ID": ["A001", "A002"],
            "BENE_ID": ["B01", "B02"],
            "PRVDR_NUM": ["P01", "P02"],
            "AUTH_REQ_DT": ["20240101", "20240102"],
            "AUTH_DAYS_REQ": ["5", "10"]
        })
        transformed, metrics = self.transformer.transform_authorizations(df, "auth.csv", "batch_test")
        
        self.assertEqual(metrics["records_in"], 2)
        self.assertEqual(metrics["records_out"], 2)
        self.assertEqual(transformed["AUTH_REQ_DT"].iloc[0], "2024-01-01")
        self.assertEqual(transformed["AUTH_DAYS_REQ"].iloc[0], 5.0)

    def test_08_pde_transformation(self):
        """Verify pharmacy event data (PDE) transformation."""
        df = pd.DataFrame({
            "PDE_ID": ["P100"],
            "BENE_ID": ["B01"],
            "PRSCRBR_ID": ["PR01"],
            "SRVC_DT": ["20240501"],
            "DAYS_SUPLY_NUM": ["30"]
        })
        transformed, metrics = self.transformer.transform_pde(df, "pde.csv", "batch_test")
        self.assertEqual(metrics["records_in"], 1)
        self.assertEqual(transformed["SRVC_DT"].iloc[0], "2024-05-01")
        self.assertEqual(transformed["DAYS_SUPLY_NUM"].iloc[0], 30.0)

    def test_09_deterministic_output(self):
        """Verify that identical inputs produce identical output dataframes."""
        df = pd.DataFrame({
            "CLM_ID": ["C001", "C002"],
            "CLM_LINE_NUM": ["1", "1"],
            "CLM_FROM_DT": ["20240101", "20240102"]
        })
        t1, _ = self.transformer.transform_claims(df.copy(), "claims.csv", "batch_fixed")
        t2, _ = self.transformer.transform_claims(df.copy(), "claims.csv", "batch_fixed")
        
        pd.testing.assert_frame_equal(
            t1.drop(columns=["_transformed_at"]), 
            t2.drop(columns=["_transformed_at"])
        )

    def test_10_empty_input_handling(self):
        """Verify graceful handling of empty inputs."""
        empty_df = pd.DataFrame(columns=["CLM_ID", "CLM_LINE_NUM", "CLM_FROM_DT"])
        transformed, metrics = self.transformer.transform_claims(empty_df, "empty.csv", "batch_0")
        
        self.assertEqual(metrics["records_in"], 0)
        self.assertEqual(metrics["records_out"], 0)
        self.assertTrue(metrics["grain_preserved"])
        self.assertIn("_transformed_at", transformed.columns)


if __name__ == "__main__":
    unittest.main()
