"""
Comprehensive Unit Test Suite for MetricsRepository
===================================================
Covers all 20 required operations, filter scenarios, error cases, and time windows.
"""

import unittest
from datetime import datetime, date, timedelta, timezone
import os

from src.monitoring.models import MetricRecord, MetricsRepositoryError
from src.monitoring.metrics_repository import MetricsRepository


class TestMetricsRepository(unittest.TestCase):

    def setUp(self):
        """Set up an isolated in-memory MetricsRepository for each test."""
        self.repo = MetricsRepository(db_path=":memory:")

    # 1. Metric insertion
    def test_01_save_metric_single(self):
        record = MetricRecord(
            metric_name="records_processed",
            metric_value=1000.0,
            stage_name="transformation",
            run_id="RUN_001",
            batch_id="BATCH_001",
            hospital_id="hospital_A"
        )
        metric_id = self.repo.save_metric(record)
        self.assertEqual(metric_id, record.metric_id)

        retrieved = self.repo.get_latest_metric("records_processed", hospital_id="hospital_A")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.metric_value, 1000.0)

    # 2. Multiple metric insertion
    def test_02_save_metrics_bulk(self):
        records = [
            MetricRecord(metric_name="records_processed", metric_value=500.0, stage_name="cleaning", run_id="RUN_002"),
            MetricRecord(metric_name="records_failed", metric_value=5.0, stage_name="cleaning", run_id="RUN_002"),
            MetricRecord(metric_name="processing_duration", metric_value=12.5, stage_name="cleaning", run_id="RUN_002")
        ]
        count = self.repo.save_metrics(records)
        self.assertEqual(count, 3)

        retrieved_list = self.repo.get_metrics_for_run("RUN_002")
        self.assertEqual(len(retrieved_list), 3)

    # 3. Metric retrieval
    def test_03_metric_retrieval(self):
        record = MetricRecord(metric_name="null_count", metric_value=42.0, stage_name="validation")
        self.repo.save_metric(record)

        results = self.repo.get_metrics_for_stage("validation")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metric_name, "null_count")
        self.assertEqual(results[0].metric_value, 42.0)

    # 4. Latest metric retrieval
    def test_04_get_latest_metric(self):
        t1 = datetime.now() - timedelta(minutes=10)
        t2 = datetime.now()

        m1 = MetricRecord(metric_name="cpu_usage", metric_value=45.0, stage_name="ingestion", timestamp=t1)
        m2 = MetricRecord(metric_name="cpu_usage", metric_value=85.0, stage_name="ingestion", timestamp=t2)

        self.repo.save_metric(m1)
        self.repo.save_metric(m2)

        latest = self.repo.get_latest_metric("cpu_usage", stage_name="ingestion")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.metric_value, 85.0)

    # 5. Run-level retrieval
    def test_05_get_metrics_for_run(self):
        self.repo.save_metric(MetricRecord(metric_name="m1", metric_value=1.0, stage_name="s1", run_id="RUN_ALPHA"))
        self.repo.save_metric(MetricRecord(metric_name="m2", metric_value=2.0, stage_name="s1", run_id="RUN_ALPHA"))
        self.repo.save_metric(MetricRecord(metric_name="m3", metric_value=3.0, stage_name="s1", run_id="RUN_BETA"))

        alpha_metrics = self.repo.get_metrics_for_run("RUN_ALPHA")
        self.assertEqual(len(alpha_metrics), 2)

    # 6. Batch-level retrieval
    def test_06_get_metrics_for_batch(self):
        self.repo.save_metric(MetricRecord(metric_name="m1", metric_value=10.0, stage_name="s1", batch_id="BATCH_100"))
        self.repo.save_metric(MetricRecord(metric_name="m2", metric_value=20.0, stage_name="s1", batch_id="BATCH_200"))

        batch_100 = self.repo.get_metrics_for_batch("BATCH_100")
        self.assertEqual(len(batch_100), 1)
        self.assertEqual(batch_100[0].metric_value, 10.0)

    # 7. Stage-level retrieval
    def test_07_get_metrics_for_stage(self):
        self.repo.save_metric(MetricRecord(metric_name="m1", metric_value=1.0, stage_name="cleaning"))
        self.repo.save_metric(MetricRecord(metric_name="m2", metric_value=2.0, stage_name="transformation"))

        cleaning_metrics = self.repo.get_metrics_for_stage("cleaning")
        self.assertEqual(len(cleaning_metrics), 1)
        self.assertEqual(cleaning_metrics[0].stage_name, "cleaning")

    # 8. Time-range retrieval
    def test_08_get_historical_metrics(self):
        now = datetime.now()
        t_start = now - timedelta(hours=2)
        t_mid = now - timedelta(hours=1)
        t_end = now

        self.repo.save_metric(MetricRecord(metric_name="m_early", metric_value=1.0, stage_name="s", timestamp=t_start))
        self.repo.save_metric(MetricRecord(metric_name="m_mid", metric_value=2.0, stage_name="s", timestamp=t_mid))
        self.repo.save_metric(MetricRecord(metric_name="m_late", metric_value=3.0, stage_name="s", timestamp=now + timedelta(hours=5)))

        res = self.repo.get_historical_metrics(t_start, t_end)
        self.assertEqual(len(res), 2)

    # 9. Today query
    def test_09_get_metrics_today(self):
        now = datetime.now()
        yesterday_ts = now - timedelta(days=1)

        self.repo.save_metric(MetricRecord(metric_name="today_metric", metric_value=100.0, stage_name="s", timestamp=now))
        self.repo.save_metric(MetricRecord(metric_name="old_metric", metric_value=50.0, stage_name="s", timestamp=yesterday_ts))

        today_metrics = self.repo.get_metrics_today()
        self.assertEqual(len(today_metrics), 1)
        self.assertEqual(today_metrics[0].metric_name, "today_metric")

    # 10. Yesterday query
    def test_10_get_metrics_yesterday(self):
        now = datetime.now()
        yesterday_ts = now - timedelta(days=1)

        self.repo.save_metric(MetricRecord(metric_name="today_metric", metric_value=100.0, stage_name="s", timestamp=now))
        self.repo.save_metric(MetricRecord(metric_name="yesterday_metric", metric_value=50.0, stage_name="s", timestamp=yesterday_ts))

        yesterday_metrics = self.repo.get_metrics_yesterday()
        self.assertEqual(len(yesterday_metrics), 1)
        self.assertEqual(yesterday_metrics[0].metric_name, "yesterday_metric")

    # 11. 30-day query
    def test_11_get_metrics_last_30_days(self):
        now = datetime.now()
        t_15d = now - timedelta(days=15)
        t_45d = now - timedelta(days=45)

        self.repo.save_metric(MetricRecord(metric_name="m15", metric_value=15.0, stage_name="s", timestamp=t_15d))
        self.repo.save_metric(MetricRecord(metric_name="m45", metric_value=45.0, stage_name="s", timestamp=t_45d))

        res = self.repo.get_metrics_last_30_days()
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].metric_name, "m15")

    # 12. 6-month query
    def test_12_get_metrics_last_6_months(self):
        now = datetime.now()
        t_60d = now - timedelta(days=60)
        t_300d = now - timedelta(days=300)

        self.repo.save_metric(MetricRecord(metric_name="m60", metric_value=60.0, stage_name="s", timestamp=t_60d))
        self.repo.save_metric(MetricRecord(metric_name="m300", metric_value=300.0, stage_name="s", timestamp=t_300d))

        res = self.repo.get_metrics_last_6_months()
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].metric_name, "m60")

    # 13. Invalid metric handling
    def test_13_invalid_metric_handling(self):
        invalid_metric = MetricRecord(metric_name="", metric_value=10.0, stage_name="s")
        with self.assertRaises(MetricsRepositoryError):
            self.repo.save_metric(invalid_metric)

    # 14. Missing required field handling
    def test_14_missing_required_field_handling(self):
        record = MetricRecord(metric_name="test", metric_value=None, stage_name="s")  # type: ignore
        with self.assertRaises(MetricsRepositoryError):
            self.repo.save_metric(record)

    # 15. Duplicate behavior
    def test_15_duplicate_metric_id_handling(self):
        m1 = MetricRecord(metric_id="FIXED_ID_100", metric_name="test", metric_value=1.0, stage_name="s")
        m2 = MetricRecord(metric_id="FIXED_ID_100", metric_name="test", metric_value=2.0, stage_name="s")

        self.repo.save_metric(m1)
        with self.assertRaises(MetricsRepositoryError):
            self.repo.save_metric(m2)

    # 16. Database error handling
    def test_16_database_error_handling(self):
        # Query invalid table or column safely
        with self.assertRaises(MetricsRepositoryError):
            self.repo.get_metrics_for_run(12345)  # type: ignore

    # 17. Timestamp handling
    def test_17_timestamp_handling(self):
        utc_ts = datetime.now(timezone.utc)
        m = MetricRecord(metric_name="utc_test", metric_value=1.0, stage_name="s", timestamp=utc_ts)
        self.repo.save_metric(m)

        retrieved = self.repo.get_latest_metric("utc_test")
        self.assertIsNotNone(retrieved)
        self.assertIsNotNone(retrieved.timestamp)

    # 18. Hospital/stage filtering
    def test_18_hospital_and_stage_filtering(self):
        self.repo.save_metric(MetricRecord(metric_name="m1", metric_value=1.0, stage_name="stage1", hospital_id="HOSP_A"))
        self.repo.save_metric(MetricRecord(metric_name="m1", metric_value=2.0, stage_name="stage1", hospital_id="HOSP_B"))
        self.repo.save_metric(MetricRecord(metric_name="m1", metric_value=3.0, stage_name="stage2", hospital_id="HOSP_A"))

        hosp_a_stage1 = self.repo.get_metrics_since(datetime.now() - timedelta(days=1), hospital_id="HOSP_A", stage_name="stage1")
        self.assertEqual(len(hosp_a_stage1), 1)
        self.assertEqual(hosp_a_stage1[0].metric_value, 1.0)

    # 19. Metric dimension filtering
    def test_19_metric_dimensions(self):
        dims = {"schema_version": "v1.2", "environment": "production", "error_code": "E500"}
        record = MetricRecord(metric_name="dim_test", metric_value=5.0, stage_name="s", dimensions=dims)
        self.repo.save_metric(record)

        retrieved = self.repo.get_latest_metric("dim_test")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.dimensions.get("schema_version"), "v1.2")
        self.assertEqual(retrieved.dimensions.get("error_code"), "E500")

    # 20. Health check
    def test_20_health_check(self):
        self.assertTrue(self.repo.health_check())


if __name__ == "__main__":
    unittest.main()
