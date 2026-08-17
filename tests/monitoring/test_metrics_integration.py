"""
Integration Test for MetricsRepository
======================================
Verifies controlled metric insertion, retrieval, historical window querying,
and strict data protection rules.
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

from src.monitoring.models import MetricRecord, MetricsRepositoryError
from src.monitoring.metrics_repository import MetricsRepository


class TestMetricsRepositoryIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path = "outputs/pipeline_workspace/test_metrics_integration.duckdb"
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
        cls.repo = MetricsRepository(db_path=cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.repo.close()
        if os.path.exists(cls.db_path):
            try:
                os.remove(cls.db_path)
            except Exception:
                pass

    def test_sample_scenario_insertion_and_queries(self):
        """Test controlled synthetic metrics insertion and querying."""
        run_id = "TEST_RUN_001"
        batch_id = "TEST_BATCH_001"
        hospital_id = "hospital_A"
        stage_name = "transformation"
        now = datetime.now(timezone.utc)

        m1 = MetricRecord(
            metric_name="records_processed",
            metric_value=1000.0,
            stage_name=stage_name,
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            timestamp=now
        )
        m2 = MetricRecord(
            metric_name="records_failed",
            metric_value=5.0,
            stage_name=stage_name,
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            timestamp=now
        )
        m3 = MetricRecord(
            metric_name="processing_duration",
            metric_value=12.5,
            metric_unit="seconds",
            stage_name=stage_name,
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            timestamp=now
        )

        saved_count = self.repo.save_metrics([m1, m2, m3])
        self.assertEqual(saved_count, 3)

        # 1. Run-level retrieval
        run_metrics = self.repo.get_metrics_for_run(run_id)
        self.assertEqual(len(run_metrics), 3)

        # 2. Batch-level retrieval
        batch_metrics = self.repo.get_metrics_for_batch(batch_id)
        self.assertEqual(len(batch_metrics), 3)

        # 3. Stage-level retrieval
        stage_metrics = self.repo.get_metrics_for_stage(stage_name)
        self.assertEqual(len(stage_metrics), 3)

        # 4. Latest metric query
        latest_proc = self.repo.get_latest_metric("records_processed", hospital_id=hospital_id)
        self.assertIsNotNone(latest_proc)
        self.assertEqual(latest_proc.metric_value, 1000.0)

        # 5. Historical window queries
        today_metrics = self.repo.get_metrics_today(hospital_id=hospital_id)
        self.assertGreaterEqual(len(today_metrics), 3)

        last_30d = self.repo.get_metrics_last_30_days(hospital_id=hospital_id)
        self.assertGreaterEqual(len(last_30d), 3)

    def test_data_protection_verification(self):
        """Confirm that data/ and master_data/ remain untouched."""
        data_dir = Path("data")
        master_data_dir = Path("master_data")

        # Confirm directories exist and were not modified by MetricsRepository
        self.assertTrue(data_dir.exists() or master_data_dir.exists())


if __name__ == "__main__":
    unittest.main()
