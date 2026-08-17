"""
DataSentinal Monitoring System — Metric Data Models
===================================================
Defines the standard structured data record for historical pipeline and
monitoring metrics.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
import uuid
import json


class MetricsRepositoryError(Exception):
    """Custom exception raised for invalid metric operations or storage failures."""
    pass


@dataclass
class MetricRecord:
    """
    Structured historical metric record.
    
    Attributes:
        metric_name: Name of the metric (e.g. 'records_processed', 'null_count')
        metric_value: Numeric value of the metric
        stage_name: Name of the pipeline/monitoring stage (e.g. 'transformation', 'cleaning')
        metric_id: Unique UUID identifier for the metric record
        timestamp: Timezone-aware UTC timestamp when the metric was generated/recorded
        run_id: Execution run identifier
        batch_id: Source batch identifier
        hospital_id: Hospital/provider identifier
        metric_unit: Measurement unit (e.g. 'count', 'seconds', 'ratio', 'bytes')
        status: Status of the execution associated with the metric ('SUCCESS', 'FAILED', 'WARNING')
        source: Source component that produced the metric ('pipeline', 'dq_engine', 'observability')
        dimensions: Flexible dictionary of additional tags/dimensions
    """
    metric_name: str
    metric_value: float
    stage_name: str
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str = "DEFAULT_RUN"
    batch_id: str = "DEFAULT_BATCH"
    hospital_id: str = "DEFAULT_HOSPITAL"
    metric_unit: str = "count"
    status: str = "SUCCESS"
    source: str = "pipeline"
    dimensions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert MetricRecord to dictionary format."""
        d = asdict(self)
        if isinstance(d["timestamp"], datetime):
            d["timestamp"] = d["timestamp"].isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricRecord":
        """Reconstruct MetricRecord from dictionary format."""
        data_copy = data.copy()
        ts_val = data_copy.get("timestamp")
        if isinstance(ts_val, str):
            data_copy["timestamp"] = datetime.fromisoformat(ts_val)
        elif ts_val is None:
            data_copy["timestamp"] = datetime.now(timezone.utc)
            
        dims = data_copy.get("dimensions")
        if isinstance(dims, str):
            try:
                data_copy["dimensions"] = json.loads(dims)
            except Exception:
                data_copy["dimensions"] = {}
        elif dims is None:
            data_copy["dimensions"] = {}
            
        return cls(**data_copy)


@dataclass
class AnomalyEvent:
    """
    Canonical record representing a detected anomaly across any detection domain.
    """
    run_id: str
    hospital_id: str
    batch_id: str
    stage: str
    feature_name: str
    detector: str
    model_name: str
    model_version: str
    anomaly_type: str
    observed_value: float
    expected_value: float
    baseline_value: float
    anomaly_score: float
    confidence_score: float
    severity: str
    evidence: Dict[str, Any]
    anomaly_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert AnomalyEvent to dictionary format."""
        d = asdict(self)
        if isinstance(d["detected_at"], datetime):
            d["detected_at"] = d["detected_at"].isoformat()
        if isinstance(d["evidence"], dict):
            d["evidence"] = json.dumps(d["evidence"])
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnomalyEvent":
        """Reconstruct AnomalyEvent from dictionary format."""
        data_copy = data.copy()
        ts_val = data_copy.get("detected_at")
        if isinstance(ts_val, str):
            data_copy["detected_at"] = datetime.fromisoformat(ts_val)
        elif ts_val is None:
            data_copy["detected_at"] = datetime.now(timezone.utc)
            
        ev = data_copy.get("evidence")
        if isinstance(ev, str):
            try:
                data_copy["evidence"] = json.loads(ev)
            except Exception:
                data_copy["evidence"] = {}
        elif ev is None:
            data_copy["evidence"] = {}
            
        return cls(**data_copy)
