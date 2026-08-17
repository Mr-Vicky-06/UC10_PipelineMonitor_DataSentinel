import duckdb
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import pandas as pd
from src.observability.models import ObservabilityResult, ObservabilityFinding, ObservabilityMetric

logger = logging.getLogger(__name__)

class ObservabilityRepository:
    def __init__(
        self, 
        telemetry_db_path: str = "outputs/pipeline_workspace/pipeline_telemetry.duckdb",
        processed_db_path: str = "outputs/pipeline_workspace/processed_claims.duckdb",
        observability_db_path: str = "outputs/pipeline_workspace/pipeline_observability.duckdb"
    ):
        self.telemetry_db_path = str(Path(telemetry_db_path).resolve())
        self.processed_db_path = str(Path(processed_db_path).resolve())
        self.observability_db_path = str(Path(observability_db_path).resolve())
        
        # Ensure observability directory exists
        Path(self.observability_db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _initialize_schema(self):
        """Initialize tables in the pipeline_observability.duckdb"""
        try:
            with duckdb.connect(self.observability_db_path) as con:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS observability_runs (
                        analysis_id VARCHAR PRIMARY KEY,
                        run_id VARCHAR,
                        hospital_id VARCHAR,
                        batch_id VARCHAR,
                        analysis_timestamp TIMESTAMP,
                        overall_status VARCHAR,
                        finding_count INTEGER,
                        critical_count INTEGER,
                        warning_count INTEGER,
                        duration_ms BIGINT,
                        records_in BIGINT,
                        records_out BIGINT,
                        records_persisted BIGINT,
                        slowest_stage VARCHAR,
                        operational_errors BIGINT,
                        warnings BIGINT
                    );
                """)
                
                con.execute("""
                    CREATE TABLE IF NOT EXISTS observability_metrics (
                        analysis_id VARCHAR,
                        run_id VARCHAR,
                        hospital_id VARCHAR,
                        batch_id VARCHAR,
                        stage VARCHAR,
                        metric_name VARCHAR,
                        observed_value VARCHAR,
                        baseline_value VARCHAR,
                        deviation_pct DOUBLE,
                        threshold_value DOUBLE,
                        measurement_timestamp TIMESTAMP
                    );
                """)
                
                con.execute("""
                    CREATE TABLE IF NOT EXISTS observability_findings (
                        finding_id VARCHAR PRIMARY KEY,
                        analysis_id VARCHAR,
                        run_id VARCHAR,
                        hospital_id VARCHAR,
                        batch_id VARCHAR,
                        category VARCHAR,
                        severity VARCHAR,
                        metric VARCHAR,
                        observed_value VARCHAR,
                        baseline_value VARCHAR,
                        deviation_pct DOUBLE,
                        threshold_value DOUBLE,
                        status VARCHAR,
                        message VARCHAR,
                        stage VARCHAR,
                        detected_at TIMESTAMP
                    );
                """)
        except Exception as e:
            logger.error(f"Failed to initialize observability schema: {str(e)}")

    def get_telemetry_events(self, run_id: Optional[str] = None) -> pd.DataFrame:
        """Fetch pipeline telemetry events."""
        try:
            with duckdb.connect(self.telemetry_db_path, read_only=True) as con:
                if run_id:
                    return con.execute("SELECT * FROM pipeline_events WHERE run_id = ? ORDER BY timestamp ASC", [run_id]).df()
                return con.execute("SELECT * FROM pipeline_events ORDER BY timestamp ASC").df()
        except Exception as e:
            logger.error(f"Failed to read telemetry events: {e}")
            return pd.DataFrame()
            
    def get_historical_successful_runs(self, limit: int = 30) -> pd.DataFrame:
        """Fetch past successful runs to build baselines."""
        # A run is successful if STORAGE COMPLETED is present
        try:
            with duckdb.connect(self.telemetry_db_path, read_only=True) as con:
                return con.execute(f"""
                    SELECT run_id, MAX(timestamp) as last_ts 
                    FROM pipeline_events 
                    WHERE stage='STORAGE' AND status='COMPLETED' 
                    GROUP BY run_id 
                    ORDER BY last_ts DESC LIMIT {limit}
                """).df()
        except Exception as e:
            logger.error(f"Failed to read historical runs: {e}")
            return pd.DataFrame()

    def get_processed_claims(self, run_id: str) -> pd.DataFrame:
        """Fetch processed claims for a run to do null-rate and schema checking."""
        try:
            with duckdb.connect(self.processed_db_path, read_only=True) as con:
                return con.execute("SELECT * FROM processed_claims WHERE run_id = ?", [run_id]).df()
        except Exception as e:
            logger.error(f"Failed to read processed claims: {e}")
            return pd.DataFrame()
            
    def get_rule_results(self, run_id: Optional[str] = None) -> pd.DataFrame:
        """Fetch rule results for DQ checking."""
        try:
            with duckdb.connect(self.processed_db_path, read_only=True) as con:
                if run_id:
                    return con.execute("SELECT * FROM rule_results WHERE run_id = ?", [run_id]).df()
                return con.execute("SELECT * FROM rule_results").df()
        except Exception as e:
            logger.error(f"Failed to read rule results: {e}")
            return pd.DataFrame()

    def save_observability_result(self, result: ObservabilityResult):
        """Persists the final observability analysis, ensuring idempotency by deleting any previous records for this run_id."""
        try:
            with duckdb.connect(self.observability_db_path) as con:
                # Idempotent cleanup of old analysis for this run_id
                con.execute("DELETE FROM observability_findings WHERE run_id = ?", [result.run_id])
                con.execute("DELETE FROM observability_metrics WHERE run_id = ?", [result.run_id])
                con.execute("DELETE FROM observability_runs WHERE run_id = ?", [result.run_id])
                
                # Insert Run
                con.execute("""
                    INSERT INTO observability_runs 
                    (analysis_id, run_id, hospital_id, batch_id, analysis_timestamp, overall_status, 
                     finding_count, critical_count, warning_count, duration_ms, records_in, 
                     records_out, records_persisted, slowest_stage, operational_errors, warnings)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    result.analysis_id, result.run_id, result.hospital_id, result.batch_id,
                    result.analysis_timestamp, result.overall_status.value, result.finding_count,
                    result.critical_count, result.warning_count, result.duration_ms,
                    result.records_in, result.records_out, result.records_persisted,
                    result.slowest_stage, result.operational_errors, result.warnings
                ])
                
                # Insert Metrics
                if result.metrics:
                    for m in result.metrics:
                        con.execute("""
                            INSERT INTO observability_metrics 
                            (analysis_id, run_id, hospital_id, batch_id, stage, metric_name, 
                             observed_value, baseline_value, deviation_pct, threshold_value, 
                             measurement_timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, [
                            result.analysis_id, m.run_id, m.hospital_id, m.batch_id, m.stage, 
                            m.metric_name, str(m.observed_value), str(m.baseline_value), 
                            m.deviation_pct, m.threshold_value, m.measurement_timestamp
                        ])
                
                # Insert Findings
                if result.findings:
                    for f in result.findings:
                        con.execute("""
                            INSERT INTO observability_findings
                            (finding_id, analysis_id, run_id, hospital_id, batch_id, category, 
                             severity, metric, observed_value, baseline_value, deviation_pct, 
                             threshold_value, status, message, stage, detected_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, [
                            f.finding_id, result.analysis_id, f.run_id, f.hospital_id, f.batch_id,
                            f.category.value, f.severity.value, f.metric, str(f.observed_value),
                            str(f.baseline_value), f.deviation_pct, f.threshold_value, 
                            f.status.value, f.message, f.stage, f.detected_at
                        ])
        except Exception as e:
            logger.error(f"Failed to save observability result: {str(e)}")
