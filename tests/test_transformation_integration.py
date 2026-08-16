"""
Transformation Integration & UC10 Monitoring Test Suite
======================================================
Tests:
- Task 1: Transformation → Feature Engineering integration
- Task 2: UC10 Monitoring telemetry export & anomaly detection flags
- Task 3: Failure, retry recovery, reprocessing & idempotency verification
- Task 4: Very large-scale benchmark validation (1M+ records)
"""

import sys
import os
import json
import time
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0, ".")
from src.pipeline.transformation import HealthcareTransformer, TransformationError


class TestTransformationIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.transformer = HealthcareTransformer()
        cls.fixtures_dir = os.path.join("tests", "fixtures", "transformation")
        cls.claims_csv = os.path.join(cls.fixtures_dir, "synthetic_claims_input.csv")
        cls.pde_csv = os.path.join(cls.fixtures_dir, "synthetic_pde_input.csv")

    # =========================================================================
    # TASK 1: TRANSFORMATION → FEATURE ENGINEERING INTEGRATION
    # =========================================================================

    def test_task1_feature_engineering_integration(self):
        """Task 1: Verify transformed data feeds into downstream feature engineering calculations."""
        df_claims_raw = pd.read_csv(self.claims_csv, sep="|")
        df_pde_raw = pd.read_csv(self.pde_csv, sep="|")

        transformed_claims, claims_m = self.transformer.transform_claims(
            df_claims_raw, source_file=self.claims_csv, batch_id="batch_integ_01"
        )
        transformed_pde, pde_m = self.transformer.transform_pde(
            df_pde_raw, source_file=self.pde_csv, batch_id="batch_integ_01"
        )

        # Verify lineage & metadata fields exist
        for col in ["_source_file", "_batch_id", "_record_lineage_id", "_transformed_at"]:
            self.assertIn(col, transformed_claims.columns)
            self.assertIn(col, transformed_pde.columns)

        # Compute daily claims aggregation (Feature Engineering contract)
        claims_daily = transformed_claims.groupby("CLM_FROM_DT").agg(
            claim_count=("CLM_ID", "count"),
            median_claim_amount=("CLM_PMT_AMT", "median"),
            null_bene_count=("BENE_ID", lambda s: s.isna().sum())
        ).reset_index()

        self.assertGreater(len(claims_daily), 0)
        self.assertIn("claim_count", claims_daily.columns)
        self.assertEqual(claims_daily["claim_count"].sum(), len(transformed_claims))

    # =========================================================================
    # TASK 2: UC10 MONITORING METRICS INTEGRATION
    # =========================================================================

    def test_task2_uc10_monitoring_telemetry(self):
        """Task 2: Verify structured monitoring telemetry export and anomaly detection flags."""
        df_input = pd.DataFrame({
            "CLM_ID": [f"C_{i}" for i in range(100)],
            "CLM_FROM_DT": ["2026-01-15"] * 90 + ["INVALID_DATE"] * 10,  # 10% invalid dates
            "CLM_PMT_AMT": ["$100.00"] * 100
        })

        _, metrics = self.transformer.transform_claims(df_input, "telemetry_test.csv", "batch_mon_01")
        telemetry = self.transformer.get_monitoring_telemetry(metrics)

        # Verify all mandatory telemetry keys
        expected_keys = [
            "batch_id", "source_file", "records_in", "records_out", "records_rejected",
            "rejection_rate", "chunks_processed", "processing_time_sec",
            "throughput_records_per_sec", "transformation_status", "error_count",
            "rejection_types", "anomalies_detected", "timestamp"
        ]
        for key in expected_keys:
            self.assertIn(key, telemetry)

        self.assertEqual(telemetry["records_in"], 100)
        self.assertEqual(telemetry["records_rejected"], 10)
        self.assertEqual(telemetry["rejection_rate"], 0.10)
        self.assertEqual(telemetry["transformation_status"], "WARNING_HIGH_REJECTIONS")
        self.assertIn("HIGH_TRANSFORMATION_REJECTION_RATE", telemetry["anomalies_detected"])

    # =========================================================================
    # TASK 3: FAILURE / RETRY / REPROCESSING TESTING (IDEMPOTENCY)
    # =========================================================================

    def test_task3_failure_retry_idempotency(self):
        """Task 3: Verify retry execution handles batch idempotency without duplicate records."""
        df_input = pd.DataFrame({
            "CLM_ID": ["C100", "C101"],
            "CLM_LINE_NUM": ["1", "1"],
            "CLM_PMT_AMT": [100.0, 200.0]
        })

        # 1. Initial execution
        out1, m1 = self.transformer.transform_claims(df_input, "claims.csv", batch_id="batch_retry_01", is_retry=False)
        self.assertEqual(m1["records_out"], 2)
        self.assertEqual(m1["status"], "SUCCESS")

        # 2. Retry execution (same batch_id)
        out2, m2 = self.transformer.transform_claims(df_input, "claims.csv", batch_id="batch_retry_01", is_retry=True)
        self.assertEqual(m2["records_out"], 2)
        self.assertEqual(m2["status"], "SUCCESS_RETRY")
        self.assertEqual(len(out2), 2, "Retry must not produce 2x batch output records.")

        # Verify idempotency (DataFrames identical excluding timestamp)
        pd.testing.assert_frame_equal(
            out1.drop(columns=["_transformed_at"]),
            out2.drop(columns=["_transformed_at"])
        )

    # =========================================================================
    # TASK 4: VERY LARGE-SCALE SCALABILITY TESTING
    # =========================================================================

    def test_task4_large_scale_scalability_1m(self):
        """Task 4: Scalability test on 1,000,000 synthetic records using chunking."""
        n_rows = 1000000
        chunk_sz = 100000
        
        df_large = pd.DataFrame({
            "CLM_ID": [f"C_{i//2:07d}" for i in range(n_rows)],
            "CLM_LINE_NUM": [str((i % 2) + 1) for i in range(n_rows)],
            "BENE_ID": [f"B_{i % 10000:05d}" for i in range(n_rows)],
            "CLM_FROM_DT": ["20260115"] * n_rows,
            "CLM_PMT_AMT": ["$150.00"] * n_rows
        })

        df_out, metrics = self.transformer.transform_claims(
            df_large, source_file="scale_1m.csv", batch_id="batch_1m", chunk_size=chunk_sz
        )

        self.assertEqual(metrics["records_in"], n_rows)
        self.assertEqual(metrics["records_out"], n_rows)
        self.assertEqual(metrics["chunks_processed"], 10)
        self.assertTrue(metrics["grain_preserved"])
        self.assertGreater(metrics["throughput_rec_per_sec"], 10000)


if __name__ == "__main__":
    unittest.main()
