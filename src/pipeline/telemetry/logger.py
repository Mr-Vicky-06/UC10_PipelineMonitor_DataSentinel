import duckdb
import logging
from pathlib import Path
from dataclasses import asdict
from typing import Optional

from src.pipeline.telemetry.models import TelemetryEvent, PipelineStage, TelemetryStatus

logger = logging.getLogger(__name__)

class PipelineTelemetryLogger:
    """
    Centralized operational telemetry logger for the DataSentinal pipeline.
    Writes telemetry events to an isolated DuckDB store.
    Designed with a strict fail-open policy: telemetry failures must NEVER stop the pipeline.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, db_path: str = "outputs/pipeline_workspace/pipeline_telemetry.duckdb"):
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    def __init__(self, db_path: str = "outputs/pipeline_workspace/pipeline_telemetry.duckdb"):
        self.db_path = str(Path(db_path).resolve())
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _get_connection(self):
        return duckdb.connect(self.db_path)

    def _initialize_schema(self):
        """Creates the required tables if they do not exist, catching any initialization errors."""
        try:
            with self._get_connection() as con:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_events (
                        event_id VARCHAR,
                        correlation_id VARCHAR,
                        timestamp TIMESTAMP,
                        run_id VARCHAR,
                        hospital_id VARCHAR,
                        batch_id VARCHAR,
                        source_file VARCHAR,
                        service_date VARCHAR,
                        stage VARCHAR,
                        status VARCHAR,
                        duration_ms BIGINT,
                        records_in BIGINT,
                        records_out BIGINT,
                        errors BIGINT,
                        warnings BIGINT,
                        message VARCHAR,
                        error_type VARCHAR,
                        error_message VARCHAR
                    );
                """)
                # Create indexes for correlation and lookups
                con.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_run ON pipeline_events(run_id, hospital_id, batch_id);")
                con.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_correlation ON pipeline_events(correlation_id);")
        except Exception as e:
            # FAIL-OPEN: Log the failure but do not crash the application
            logger.error(f"Failed to initialize telemetry schema: {str(e)}")

    def log_event(self, event: TelemetryEvent) -> None:
        """
        Persists a telemetry event. 
        Fail-open: If the database is locked or corrupted, logs to stdout and continues.
        """
        try:
            event_dict = asdict(event)
            # Ensure enum types and optional dates are converted to string for DuckDB
            event_dict['stage'] = event.stage.value if isinstance(event.stage, PipelineStage) else event.stage
            event_dict['status'] = event.status.value if isinstance(event.status, TelemetryStatus) else event.status
            event_dict['service_date'] = str(event.service_date) if event.service_date else ""
            
            with self._get_connection() as con:
                # Using prepared statement to insert
                con.execute("""
                    INSERT INTO pipeline_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    event_dict['event_id'],
                    event_dict['correlation_id'],
                    event_dict['timestamp'],
                    event_dict['run_id'],
                    event_dict['hospital_id'],
                    event_dict['batch_id'],
                    event_dict['source_file'],
                    event_dict['service_date'],
                    event_dict['stage'],
                    event_dict['status'],
                    event_dict['duration_ms'],
                    event_dict['records_in'],
                    event_dict['records_out'],
                    event_dict['errors'],
                    event_dict['warnings'],
                    event_dict['message'],
                    event_dict['error_type'],
                    event_dict['error_message']
                ])
        except Exception as e:
            # FAIL-OPEN constraint: catch exception, emit standard log, do not raise
            logger.error(f"TELEMETRY FAILURE: Failed to log event {event.event_id} ({event.stage} {event.status}): {str(e)}")
            # Fallback output
            logger.warning(f"TELEMETRY FALLBACK: {event_dict}")
