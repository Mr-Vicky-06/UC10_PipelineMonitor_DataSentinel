from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime, date
import uuid

class PipelineStage(str, Enum):
    LANDING = "LANDING"
    INGESTION = "INGESTION"
    VALIDATION = "VALIDATION"
    CLEANING = "CLEANING"
    TRANSFORMATION = "TRANSFORMATION"
    BUSINESS_RULES = "BUSINESS_RULES"
    STORAGE = "STORAGE"

class TelemetryStatus(str, Enum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class TelemetryEvent:
    run_id: str
    hospital_id: str
    batch_id: str
    stage: PipelineStage
    status: TelemetryStatus
    
    source_file: str = ""
    service_date: Optional[str] = None
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    duration_ms: int = 0
    records_in: int = 0
    records_out: int = 0
    errors: int = 0
    warnings: int = 0
    
    message: str = ""
    error_type: str = ""
    error_message: str = ""
