from enum import Enum
from typing import List, Optional, Any, Dict
from dataclasses import dataclass, field
import datetime


class ObservabilityStatus(Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class FindingCategory(Enum):
    PIPELINE_HEALTH = "PIPELINE_HEALTH"
    VOLUME = "VOLUME"
    LATENCY = "LATENCY"
    FRESHNESS = "FRESHNESS"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    COMPLETENESS = "COMPLETENESS"
    DATA_QUALITY = "DATA_QUALITY"


class FindingSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class ObservabilityFinding:
    finding_id: str
    run_id: str
    hospital_id: str
    batch_id: str
    category: FindingCategory
    severity: FindingSeverity
    metric: str
    observed_value: Any
    baseline_value: Any
    deviation_pct: Optional[float]
    threshold_value: Optional[float]
    status: ObservabilityStatus
    message: str
    stage: Optional[str] = None
    detected_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)


@dataclass
class ObservabilityMetric:
    run_id: str
    hospital_id: str
    batch_id: str
    stage: str
    metric_name: str
    observed_value: Any
    baseline_value: Any
    deviation_pct: Optional[float]
    threshold_value: Optional[float]
    measurement_timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)


@dataclass
class ObservabilityResult:
    analysis_id: str
    run_id: str
    hospital_id: str
    batch_id: str
    overall_status: ObservabilityStatus
    records_in: int = 0
    records_out: int = 0
    records_persisted: int = 0
    duration_ms: int = 0
    slowest_stage: Optional[str] = None
    operational_errors: int = 0
    warnings: int = 0
    findings: List[ObservabilityFinding] = field(default_factory=list)
    metrics: List[ObservabilityMetric] = field(default_factory=list)
    analysis_timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    
    @property
    def finding_count(self) -> int:
        return len(self.findings)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.CRITICAL)
        
    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.WARNING)
