import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional

from rag.models.evidence import Evidence

def safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def adapt_pipeline_event(row: Dict[str, Any]) -> Evidence:
    """
    Converts a pipeline_events row into a Canonical Evidence object.
    """
    event_id = str(row.get('event_id') or uuid.uuid4())
    
    # Identify the key metric to report for this event
    # If duration is available, we might report duration. If it's an error, report error_count.
    status = row.get('status', 'UNKNOWN')
    
    if status == 'FAILED' or row.get('error_type'):
        identifier = row.get('error_type', 'PIPELINE_FAILURE')
        observed = row.get('error_message', row.get('message', 'Failed'))
        ev_type = 'pipeline_failure'
        severity = 'CRITICAL'
    else:
        identifier = 'stage_duration'
        observed = row.get('duration_ms')
        ev_type = 'operational_metric'
        severity = 'INFO'
        
    # Construct a reference for provenance
    source_ref = {
        'event_id': event_id,
        'correlation_id': row.get('correlation_id'),
        'table': 'pipeline_events',
        'database': 'pipeline_telemetry.duckdb'
    }
        
    return Evidence(
        evidence_id=f"EV-PL-{event_id[:8]}",
        run_id=str(row.get('run_id', 'UNKNOWN')),
        hospital_id=str(row.get('hospital_id', 'UNKNOWN')),
        batch_id=str(row.get('batch_id', 'UNKNOWN')),
        stage=str(row.get('stage', 'UNKNOWN')),
        timestamp=row.get('timestamp') or datetime.now(),
        source='pipeline_events',
        evidence_type=ev_type,
        identifier=identifier,
        observed_value=observed,
        baseline_value=None,
        deviation=None,
        severity=severity,
        source_reference=source_ref
    )

def adapt_rule_result(row: Dict[str, Any]) -> Evidence:
    """
    Converts a rule_results row into a Canonical Evidence object.
    """
    # Rule results might not have an explicit ID, generate a deterministic one based on claim+rule
    clm_id = str(row.get('CLM_ID', 'UNKNOWN'))
    rule_id = str(row.get('rule_id', 'UNKNOWN'))
    
    source_ref = {
        'CLM_ID': clm_id,
        'CLM_LINE_NUM': row.get('CLM_LINE_NUM'),
        'rule_name': row.get('rule_name'),
        'table': 'rule_results',
        'database': 'processed_claims.duckdb'
    }
    
    severity = str(row.get('severity', 'WARNING')).upper()
    
    return Evidence(
        evidence_id=f"EV-DQ-{uuid.uuid4().hex[:8]}",
        run_id=str(row.get('run_id', 'UNKNOWN')),
        hospital_id="UNKNOWN", # Often not directly in the rule result row unless joined
        batch_id="UNKNOWN",
        stage="BUSINESS_RULES",
        timestamp=row.get('evaluation_timestamp') or datetime.now(),
        source='rule_results',
        evidence_type='rule_violation',
        identifier=rule_id,
        observed_value=row.get('message', 'Rule Failed'),
        baseline_value=None, # DQ rules usually don't have a baseline metric, they are pass/fail
        deviation=None,
        severity=severity,
        source_reference=source_ref
    )

def adapt_anomaly_event(row: Dict[str, Any]) -> Evidence:
    """
    Converts an anomaly_events row into a Canonical Evidence object.
    """
    anomaly_id = str(row.get('anomaly_id') or uuid.uuid4())
    
    source_ref = {
        'anomaly_id': anomaly_id,
        'model_name': row.get('model_name'),
        'detector': row.get('detector'),
        'evidence_json': row.get('evidence'),
        'table': 'anomaly_events',
        'database': 'metrics_repository.duckdb'
    }
    
    observed = safe_float(row.get('observed_value'))
    baseline = safe_float(row.get('baseline_value'))
    expected = safe_float(row.get('expected_value'))
    if baseline is None and expected is not None:
        baseline = expected
        
    # Calculate % deviation if possible
    deviation = None
    if observed is not None and baseline is not None and baseline != 0:
        deviation = ((observed - baseline) / baseline) * 100.0
        
    severity = str(row.get('severity', 'HIGH')).upper()
    
    return Evidence(
        evidence_id=f"EV-ML-{anomaly_id[:8]}",
        run_id=str(row.get('run_id', 'UNKNOWN')),
        hospital_id=str(row.get('hospital_id', 'UNKNOWN')),
        batch_id=str(row.get('batch_id', 'UNKNOWN')),
        stage=str(row.get('stage', 'UNKNOWN')),
        timestamp=row.get('detected_at') or datetime.now(),
        source='anomaly_events',
        evidence_type='statistical_anomaly',
        identifier=str(row.get('feature_name', row.get('anomaly_type', 'UNKNOWN'))),
        observed_value=observed,
        baseline_value=baseline,
        deviation=deviation,
        severity=severity,
        source_reference=source_ref
    )

