import pandas as pd
from typing import List, Tuple
import uuid
from src.observability.models import ObservabilityFinding, ObservabilityStatus, FindingCategory, FindingSeverity


EXPECTED_STAGES = [
    "LANDING",
    "INGESTION",
    "VALIDATION",
    "CLEANING",
    "TRANSFORMATION",
    "BUSINESS_RULES",
    "STORAGE"
]


def check_pipeline_health(run_events: pd.DataFrame, run_id: str, hospital_id: str, batch_id: str) -> Tuple[ObservabilityStatus, List[ObservabilityFinding]]:
    """
    Reconstructs the pipeline health from telemetry events.
    Detects missing stages, failures, and record reconciliation mismatches.
    """
    findings = []
    overall_status = ObservabilityStatus.HEALTHY
    
    if run_events.empty:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.PIPELINE_HEALTH, severity=FindingSeverity.CRITICAL,
            metric="events_count", observed_value=0, baseline_value=">0", deviation_pct=None, threshold_value=None,
            status=ObservabilityStatus.FAILED, message="No telemetry events found for this run."
        ))
        return ObservabilityStatus.FAILED, findings

    # Stage execution checks
    stage_records_out = {}
    stage_records_in = {}
    previous_stage = None
    
    for stage in EXPECTED_STAGES:
        stage_events = run_events[run_events['stage'] == stage]
        
        if stage_events.empty:
            overall_status = ObservabilityStatus.INCOMPLETE if overall_status != ObservabilityStatus.FAILED else overall_status
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.PIPELINE_HEALTH, severity=FindingSeverity.CRITICAL,
                metric=f"{stage}_missing", observed_value=0, baseline_value=1, deviation_pct=None, threshold_value=None,
                status=ObservabilityStatus.INCOMPLETE, message=f"Stage {stage} is entirely missing from telemetry.", stage=stage
            ))
            continue
            
        started_events = stage_events[stage_events['status'] == 'STARTED']
        terminal_events = stage_events[stage_events['status'].isin(['COMPLETED', 'FAILED'])]
        
        if started_events.empty:
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.PIPELINE_HEALTH, severity=FindingSeverity.WARNING,
                metric=f"{stage}_started_missing", observed_value=0, baseline_value=1, deviation_pct=None, threshold_value=None,
                status=ObservabilityStatus.WARNING, message=f"Orphan terminal event found for {stage} without a STARTED event.", stage=stage
            ))
            
        if terminal_events.empty:
            overall_status = ObservabilityStatus.INCOMPLETE if overall_status != ObservabilityStatus.FAILED else overall_status
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.PIPELINE_HEALTH, severity=FindingSeverity.CRITICAL,
                metric=f"{stage}_terminal_missing", observed_value=0, baseline_value=1, deviation_pct=None, threshold_value=None,
                status=ObservabilityStatus.INCOMPLETE, message=f"Orphan STARTED event for {stage}. Stage never completed.", stage=stage
            ))
            continue
            
        # Check for FAILED
        failed_events = terminal_events[terminal_events['status'] == 'FAILED']
        if not failed_events.empty:
            overall_status = ObservabilityStatus.FAILED
            err_msg = failed_events.iloc[0]['error_message'] if 'error_message' in failed_events.columns else "Unknown error"
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.PIPELINE_HEALTH, severity=FindingSeverity.CRITICAL,
                metric=f"{stage}_failed", observed_value=1, baseline_value=0, deviation_pct=None, threshold_value=None,
                status=ObservabilityStatus.FAILED, message=f"Stage {stage} FAILED. Error: {err_msg}", stage=stage
            ))
            continue
            
        # Record reconciliation
        completed = terminal_events[terminal_events['status'] == 'COMPLETED'].iloc[0]
        r_in = completed['records_in'] if pd.notnull(completed['records_in']) else 0
        r_out = completed['records_out'] if pd.notnull(completed['records_out']) else 0
        
        stage_records_in[stage] = r_in
        stage_records_out[stage] = r_out
        
        if previous_stage and previous_stage in stage_records_out:
            prev_out = stage_records_out[previous_stage]
            # Landing does not feed records_in strictly in the same way, ingestion reads files.
            # Let's enforce strict reconciliation from INGESTION onwards where records_in should equal records_out of previous
            # actually, VALIDATION drops records (records_rejected). 
            # Clean reconciliation: prev_out == current_in
            if stage != "INGESTION" and stage != "LANDING":
                if prev_out != r_in:
                    findings.append(ObservabilityFinding(
                        finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                        category=FindingCategory.PIPELINE_HEALTH, severity=FindingSeverity.WARNING,
                        metric=f"{stage}_reconciliation_mismatch", observed_value=r_in, baseline_value=prev_out, 
                        deviation_pct=None, threshold_value=None,
                        status=ObservabilityStatus.WARNING, message=f"Record mismatch: {previous_stage} output {prev_out} but {stage} received {r_in}.", stage=stage
                    ))
                    
        previous_stage = stage
        
    return overall_status, findings
