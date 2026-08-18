from datetime import datetime
import json
from src.rag.models.evidence import Evidence
from src.sla.evidence import SLAObservation

def adapt_sla_observation(obs: SLAObservation) -> Evidence:
    """Adapts an SLAObservation to the canonical Evidence format."""
    
    # Map SLA status to Evidence severity
    severity_map = {
        "BREACHED": "CRITICAL",
        "AT_RISK": "WARNING",
        "ON_TRACK": "INFO",
        "UNKNOWN": "INFO"
    }
    
    # Store dynamic calculation fields in source_reference
    source_ref = {
        "expected_records": obs.expected_records,
        "processed_records": obs.processed_records,
        "remaining_records": obs.remaining_records,
        "throughput": obs.throughput,
        "elapsed_seconds": obs.elapsed_seconds,
        "estimated_remaining_seconds": obs.estimated_remaining_seconds,
        "estimated_completion_time": obs.estimated_completion_time,
        "sla_deadline": obs.sla_deadline,
        "sla_margin_seconds": obs.sla_margin_seconds
    }
    
    return Evidence(
        evidence_id=f"sla_{obs.run_id}_{obs.stage}",
        run_id=obs.run_id,
        hospital_id=obs.hospital_id or "UNKNOWN",
        batch_id=obs.batch_id or "UNKNOWN",
        stage=obs.stage,
        timestamp=datetime.fromtimestamp(obs.timestamp) if obs.timestamp else datetime.utcnow(),
        source="sla_engine",
        evidence_type="sla_status",
        identifier=obs.sla_id,
        observed_value=obs.status,
        severity=severity_map.get(obs.status, "INFO"),
        source_reference=source_ref
    )
