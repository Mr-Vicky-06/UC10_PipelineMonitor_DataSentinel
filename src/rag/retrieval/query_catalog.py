from typing import Dict, Any, List
import logging
from rag.retrieval.duckdb_client import ReadOnlyDuckDBClient
from rag.evidence.adapters import adapt_pipeline_event, adapt_rule_result, adapt_anomaly_event
from rag.models.evidence import Evidence

logger = logging.getLogger(__name__)

class QueryCatalog:
    """
    Bounded catalog of parameterized SQL queries to prevent unrestricted Text-to-SQL.
    Executes intent-driven requests and returns canonical Evidence objects.
    """
    def __init__(self, db_client: ReadOnlyDuckDBClient):
        self.db = db_client

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
        
        # Sort all evidence chronologically
        evidence.sort(key=lambda x: x.timestamp)
        return evidence
