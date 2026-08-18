from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime

class AlertDetailResponse(BaseModel):
    rule_id: Optional[str]
    rule_name: Optional[str]
    metric: str
    value: float
    unit: Optional[str]
    message: Optional[str]
    affected_rows: Optional[int]
    total_rows: Optional[int]
    affected_percentage: Optional[float]

    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    alert_id: str
    source: str
    event_type: str
    pipeline: str
    hospital: str
    severity: str
    status: str
    summary: str
    created_at: datetime.datetime
    occurrence_count: int
    
    class Config:
        from_attributes = True

class AlertDetailedResponse(AlertResponse):
    details: List[AlertDetailResponse]
    # Optionally include notifications
    
    class Config:
        from_attributes = True

class AlertSummary(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    open: int
    acknowledged: int
    resolved: int
