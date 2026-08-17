import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

from src.monitoring.models import AnomalyEvent
from src.detection.models import BaseDetector

class DQDetector(BaseDetector):
    """
    Phase 4A Deterministic Data Quality Detector.
    Converts failed rule_results from the Business Rule Engine into canonical AnomalyEvents.
    """
    
    def __init__(self, rule_version: str = "1.0.0"):
        self.rule_version = rule_version
        
    def _create_anomaly_from_result(
        self,
        record: Dict[str, Any],
        hospital_id: str,
        batch_id: str
    ) -> AnomalyEvent:
        """
        Map a single FAILED or NO_AUTHORIZATION rule_result dictionary to an AnomalyEvent.
        """
        # Build evidence JSON
        evidence = {
            "rule_id": record.get("rule_id", "UNKNOWN"),
            "rule_name": record.get("rule_name", "UNKNOWN"),
            "claim_identity": {
                "CLM_ID": record.get("CLM_ID"),
                "CLM_LINE_NUM": record.get("CLM_LINE_NUM")
            },
            "severity": record.get("severity", "UNKNOWN"),
            "message": record.get("message", ""),
            "field_values": record.get("field_values", {})
        }
        
        # Ensure field_values is parsed if it's a string
        if isinstance(evidence["field_values"], str):
            try:
                evidence["field_values"] = json.loads(evidence["field_values"])
            except Exception:
                pass

        # Handle evaluation timestamp
        ts = record.get("evaluation_timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = datetime.now(timezone.utc)
        elif not isinstance(ts, datetime):
            ts = datetime.now(timezone.utc)
            
        # Create AnomalyEvent
        return AnomalyEvent(
            anomaly_id=str(uuid.uuid4()),
            run_id=record.get("run_id", "UNKNOWN"),
            hospital_id=hospital_id,
            batch_id=batch_id,
            stage="validation",  # DQ Engine runs in validation/cleaning stage
            feature_name=record.get("rule_id", "dq_rule"),
            detector="BusinessRuleEngine",
            model_name="DQ_RULE_ENGINE",
            model_version=self.rule_version,
            anomaly_type="DATA_QUALITY_VIOLATION",
            observed_value=1.0,  # Single violation instance
            expected_value=0.0,
            baseline_value=0.0,
            anomaly_score=1.0,  # Deterministic failure
            confidence_score=1.0, # Deterministic confidence
            severity=record.get("severity", "MEDIUM"),
            evidence=evidence,
            detected_at=ts
        )

    def detect(self, rule_results: List[Dict[str, Any]], hospital_id: str = "UNKNOWN", batch_id: str = "UNKNOWN") -> List[AnomalyEvent]:
        """
        Process a batch of rule_results and return AnomalyEvents for any violations.
        A violation is defined as a rule_result where status != 'PASSED'.
        """
        anomalies = []
        for result in rule_results:
            status = result.get("status", "PASSED")
            if status != "PASSED":
                anomaly = self._create_anomaly_from_result(result, hospital_id, batch_id)
                anomalies.append(anomaly)
        return anomalies
