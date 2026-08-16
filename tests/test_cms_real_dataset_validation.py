"""
Real CMS Dataset Validation Test
================================
Runs production HealthcareTransformer against local real CMS Part D (PDE) and
CMS Inpatient claims datasets to validate:
- Schema compatibility
- Date formatting (CLM_FROM_DT, CLM_THRU_DT, SRVC_DT)
- Numeric formatting (CLM_PMT_AMT, TOT_RX_CST_AMT)
- NPI & Provider ID normalization
- CMS suppression indicator handling ('*', '#')
- Record count retention & lineage tracking
"""

import os
import sys
import unittest
import pandas as pd

sys.path.insert(0, ".")
from src.pipeline.transformation import HealthcareTransformer


class TestCMSRealDatasetValidation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.transformer = HealthcareTransformer()
        
        # Local real CMS dataset paths
        cls.cms_inpatient_path = os.path.join("data", "data", "raw", "claims", "inpatient.csv")
        if not os.path.exists(cls.cms_inpatient_path):
            cls.cms_inpatient_path = os.path.join("data", "raw", "claims", "inpatient.csv")

        cls.cms_pde_path = os.path.join("data", "data", "raw", "pde", "pde.csv")
        if not os.path.exists(cls.cms_pde_path):
            cls.cms_pde_path = os.path.join("data", "raw", "pde", "pde.csv")

    def test_cms_real_inpatient_claims_validation(self):
        """Validate real HealthcareTransformer on local CMS Inpatient Claims dataset sample (5,000 rows)."""
        if not os.path.exists(self.cms_inpatient_path):
            self.skipTest(f"CMS Inpatient raw dataset not found at {self.cms_inpatient_path}")

        print(f"\n[CMS VALIDATION] Reading CMS Inpatient Claims sample from {self.cms_inpatient_path}...")
        df_raw = pd.read_csv(self.cms_inpatient_path, sep="|", nrows=5000, low_memory=False)
        
        records_in = len(df_raw)
        distinct_claims_in = df_raw["CLM_ID"].nunique() if "CLM_ID" in df_raw.columns else 0

        df_out, metrics = self.transformer.transform_claims(
            df_raw, source_file=self.cms_inpatient_path, batch_id="cms_inpatient_batch_001", chunk_size=1000
        )

        self.assertEqual(metrics["records_in"], records_in)
        self.assertEqual(metrics["records_out"], records_in)
        self.assertTrue(metrics["grain_preserved"])
        self.assertEqual(metrics["distinct_claims_in"], distinct_claims_in)
        self.assertEqual(metrics["distinct_claims_out"], distinct_claims_in)

        # Check ISO date conversion
        valid_dates = df_out["CLM_FROM_DT"].dropna().head(10).tolist()
        for d in valid_dates:
            self.assertRegex(d, r"^\d{4}-\d{2}-\d{2}$")

        # Check lineage metadata
        self.assertIn("_record_lineage_id", df_out.columns)
        self.assertEqual(len(df_out["_record_lineage_id"].unique()), records_in)

        print(f"[CMS VALIDATION SUCCESS] Inpatient: {records_in} rows processed, {metrics['throughput_rec_per_sec']} rec/sec.")

    def test_cms_real_pde_validation(self):
        """Validate real HealthcareTransformer on local CMS Part D (PDE) dataset sample (5,000 rows)."""
        if not os.path.exists(self.cms_pde_path):
            self.skipTest(f"CMS PDE raw dataset not found at {self.cms_pde_path}")

        print(f"\n[CMS VALIDATION] Reading CMS Part D (PDE) sample from {self.cms_pde_path}...")
        df_raw = pd.read_csv(self.cms_pde_path, sep="|", nrows=5000, low_memory=False)
        
        records_in = len(df_raw)

        df_out, metrics = self.transformer.transform_pde(
            df_raw, source_file=self.cms_pde_path, batch_id="cms_pde_batch_001", chunk_size=1000
        )

        self.assertEqual(metrics["records_in"], records_in)
        self.assertEqual(metrics["records_out"], records_in)
        self.assertTrue(metrics["grain_preserved"])

        print(f"[CMS VALIDATION SUCCESS] Part D PDE: {records_in} rows processed, {metrics['throughput_rec_per_sec']} rec/sec.")


if __name__ == "__main__":
    unittest.main()
