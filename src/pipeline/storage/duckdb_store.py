import duckdb
import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import time
import uuid

from src.pipeline.telemetry import PipelineTelemetryLogger, TelemetryEvent, PipelineStage, TelemetryStatus

from src.business_rules.models import BusinessRuleResult, BusinessRuleViolation

logger = logging.getLogger(__name__)

class ProcessedClaimsStore:
    """
    DuckDB-backed persistent store for processed claims and business rule violations.
    Serves as the pipeline boundary after Business Rules evaluation.
    """

    def __init__(self, db_path: str = "outputs/pipeline_workspace/processed_claims.duckdb"):
        self.db_path = str(Path(db_path).resolve())
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()
        self.telemetry = PipelineTelemetryLogger.get_instance()

    def _get_connection(self):
        return duckdb.connect(self.db_path)

    def initialize_schema(self):
        """Creates the required tables and indexes if they do not exist."""
        with self._get_connection() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS processed_claims (
                    run_id VARCHAR,
                    CLM_ID VARCHAR,
                    CLM_LINE_NUM VARCHAR,
                    hospital_id VARCHAR,
                    batch_id VARCHAR,
                    source_file VARCHAR,
                    processed_timestamp TIMESTAMP,
                    -- Core identifiers
                    BENE_ID VARCHAR,
                    PRVDR_NUM VARCHAR,
                    HCPCS_CD VARCHAR,
                    CLM_FROM_DT VARCHAR,
                    -- Dynamic transformed JSON to preserve any schema evolution
                    transformed_data JSON
                );
            """)
            
            con.execute("""
                CREATE TABLE IF NOT EXISTS rule_results (
                    run_id VARCHAR,
                    CLM_ID VARCHAR,
                    CLM_LINE_NUM VARCHAR,
                    rule_id VARCHAR,
                    rule_name VARCHAR,
                    status VARCHAR,
                    severity VARCHAR,
                    message VARCHAR,
                    field_values JSON,
                    evaluation_timestamp TIMESTAMP
                );
            """)

            # Indexes for idempotency and query performance
            con.execute("CREATE INDEX IF NOT EXISTS idx_processed_claims_pk ON processed_claims(run_id, CLM_ID, CLM_LINE_NUM);")
            con.execute("CREATE INDEX IF NOT EXISTS idx_rule_results_pk ON rule_results(run_id, CLM_ID, CLM_LINE_NUM, rule_id);")

    def save(self, 
             df_transformed: pd.DataFrame, 
             rule_result: BusinessRuleResult, 
             run_id: str, 
             hospital_id: str, 
             batch_id: str,
             source_file: str = "") -> None:
        """
        Persists transformed claims and rule results.
        Uses a delete-then-insert strategy to guarantee idempotency.
        """
        if df_transformed.empty:
            logger.warning("Empty dataframe provided to ProcessedClaimsStore. Nothing to save.")
            return

        correlation_id = str(uuid.uuid4())
        start_t = time.time()
        
        start_event = TelemetryEvent(
            correlation_id=correlation_id, run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            stage=PipelineStage.STORAGE, status=TelemetryStatus.STARTED, source_file=source_file
        )
        self.telemetry.log_event(start_event)

        processed_timestamp = datetime.now().isoformat()

        # 1. Prepare processed_claims data
        # Extract core fields explicitly, and serialize the rest to JSON
        df_claims = df_transformed.copy()
        
        # Ensure we have the core fields, if missing fill with empty string (though validation should prevent this)
        core_fields = ['CLM_ID', 'CLM_LINE_NUM', 'BENE_ID', 'PRVDR_NUM', 'HCPCS_CD', 'CLM_FROM_DT']
        for col in core_fields:
            if col not in df_claims.columns:
                df_claims[col] = ""

        # To avoid schema fragility, we'll store the entire row as a JSON blob in transformed_data
        # This keeps the schema robust while keeping core fields indexable
        records = df_claims.to_dict(orient='records')
        
        claims_rows = []
        for r in records:
            claims_rows.append({
                'run_id': run_id,
                'CLM_ID': str(r.get('CLM_ID', '')),
                'CLM_LINE_NUM': str(r.get('CLM_LINE_NUM', '')),
                'hospital_id': hospital_id,
                'batch_id': batch_id,
                'source_file': source_file,
                'processed_timestamp': processed_timestamp,
                'BENE_ID': str(r.get('BENE_ID', '')),
                'PRVDR_NUM': str(r.get('PRVDR_NUM', '')),
                'HCPCS_CD': str(r.get('HCPCS_CD', '')),
                'CLM_FROM_DT': str(r.get('CLM_FROM_DT', '')),
                'transformed_data': json.dumps(r)
            })
            
        df_claims_stg = pd.DataFrame(claims_rows)

        # 2. Prepare rule_results data
        rule_rows = []
        for violation in rule_result.violations:
            rule_rows.append({
                'run_id': run_id,
                'CLM_ID': str(violation.clm_id),
                'CLM_LINE_NUM': str(violation.clm_line_num),
                'rule_id': str(violation.rule_id),
                'rule_name': str(violation.rule_name),
                'status': str(violation.status),
                'severity': str(violation.severity),
                'message': str(violation.message),
                'field_values': json.dumps(violation.field_values),
                'evaluation_timestamp': rule_result.execution_timestamp
            })
            
        df_rules_stg = pd.DataFrame(rule_rows)
        # Handle case where there are no violations
        if df_rules_stg.empty:
            df_rules_stg = pd.DataFrame(columns=[
                'run_id', 'CLM_ID', 'CLM_LINE_NUM', 'rule_id', 'rule_name', 
                'status', 'severity', 'message', 'field_values', 'evaluation_timestamp'
            ])

        # Execute Transaction
        with self._get_connection() as con:
            try:
                con.execute("BEGIN TRANSACTION")
                
                # Delete existing records for this (run_id, CLM_ID, CLM_LINE_NUM) to support idempotent retries
                # This ensures we don't duplicate on partial retries or duplicate inputs
                
                # We need unique CLM_ID + CLM_LINE_NUM pairs from the incoming batch
                # to delete from the DB where run_id matches.
                unique_claims = df_claims_stg[['CLM_ID', 'CLM_LINE_NUM']].drop_duplicates()
                
                con.execute("""
                    DELETE FROM processed_claims
                    USING unique_claims u
                    WHERE processed_claims.run_id = ?
                    AND processed_claims.CLM_ID = u.CLM_ID
                    AND processed_claims.CLM_LINE_NUM = u.CLM_LINE_NUM
                """, [run_id])
    
                con.execute("""
                    DELETE FROM rule_results
                    USING unique_claims u
                    WHERE rule_results.run_id = ?
                    AND rule_results.CLM_ID = u.CLM_ID
                    AND rule_results.CLM_LINE_NUM = u.CLM_LINE_NUM
                """, [run_id])
                
                # Insert the new ones
                con.execute("INSERT INTO processed_claims SELECT * FROM df_claims_stg")
                
                if not df_rules_stg.empty:
                    # In rare cases a single claim might trigger the SAME rule twice 
                    # We deduplicate df_rules_stg just in case to avoid breaking the unique index
                    df_rules_stg = df_rules_stg.drop_duplicates(subset=['run_id', 'CLM_ID', 'CLM_LINE_NUM', 'rule_id'], keep='last')
                    con.execute("INSERT INTO rule_results SELECT * FROM df_rules_stg")
                
                con.execute("COMMIT")
                
                end_event = TelemetryEvent(
                    correlation_id=correlation_id, run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                    stage=PipelineStage.STORAGE, status=TelemetryStatus.COMPLETED, source_file=source_file,
                    duration_ms=int((time.time() - start_t) * 1000), records_in=len(df_transformed), records_out=len(df_transformed),
                    errors=0
                )
                self.telemetry.log_event(end_event)
                
            except Exception as e:
                con.execute("ROLLBACK")
                logger.error(f"Failed to persist batch {batch_id} for run {run_id}: {str(e)}")
                
                err_event = TelemetryEvent(
                    correlation_id=correlation_id, run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                    stage=PipelineStage.STORAGE, status=TelemetryStatus.FAILED, source_file=source_file,
                    duration_ms=int((time.time() - start_t) * 1000), error_type=type(e).__name__, error_message=str(e)
                )
                self.telemetry.log_event(err_event)
                raise
