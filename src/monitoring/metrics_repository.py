"""
DataSentinal Monitoring System — Metrics Repository
===================================================
Provides persistent structured historical metric storage and querying capabilities
for the DataSentinal pipeline monitoring layer.
"""

import os
import json
import logging
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import duckdb

from src.monitoring.models import MetricRecord, MetricsRepositoryError, AnomalyEvent

logger = logging.getLogger(__name__)


class MetricsRepository:
    """
    Persistent Metrics Repository for DataSentinal.
    Stores and queries pipeline, data quality, observability, and transformation metrics.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.environ.get("METRICS_DB_PATH", os.environ.get("DATABASE_URL"))
        if db_path is None:
            db_path = "outputs/pipeline_workspace/metrics_repository.duckdb"

        self.db_path = db_path
        self.is_memory = db_path in (":memory:", "memory")

        if not self.is_memory:
            p = Path(self.db_path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(p)

        self._conn = duckdb.connect(self.db_path)
        self.initialize_schema()
        self.initialize_anomaly_schema()

    def _get_connection(self):
        """Obtain the active database connection."""
        return self._conn

    def close(self):
        """Close database connection."""
        if hasattr(self, "_conn") and self._conn:
            try:
                self._conn.close()
            except Exception:
                pass

    def initialize_schema(self) -> None:
        """Initialize the metrics database table and indexes if they do not exist."""
        try:
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    metric_id VARCHAR PRIMARY KEY,
                    timestamp TIMESTAMP,
                    run_id VARCHAR,
                    batch_id VARCHAR,
                    hospital_id VARCHAR,
                    stage_name VARCHAR,
                    metric_name VARCHAR,
                    metric_value DOUBLE,
                    metric_unit VARCHAR,
                    status VARCHAR,
                    source VARCHAR,
                    dimensions VARCHAR
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_run_batch ON metrics(run_id, batch_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_lookup ON metrics(hospital_id, stage_name, metric_name);")
        except Exception as e:
            logger.error(f"Failed to initialize MetricsRepository schema: {str(e)}")
            raise MetricsRepositoryError(f"Schema initialization failed: {str(e)}") from e

    def initialize_anomaly_schema(self) -> None:
        """Initialize the anomaly events database table and indexes if they do not exist."""
        try:
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS anomaly_events (
                    anomaly_id VARCHAR PRIMARY KEY,
                    run_id VARCHAR,
                    hospital_id VARCHAR,
                    batch_id VARCHAR,
                    stage VARCHAR,
                    feature_name VARCHAR,
                    detector VARCHAR,
                    model_name VARCHAR,
                    model_version VARCHAR,
                    anomaly_type VARCHAR,
                    observed_value DOUBLE,
                    expected_value DOUBLE,
                    baseline_value DOUBLE,
                    anomaly_score DOUBLE,
                    confidence_score DOUBLE,
                    severity VARCHAR,
                    detected_at TIMESTAMP,
                    evidence VARCHAR
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_events_timestamp ON anomaly_events(detected_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_events_run_batch ON anomaly_events(run_id, batch_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_events_lookup ON anomaly_events(hospital_id, stage, feature_name);")
        except Exception as e:
            logger.error(f"Failed to initialize anomaly_events schema: {str(e)}")
            raise MetricsRepositoryError(f"Anomaly Schema initialization failed: {str(e)}") from e

    def _validate_metric(self, metric: MetricRecord) -> None:
        """Validate required fields of a MetricRecord prior to insertion."""
        if not metric.metric_name or not isinstance(metric.metric_name, str):
            raise MetricsRepositoryError("Metric record must contain a non-empty string 'metric_name'.")
        if metric.metric_value is None or not isinstance(metric.metric_value, (int, float)):
            raise MetricsRepositoryError("Metric record must contain a valid numeric 'metric_value'.")
        if not metric.stage_name or not isinstance(metric.stage_name, str):
            raise MetricsRepositoryError("Metric record must contain a non-empty string 'stage_name'.")
        if not metric.metric_id:
            raise MetricsRepositoryError("Metric record must contain a non-empty 'metric_id'.")
        if not isinstance(metric.timestamp, datetime):
            raise MetricsRepositoryError("Metric record 'timestamp' must be a valid datetime instance.")

    def save_metric(self, metric: MetricRecord) -> str:
        """
        Persist a single MetricRecord to the repository.
        Returns the inserted metric_id.
        """
        self._validate_metric(metric)
        dims_json = json.dumps(metric.dimensions or {})
        ts = metric.timestamp

        try:
            conn = self._get_connection()
            # Check for duplicate metric_id
            existing = conn.execute("SELECT COUNT(*) FROM metrics WHERE metric_id = ?", [metric.metric_id]).fetchone()
            if existing and existing[0] > 0:
                raise MetricsRepositoryError(f"Duplicate metric insertion blocked for metric_id='{metric.metric_id}'.")

            conn.execute("""
                INSERT INTO metrics (
                    metric_id, timestamp, run_id, batch_id, hospital_id,
                    stage_name, metric_name, metric_value, metric_unit,
                    status, source, dimensions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                metric.metric_id,
                ts,
                metric.run_id,
                metric.batch_id,
                metric.hospital_id,
                metric.stage_name,
                metric.metric_name,
                float(metric.metric_value),
                metric.metric_unit,
                metric.status,
                metric.source,
                dims_json
            ])
            return metric.metric_id
        except MetricsRepositoryError:
            raise
        except Exception as e:
            logger.error(f"Error saving metric '{metric.metric_name}': {str(e)}")
            raise MetricsRepositoryError(f"Failed to save metric: {str(e)}") from e

    def save_metrics(self, metrics: List[MetricRecord]) -> int:
        """
        Persist multiple MetricRecord items in a single transaction.
        Returns the count of successfully saved records.
        """
        if not metrics:
            return 0

        for m in metrics:
            self._validate_metric(m)

        rows = []
        for m in metrics:
            dims_json = json.dumps(m.dimensions or {})
            rows.append((
                m.metric_id,
                m.timestamp,
                m.run_id,
                m.batch_id,
                m.hospital_id,
                m.stage_name,
                m.metric_name,
                float(m.metric_value),
                m.metric_unit,
                m.status,
                m.source,
                dims_json
            ))

        try:
            conn = self._get_connection()
            conn.execute("BEGIN TRANSACTION")
            for r in rows:
                conn.execute("""
                    INSERT INTO metrics (
                        metric_id, timestamp, run_id, batch_id, hospital_id,
                        stage_name, metric_name, metric_value, metric_unit,
                        status, source, dimensions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, r)
            conn.execute("COMMIT")
            return len(rows)
        except Exception as e:
            try:
                self._get_connection().execute("ROLLBACK")
            except Exception:
                pass
            logger.error(f"Failed bulk insertion of {len(metrics)} metrics: {str(e)}")
            raise MetricsRepositoryError(f"Bulk metric save failed: {str(e)}") from e

    def save_anomaly(self, anomaly: AnomalyEvent) -> str:
        """
        Persist a single AnomalyEvent to the repository.
        Returns the inserted anomaly_id.
        """
        evidence_json = json.dumps(anomaly.evidence or {})
        ts = anomaly.detected_at

        try:
            conn = self._get_connection()
            existing = conn.execute("SELECT COUNT(*) FROM anomaly_events WHERE anomaly_id = ?", [anomaly.anomaly_id]).fetchone()
            if existing and existing[0] > 0:
                raise MetricsRepositoryError(f"Duplicate anomaly insertion blocked for anomaly_id='{anomaly.anomaly_id}'.")

            conn.execute("""
                INSERT INTO anomaly_events (
                    anomaly_id, run_id, hospital_id, batch_id, stage,
                    feature_name, detector, model_name, model_version,
                    anomaly_type, observed_value, expected_value, baseline_value,
                    anomaly_score, confidence_score, severity, detected_at, evidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                anomaly.anomaly_id,
                anomaly.run_id,
                anomaly.hospital_id,
                anomaly.batch_id,
                anomaly.stage,
                anomaly.feature_name,
                anomaly.detector,
                anomaly.model_name,
                anomaly.model_version,
                anomaly.anomaly_type,
                float(anomaly.observed_value),
                float(anomaly.expected_value),
                float(anomaly.baseline_value),
                float(anomaly.anomaly_score),
                float(anomaly.confidence_score),
                anomaly.severity,
                ts,
                evidence_json
            ])
            return anomaly.anomaly_id
        except MetricsRepositoryError:
            raise
        except Exception as e:
            logger.error(f"Error saving anomaly '{anomaly.anomaly_id}': {str(e)}")
            raise MetricsRepositoryError(f"Failed to save anomaly: {str(e)}") from e

    def save_anomalies(self, anomalies: List[AnomalyEvent]) -> int:
        """
        Persist multiple AnomalyEvent items in a single transaction.
        Returns the count of successfully saved records.
        """
        if not anomalies:
            return 0

        rows = []
        for a in anomalies:
            evidence_json = json.dumps(a.evidence or {})
            rows.append((
                a.anomaly_id,
                a.run_id,
                a.hospital_id,
                a.batch_id,
                a.stage,
                a.feature_name,
                a.detector,
                a.model_name,
                a.model_version,
                a.anomaly_type,
                float(a.observed_value),
                float(a.expected_value),
                float(a.baseline_value),
                float(a.anomaly_score),
                float(a.confidence_score),
                a.severity,
                a.detected_at,
                evidence_json
            ))

        try:
            conn = self._get_connection()
            conn.execute("BEGIN TRANSACTION")
            for r in rows:
                conn.execute("""
                    INSERT INTO anomaly_events (
                        anomaly_id, run_id, hospital_id, batch_id, stage,
                        feature_name, detector, model_name, model_version,
                        anomaly_type, observed_value, expected_value, baseline_value,
                        anomaly_score, confidence_score, severity, detected_at, evidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, r)
            conn.execute("COMMIT")
            return len(rows)
        except Exception as e:
            try:
                self._get_connection().execute("ROLLBACK")
            except Exception:
                pass
            logger.error(f"Failed bulk insertion of {len(anomalies)} anomalies: {str(e)}")
            raise MetricsRepositoryError(f"Bulk anomaly save failed: {str(e)}") from e

    def _row_to_record(self, row: tuple) -> MetricRecord:
        """Convert database tuple row to MetricRecord."""
        metric_id, ts, run_id, batch_id, hospital_id, stage_name, metric_name, value, unit, status, source, dims_str = row
        
        dims = {}
        if dims_str:
            try:
                dims = json.loads(dims_str)
            except Exception:
                dims = {}

        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        return MetricRecord(
            metric_id=metric_id,
            timestamp=ts,
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            stage_name=stage_name,
            metric_name=metric_name,
            metric_value=float(value),
            metric_unit=unit,
            status=status,
            source=source,
            dimensions=dims
        )

    def get_latest_metric(
        self, metric_name: str, hospital_id: Optional[str] = None, stage_name: Optional[str] = None
    ) -> Optional[MetricRecord]:
        """Query the most recent metric matching metric_name (and optional filters)."""
        query = "SELECT metric_id, timestamp, run_id, batch_id, hospital_id, stage_name, metric_name, metric_value, metric_unit, status, source, dimensions FROM metrics WHERE metric_name = ?"
        params = [metric_name]

        if hospital_id:
            query += " AND hospital_id = ?"
            params.append(hospital_id)
        if stage_name:
            query += " AND stage_name = ?"
            params.append(stage_name)

        query += " ORDER BY timestamp DESC LIMIT 1"

        try:
            conn = self._get_connection()
            res = conn.execute(query, params).fetchone()
            return self._row_to_record(res) if res else None
        except Exception as e:
            logger.error(f"Error executing get_latest_metric: {str(e)}")
            raise MetricsRepositoryError(f"Query get_latest_metric failed: {str(e)}") from e

    def get_metrics_for_run(self, run_id: str) -> List[MetricRecord]:
        """Retrieve all metrics recorded for a specific pipeline run."""
        if not isinstance(run_id, str):
            raise MetricsRepositoryError("run_id must be a string.")
        query = "SELECT metric_id, timestamp, run_id, batch_id, hospital_id, stage_name, metric_name, metric_value, metric_unit, status, source, dimensions FROM metrics WHERE run_id = ? ORDER BY timestamp ASC"
        try:
            conn = self._get_connection()
            rows = conn.execute(query, [run_id]).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying metrics for run_id='{run_id}': {str(e)}")
            raise MetricsRepositoryError(f"Query get_metrics_for_run failed: {str(e)}") from e

    def get_metrics_for_batch(self, batch_id: str) -> List[MetricRecord]:
        """Retrieve all metrics recorded for a specific batch."""
        if not isinstance(batch_id, str):
            raise MetricsRepositoryError("batch_id must be a string.")
        query = "SELECT metric_id, timestamp, run_id, batch_id, hospital_id, stage_name, metric_name, metric_value, metric_unit, status, source, dimensions FROM metrics WHERE batch_id = ? ORDER BY timestamp ASC"
        try:
            conn = self._get_connection()
            rows = conn.execute(query, [batch_id]).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying metrics for batch_id='{batch_id}': {str(e)}")
            raise MetricsRepositoryError(f"Query get_metrics_for_batch failed: {str(e)}") from e

    def get_metrics_for_stage(self, stage_name: str) -> List[MetricRecord]:
        """Retrieve all metrics recorded for a specific pipeline stage."""
        if not isinstance(stage_name, str):
            raise MetricsRepositoryError("stage_name must be a string.")
        query = "SELECT metric_id, timestamp, run_id, batch_id, hospital_id, stage_name, metric_name, metric_value, metric_unit, status, source, dimensions FROM metrics WHERE stage_name = ? ORDER BY timestamp ASC"
        try:
            conn = self._get_connection()
            rows = conn.execute(query, [stage_name]).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying metrics for stage_name='{stage_name}': {str(e)}")
            raise MetricsRepositoryError(f"Query get_metrics_for_stage failed: {str(e)}") from e

    def get_metrics_since(
        self,
        start_time: datetime,
        hospital_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        metric_name: Optional[str] = None
    ) -> List[MetricRecord]:
        """Retrieve metrics recorded since a given timestamp."""
        query = "SELECT metric_id, timestamp, run_id, batch_id, hospital_id, stage_name, metric_name, metric_value, metric_unit, status, source, dimensions FROM metrics WHERE timestamp >= ?"
        params: List[Any] = [start_time]

        if hospital_id:
            query += " AND hospital_id = ?"
            params.append(hospital_id)
        if stage_name:
            query += " AND stage_name = ?"
            params.append(stage_name)
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)

        query += " ORDER BY timestamp ASC"

        try:
            conn = self._get_connection()
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying get_metrics_since: {str(e)}")
            raise MetricsRepositoryError(f"Query get_metrics_since failed: {str(e)}") from e

    def get_daily_metrics(
        self,
        target_date: Union[date, datetime, str],
        hospital_id: Optional[str] = None,
        stage_name: Optional[str] = None
    ) -> List[MetricRecord]:
        """Retrieve metrics for a specific calendar day."""
        if isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)
        elif isinstance(target_date, datetime):
            target_date = target_date.date()

        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        return self.get_historical_metrics(start_dt, end_dt, hospital_id=hospital_id, stage_name=stage_name)

    def get_historical_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        hospital_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        metric_name: Optional[str] = None
    ) -> List[MetricRecord]:
        """Retrieve metrics recorded within a specific start and end timestamp window."""
        query = "SELECT metric_id, timestamp, run_id, batch_id, hospital_id, stage_name, metric_name, metric_value, metric_unit, status, source, dimensions FROM metrics WHERE timestamp >= ? AND timestamp <= ?"
        params: List[Any] = [start_time, end_time]

        if hospital_id:
            query += " AND hospital_id = ?"
            params.append(hospital_id)
        if stage_name:
            query += " AND stage_name = ?"
            params.append(stage_name)
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)

        query += " ORDER BY timestamp ASC"

        try:
            conn = self._get_connection()
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying get_historical_metrics: {str(e)}")
            raise MetricsRepositoryError(f"Query get_historical_metrics failed: {str(e)}") from e

    def get_metrics_today(self, hospital_id: Optional[str] = None) -> List[MetricRecord]:
        """Convenience query for today's metrics."""
        today = datetime.now().date()
        return self.get_daily_metrics(today, hospital_id=hospital_id)

    def get_metrics_yesterday(self, hospital_id: Optional[str] = None) -> List[MetricRecord]:
        """Convenience query for yesterday's metrics."""
        yesterday = datetime.now().date() - timedelta(days=1)
        return self.get_daily_metrics(yesterday, hospital_id=hospital_id)

    def get_metrics_last_30_days(self, hospital_id: Optional[str] = None) -> List[MetricRecord]:
        """Convenience query for metrics over the last 30 days."""
        start_time = datetime.now() - timedelta(days=30)
        return self.get_metrics_since(start_time, hospital_id=hospital_id)

    def get_metrics_last_6_months(self, hospital_id: Optional[str] = None) -> List[MetricRecord]:
        """Convenience query for metrics over the last 6 months (180 days)."""
        start_time = datetime.now() - timedelta(days=180)
        return self.get_metrics_since(start_time, hospital_id=hospital_id)

    def health_check(self) -> bool:
        """Verify database connectivity and repository functionality."""
        try:
            conn = self._get_connection()
            res = conn.execute("SELECT 1").fetchone()
            return res is not None and res[0] == 1
        except Exception as e:
            logger.warning(f"MetricsRepository health check failed: {str(e)}")
            return False
