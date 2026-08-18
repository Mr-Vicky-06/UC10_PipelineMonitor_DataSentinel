import json
import os
from typing import List, Dict, Any, Optional
from src.action.models import AlertEvent

class ActionEngine:
    def __init__(self, alerts_path: str = "outputs/action/alerts.jsonl"):
        self.alerts_path = alerts_path
        os.makedirs(os.path.dirname(self.alerts_path), exist_ok=True)
        self.active_dedup_keys = set()
        self._load_existing_alerts()
        
    def _load_existing_alerts(self):
        """Loads existing deduplication keys to prevent alert storms."""
        if not os.path.exists(self.alerts_path):
            return
            
        with open(self.alerts_path, "r") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    # reconstruct the deduplication key
                    key = f"{data.get('run_id')}_{data.get('batch_id')}_{data.get('alert_type')}_{data.get('stage')}"
                    self.active_dedup_keys.add(key)
                except Exception:
                    pass

    def evaluate_and_alert(
        self, 
        incident_id: str,
        run_id: str, 
        batch_id: str,
        stage: str,
        rca_summary: str,
        evidence_ids: List[str],
        sla_status: str,
        anomaly_type: str,
        raw_severity: str = "PENDING_SLA"
    ) -> Optional[AlertEvent]:
        
        # Priority mapping determinism
        # If SLA is BREACHED -> CRITICAL
        # If SLA is AT_RISK -> HIGH
        # If DQ Anomaly and NO SLA data -> HIGH
        # If ML Anomaly -> MEDIUM
        
        severity = "INFO"
        alert_type = anomaly_type
        
        if sla_status == "BREACHED":
            severity = "CRITICAL"
            alert_type = "SLA_BREACH"
        elif sla_status == "AT_RISK":
            severity = "HIGH"
            alert_type = "SLA_RISK"
        elif "DQ" in anomaly_type or anomaly_type == "DATA_QUALITY":
            severity = "HIGH"
        elif "ANOMALY" in anomaly_type or "ML" in anomaly_type:
            severity = "MEDIUM"
        else:
            if raw_severity != "PENDING_SLA":
                severity = raw_severity
                
        alert = AlertEvent(
            incident_id=incident_id,
            run_id=run_id,
            batch_id=batch_id,
            stage=stage,
            alert_type=alert_type,
            severity=severity,
            summary=rca_summary,
            evidence_ids=evidence_ids
        )
        
        dedup_key = alert.get_deduplication_key()
        if dedup_key in self.active_dedup_keys:
            # Duplicate suppressed
            return None
            
        # Emit alert
        self.active_dedup_keys.add(dedup_key)
        self._write_alert(alert)
        return alert
        
    def _write_alert(self, alert: AlertEvent):
        """Append to the structured JSONL store."""
        with open(self.alerts_path, "a") as f:
            # We use __dict__ simply here, or dataclasses.asdict
            import dataclasses
            f.write(json.dumps(dataclasses.asdict(alert)) + "\n")
