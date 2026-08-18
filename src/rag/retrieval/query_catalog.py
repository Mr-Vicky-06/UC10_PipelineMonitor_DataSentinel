from typing import Dict, Any, List
import logging
from src.rag.retrieval.duckdb_client import ReadOnlyDuckDBClient
from src.rag.evidence.adapters import adapt_pipeline_event, adapt_rule_result, adapt_anomaly_event, adapt_sla_observation
from src.rag.models.evidence import Evidence
from src.sla.config import SLAConfigManager
from src.sla.calculator import SLACalculator

logger = logging.getLogger(__name__)

class QueryCatalog:
    """
    Bounded catalog of parameterized SQL queries to prevent unrestricted Text-to-SQL.
    Executes intent-driven requests and returns canonical Evidence objects.
    """
    def __init__(self, db_client: ReadOnlyDuckDBClient):
        self.db = db_client
        self.sla_manager = SLAConfigManager()

    def execute_intent(self, intent: str, params: Dict[str, Any]) -> List[Evidence]:
        """
        Routes the intent to the corresponding parameterized query function.
        """
        methods = {
            "RUN_SUMMARY": self._get_run_summary,
            "BATCH_SUMMARY": self._get_batch_summary,
            "STAGE_PERFORMANCE": self._get_stage_performance,
            "RULE_VIOLATIONS": self._get_rule_violations,
            "ANOMALY_SUMMARY": self._get_anomaly_summary,
            "RCA_ANALYSIS": self._get_rca_analysis
        }
        
        handler = methods.get(intent.upper())
        if not handler:
            logger.warning(f"Unsupported query intent: {intent}")
            return []
            
        try:
            return handler(params)
        except Exception as e:
            logger.error(f"Error executing intent {intent}: {str(e)}")
            return []

    def _get_run_summary(self, params: Dict[str, Any]) -> List[Evidence]:
        run_id = params.get("run_id")
        if not run_id:
            return []
            
        query = """
        SELECT * FROM pipeline_events
        WHERE run_id = ?
        ORDER BY timestamp ASC
        """
        rows = self.db.query_telemetry(query, (run_id,))
        return [adapt_pipeline_event(row) for row in rows]

    def _get_batch_summary(self, params: Dict[str, Any]) -> List[Evidence]:
        batch_id = params.get("batch_id")
        if not batch_id:
            return []
            
        query = """
        SELECT * FROM pipeline_events
        WHERE batch_id = ?
        ORDER BY timestamp ASC
        """
        rows = self.db.query_telemetry(query, (batch_id,))
        return [adapt_pipeline_event(row) for row in rows]
        
    def _get_stage_performance(self, params: Dict[str, Any]) -> List[Evidence]:
        run_id = params.get("run_id")
        stage = params.get("stage")
        if not run_id or not stage:
            return []
            
        query = """
        SELECT * FROM pipeline_events
        WHERE run_id = ? AND stage = ?
        ORDER BY timestamp ASC
        """
        rows = self.db.query_telemetry(query, (run_id, stage))
        return [adapt_pipeline_event(row) for row in rows]

    def _get_rule_violations(self, params: Dict[str, Any]) -> List[Evidence]:
        run_id = params.get("run_id")
        if not run_id:
            return []
            
        query = """
        SELECT * FROM rule_results
        WHERE run_id = ? AND status != 'PASS'
        ORDER BY evaluation_timestamp ASC
        """
        rows = self.db.query_claims(query, (run_id,))
        return [adapt_rule_result(row) for row in rows]

    def _get_anomaly_summary(self, params: Dict[str, Any]) -> List[Evidence]:
        run_id = params.get("run_id")
        if not run_id:
            return []
            
        query = """
        SELECT * FROM anomaly_events
        WHERE run_id = ?
        ORDER BY detected_at ASC
        """
        rows = self.db.query_metrics(query, (run_id,))
        return [adapt_anomaly_event(row) for row in rows]

    def _get_rca_analysis(self, params: Dict[str, Any]) -> List[Evidence]:
        """
        Comprehensive retrieval for RCA: fetches telemetry, rule violations, and ML anomalies
        for a specific run_id.
        """
        run_id = params.get("run_id")
        if not run_id:
            return []
            
        evidence = []
        evidence.extend(self._get_run_summary({"run_id": run_id}))
        evidence.extend(self._get_rule_violations({"run_id": run_id}))
        evidence.extend(self._get_anomaly_summary({"run_id": run_id}))
        
        # --- Compute SLA Evidence Dynamically ---
        # 1. Identify stages from the run summary
        stages_seen = set([e.stage for e in evidence if e.source == 'pipeline_events'])
        for stage in stages_seen:
            # check if SLA is configured
            config = self.sla_manager.get_sla(pipeline_name="uc10_pipeline", stage=stage)
            if not config:
                continue
                
            # Extract events for this stage to find start/end and records
            stage_events = [e for e in evidence if e.source == 'pipeline_events' and e.stage == stage]
            if not stage_events:
                continue
                
            # Find start time
            start_event = next((e for e in stage_events if e.identifier == 'STAGE_START'), None)
            if not start_event:
                continue
                
            start_time = start_event.timestamp.timestamp()
            
            # Find current state/metrics
            current_time = start_time
            expected_records = None
            processed_records = 0
            stage_status = "RUNNING"
            
            for e in sorted(stage_events, key=lambda x: x.timestamp):
                current_time = e.timestamp.timestamp()
                if e.identifier == 'STAGE_END' or e.identifier == 'COMPLETED':
                    stage_status = "COMPLETED"
                if e.identifier == 'STAGE_FAILED' or e.identifier == 'pipeline_failure':
                    stage_status = "FAILED"
                    
                if e.source_reference:
                    metrics = e.source_reference.get('metrics', {})
                    if 'records_in' in metrics:
                        expected_records = metrics['records_in']
                    if 'records_out' in metrics:
                        processed_records = metrics['records_out']
            
            obs = SLACalculator.calculate(
                config=config,
                run_id=run_id,
                start_time=start_time,
                current_time=current_time,
                expected_records=expected_records,
                processed_records=processed_records,
                stage_status=stage_status,
                batch_id=stage_events[0].batch_id,
                hospital_id=stage_events[0].hospital_id
            )
            
            evidence.append(adapt_sla_observation(obs))
        
        # Sort all evidence chronologically
        evidence.sort(key=lambda x: x.timestamp)
        return evidence
