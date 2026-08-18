import time
import uuid
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class AlertEvent:
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str = ""
    run_id: str = ""
    batch_id: str = ""
    stage: str = ""
    alert_type: str = "" # e.g. SLA_BREACH, DQ_VIOLATION, ML_ANOMALY
    severity: str = "INFO" # CRITICAL, HIGH, MEDIUM, LOW, INFO
    status: str = "OPEN"
    summary: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    
    def get_deduplication_key(self) -> str:
        """Deterministic key to prevent alert storms."""
        return f"{self.run_id}_{self.batch_id}_{self.alert_type}_{self.stage}"
