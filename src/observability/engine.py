import pandas as pd
import uuid
import datetime
from typing import Optional, Dict
import json
import logging

from src.observability.models import ObservabilityResult, ObservabilityStatus, FindingSeverity, ObservabilityMetric
from src.observability.repository import ObservabilityRepository

from src.observability.checks.pipeline_health import check_pipeline_health
from src.observability.checks.volume import check_volume
from src.observability.checks.latency import check_latency
from src.observability.checks.freshness import check_freshness
from src.observability.checks.schema_drift import check_schema_drift
from src.observability.checks.completeness import check_completeness
from src.observability.checks.data_quality import check_data_quality_trend

logger = logging.getLogger(__name__)


class ObservabilityEngine:
    def __init__(self, repo: Optional[ObservabilityRepository] = None):
        self.repo = repo or ObservabilityRepository()

    def analyze_run(self, run_id: str) -> ObservabilityResult:
        """
        Analyzes a single pipeline run against historical baselines.
        """
        analysis_id = str(uuid.uuid4())
        result = ObservabilityResult(analysis_id=analysis_id, run_id=run_id, hospital_id="UNKNOWN", batch_id="UNKNOWN", overall_status=ObservabilityStatus.UNKNOWN)
        
        try:
            # Fetch telemetry
            current_events = self.repo.get_telemetry_events(run_id=run_id)
            if current_events.empty:
                result.overall_status = ObservabilityStatus.FAILED
                return result
                
            # Extract identities
            first_event = current_events.iloc[0]
            result.hospital_id = first_event['hospital_id']
            result.batch_id = first_event['batch_id']
            current_timestamp = current_events['timestamp'].max()
            
            # Baseline data
            historical_runs = self.repo.get_historical_successful_runs(limit=30)
            # Get full historical events for those runs
            hist_run_ids = historical_runs['run_id'].tolist() if not historical_runs.empty else []
            if hist_run_ids:
                # Exclude current run from baseline if it was successfully persisted already
                hist_run_ids = [r for r in hist_run_ids if r != run_id]
                hist_events_query = ",".join([f"'{r}'" for r in hist_run_ids])
                # This is a bit manual, but we'll fetch all telemetry and filter. In a real system, use SQL.
                all_telemetry = self.repo.get_telemetry_events()
                hist_events = all_telemetry[all_telemetry['run_id'].isin(hist_run_ids)]
            else:
                hist_events = pd.DataFrame()

            # 1. Pipeline Health
            health_status, health_findings = check_pipeline_health(current_events, run_id, result.hospital_id, result.batch_id)
            result.findings.extend(health_findings)
            result.overall_status = health_status
            
            # Update metrics from current_events (total duration, errors, etc)
            completed_stages = current_events[current_events['status'] == 'COMPLETED']
            result.duration_ms = int(completed_stages['duration_ms'].sum()) if not completed_stages.empty else 0
            
            if not completed_stages.empty:
                result.slowest_stage = completed_stages.loc[completed_stages['duration_ms'].idxmax()]['stage']
                # records_in for ingestion
                ingest_completed = completed_stages[completed_stages['stage'] == 'INGESTION']
                if not ingest_completed.empty:
                    result.records_in = int(ingest_completed.iloc[0]['records_in']) if pd.notnull(ingest_completed.iloc[0]['records_in']) else 0
                else:
                    first_completed = completed_stages.iloc[0]
                    result.records_in = int(first_completed['records_in']) if pd.notnull(first_completed['records_in']) else 0
                # records_out for storage
                storage_completed = completed_stages[completed_stages['stage'] == 'STORAGE']
                if not storage_completed.empty:
                    result.records_out = int(storage_completed.iloc[0]['records_out'])
                    result.records_persisted = result.records_out
            
            failed_stages = current_events[current_events['status'] == 'FAILED']
            result.operational_errors = len(failed_stages)

            # 2. Volume
            if not hist_events.empty:
                # get records_in from INGESTION COMPLETED across historical runs
                hist_ingest = hist_events[(hist_events['stage'] == 'INGESTION') & (hist_events['status'] == 'COMPLETED')]
                volume_findings = check_volume(result.records_in, hist_ingest, run_id, result.hospital_id, result.batch_id)
                result.findings.extend(volume_findings)
                
            # 3. Latency
            if not hist_events.empty:
                latency_findings = check_latency(current_events, hist_events, run_id, result.hospital_id, result.batch_id)
                result.findings.extend(latency_findings)
                
            # 4. Freshness
            if not historical_runs.empty:
                last_success = historical_runs.iloc[0]['last_ts']
                freshness_findings = check_freshness(current_timestamp, last_success, run_id, result.hospital_id, result.batch_id)
                result.findings.extend(freshness_findings)

            # Datasets for Schema, Completeness, DQ
            current_claims = self.repo.get_processed_claims(run_id)
            current_rules = self.repo.get_rule_results(run_id)
            
            if hist_run_ids:
                hist_claims = self.repo.get_processed_claims(hist_run_ids[0])  # Using just the most recent success for schema/nulls
                hist_rules = self.repo.get_rule_results(hist_run_ids[0])
            else:
                hist_claims = pd.DataFrame()
                hist_rules = pd.DataFrame()

            # 5. Schema Drift
            if not current_claims.empty and not hist_claims.empty:
                # Basic schema deduction from dataframe
                current_schema = {col: str(current_claims[col].dtype) for col in current_claims.columns}
                hist_schema = {col: str(hist_claims[col].dtype) for col in hist_claims.columns}
                schema_findings = check_schema_drift(current_schema, hist_schema, run_id, result.hospital_id, result.batch_id)
                result.findings.extend(schema_findings)
                
            # 6. Completeness
            if not current_claims.empty and not hist_claims.empty:
                completeness_findings = check_completeness(current_claims, hist_claims, run_id, result.hospital_id, result.batch_id)
                result.findings.extend(completeness_findings)
                
            # 7. Data Quality
            if not current_claims.empty and not hist_claims.empty:
                dq_findings = check_data_quality_trend(
                    current_rules, hist_rules, len(current_claims), len(hist_claims), 
                    run_id, result.hospital_id, result.batch_id
                )
                result.findings.extend(dq_findings)

            # Adjust overall status based on highest severity finding (if not already failed/incomplete)
            if result.overall_status == ObservabilityStatus.HEALTHY:
                if any(f.severity == FindingSeverity.CRITICAL for f in result.findings):
                    # But DQ issues shouldn't make the pipeline status "FAILED" or "CRITICAL" strictly from an operational standpoint.
                    # Wait, the requirements state: "Pipeline Health = HEALTHY, Data Quality Signal = WARNING/CRITICAL". 
                    # So pipeline health (overall_status) should NOT change due to DQ/Completeness/Volume anomalies.
                    # It only changes if the pipeline itself failed (INCOMPLETE, FAILED). 
                    # The "overall_status" should reflect pipeline_health.
                    pass # Keep as HEALTHY if no operational failure.

            # Persist
            self.repo.save_observability_result(result)
            
        except Exception as e:
            logger.error(f"Observability analysis failed for run {run_id}: {e}", exc_info=True)
            result.overall_status = ObservabilityStatus.FAILED
            
        return result
