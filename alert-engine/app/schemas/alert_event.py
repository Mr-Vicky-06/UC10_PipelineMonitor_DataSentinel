from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union
import datetime
from app.models.alert import Severity

class EventDetails(BaseModel):
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    field: Optional[str] = None
    affected_rows: Optional[int] = None
    total_rows: Optional[int] = None
    affected_percentage: Optional[float] = None
    
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    deviation: Optional[float] = None
    
    deadline: Optional[str] = None
    estimated_completion: Optional[str] = None
    pipeline_status: Optional[str] = None
    
    job_name: Optional[str] = None
    stage: Optional[str] = None

class AlertEvent(BaseModel):
    source: str = Field(..., description="Source module: DQ, ANOMALY, SLA, PROCESSING")
    pipeline: str
    hospital: str
    event_type: str = Field(..., description="Type of event: DATA_QUALITY, ANOMALY, SLA, PROCESSING")
    metric: str
    value: Union[float, str]
    unit: Optional[str] = None
    summary: str
    details: EventDetails
    timestamp: datetime.datetime
