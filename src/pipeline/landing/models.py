from enum import Enum
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

class LandingStatus(str, Enum):
    LANDED = "LANDED"
    ALREADY_LANDED = "ALREADY_LANDED"
    CONFLICT = "CONFLICT"
    FAILED = "FAILED"

@dataclass
class LandedBatch:
    run_id: str
    hospital_id: str
    source_path: str
    landing_path: str
    filename: str
    service_date: date
    size_bytes: int
    source_sha256: str
    landing_sha256: Optional[str]
    landed_at: datetime
    status: LandingStatus
