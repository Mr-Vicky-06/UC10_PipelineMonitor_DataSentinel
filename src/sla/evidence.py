from dataclasses import dataclass
from typing import Optional

@dataclass
class SLAObservation:
    """Canonical structure for SLA evidence."""
    sla_id: str
    run_id: str
    stage: str
    status: str  # ON_TRACK, AT_RISK, BREACHED, UNKNOWN
    
    expected_records: Optional[int] = None
    processed_records: Optional[int] = None
    remaining_records: Optional[int] = None
    throughput: Optional[float] = None  # records per second
    
    elapsed_seconds: Optional[float] = None
    estimated_remaining_seconds: Optional[float] = None
    estimated_completion_time: Optional[float] = None
    sla_deadline: Optional[float] = None
    sla_margin_seconds: Optional[float] = None
    
    batch_id: Optional[str] = None
    hospital_id: Optional[str] = None
    timestamp: Optional[float] = None
    source_reference: str = "sla_engine"
    
    def is_breached(self) -> bool:
        return self.status == "BREACHED"
        
    def is_at_risk(self) -> bool:
        return self.status == "AT_RISK"
        
    def is_unknown(self) -> bool:
        return self.status == "UNKNOWN"
