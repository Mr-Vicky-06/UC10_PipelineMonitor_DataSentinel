import unittest
import os
import uuid
from pathlib import Path
import duckdb

from src.pipeline.telemetry import PipelineTelemetryLogger, TelemetryEvent, PipelineStage, TelemetryStatus

class TestTelemetryLogger(unittest.TestCase):
    def setUp(self):
        self.db_path = "tests/test_outputs/telemetry_test.duckdb"
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()
            
        self.logger = PipelineTelemetryLogger(db_path=self.db_path)

    def tearDown(self):
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()

    def test_schema_and_persistence(self):
        """Test telemetry schema initialization and simple persistence."""
        event = TelemetryEvent(
            run_id="run_1",
            hospital_id="HOSP-A",
            batch_id="BATCH-1",
            stage=PipelineStage.INGESTION,
            status=TelemetryStatus.STARTED,
            source_file="file1.csv",
            service_date="2026-01-01"
        )
        self.logger.log_event(event)
        
        with duckdb.connect(self.db_path) as con:
            res = con.execute("SELECT run_id, stage, status, source_file FROM pipeline_events").fetchall()
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0][0], "run_1")
            self.assertEqual(res[0][1], "INGESTION")
            self.assertEqual(res[0][2], "STARTED")
            self.assertEqual(res[0][3], "file1.csv")

    def test_started_completed_correlation(self):
        """Test that STARTED and COMPLETED events share correlation ID."""
        corr_id = str(uuid.uuid4())
        
        start = TelemetryEvent(
            correlation_id=corr_id,
            run_id="run_1",
            hospital_id="HOSP-A",
            batch_id="BATCH-1",
            stage=PipelineStage.TRANSFORMATION,
            status=TelemetryStatus.STARTED
        )
        
        complete = TelemetryEvent(
            correlation_id=corr_id,
            run_id="run_1",
            hospital_id="HOSP-A",
            batch_id="BATCH-1",
            stage=PipelineStage.TRANSFORMATION,
            status=TelemetryStatus.COMPLETED,
            duration_ms=500,
            records_in=100,
            records_out=100
        )
        
        self.logger.log_event(start)
        self.logger.log_event(complete)
        
        with duckdb.connect(self.db_path) as con:
            res = con.execute("SELECT status, duration_ms FROM pipeline_events WHERE correlation_id = ? ORDER BY timestamp ASC", [corr_id]).fetchall()
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0][0], "STARTED")
            self.assertEqual(res[0][1], 0)
            self.assertEqual(res[1][0], "COMPLETED")
            self.assertEqual(res[1][1], 500)

    def test_failed_stage_logging(self):
        """Test that errors correctly log the FAILED status with metadata."""
        err = TelemetryEvent(
            run_id="run_2",
            hospital_id="HOSP-B",
            batch_id="BATCH-2",
            stage=PipelineStage.VALIDATION,
            status=TelemetryStatus.FAILED,
            error_type="ValueError",
            error_message="Invalid schema format"
        )
        self.logger.log_event(err)
        
        with duckdb.connect(self.db_path) as con:
            res = con.execute("SELECT status, error_type, error_message FROM pipeline_events WHERE run_id = 'run_2'").fetchall()
            self.assertEqual(res[0][0], "FAILED")
            self.assertEqual(res[0][1], "ValueError")
            self.assertEqual(res[0][2], "Invalid schema format")

    def test_fail_open_behavior(self):
        """Test that telemetry logger fails open and does not crash the app if DB is locked or read-only."""
        # Open a read-only connection that locks the DB in exclusive mode (if we simulate it)
        # Actually DuckDB concurrent writes are a thing, but we can simulate failure by passing a directory instead of file
        bad_logger = PipelineTelemetryLogger(db_path="tests/test_outputs/") # Directory, should fail to open
        
        # This should NOT raise an exception
        try:
            bad_logger.log_event(TelemetryEvent(
                run_id="run_fail_open", hospital_id="H", batch_id="B", stage=PipelineStage.LANDING, status=TelemetryStatus.STARTED
            ))
            passed = True
        except Exception:
            passed = False
            
        self.assertTrue(passed, "Logger did not fail-open; raised exception instead.")

    def test_database_reopen(self):
        """Test that database can be closed and reopened safely."""
        self.logger.log_event(TelemetryEvent(
            run_id="run_persist", hospital_id="H", batch_id="B", stage=PipelineStage.STORAGE, status=TelemetryStatus.COMPLETED
        ))
        
        # Create a new instance pointing to same file
        new_logger = PipelineTelemetryLogger(db_path=self.db_path)
        new_logger.log_event(TelemetryEvent(
            run_id="run_persist_2", hospital_id="H", batch_id="B", stage=PipelineStage.STORAGE, status=TelemetryStatus.COMPLETED
        ))
        
        with duckdb.connect(self.db_path) as con:
            count = con.execute("SELECT count(*) FROM pipeline_events").fetchone()[0]
            self.assertEqual(count, 2)

if __name__ == "__main__":
    unittest.main()
