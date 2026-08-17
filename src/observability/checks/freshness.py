import pandas as pd
import uuid
import datetime
from typing import List
from src.observability.models import ObservabilityFinding, FindingCategory, FindingSeverity, ObservabilityStatus


def check_freshness(current_run_timestamp: datetime.datetime, last_success_timestamp: datetime.datetime, run_id: str, hospital_id: str, batch_id: str,
                    expected_interval_minutes: int = 60, warning_multiplier: float = 1.5, critical_multiplier: float = 2.0) -> List[ObservabilityFinding]:
    """
    Calculates if the time since the last successful run exceeds the expected arrival interval.
    Note: This is mostly evaluated when a run ACTUALLY happens, or on a schedule. Since we run this post-pipeline,
    it tells us if THIS run was late relative to the last one.
    """
    findings = []
    if not last_success_timestamp:
        return findings
        
    # Ensure timestamps are pandas datetime for reliable diff
    current = pd.to_datetime(current_run_timestamp)
    last = pd.to_datetime(last_success_timestamp)
    
    time_since_last_minutes = (current - last).total_seconds() / 60.0
    
    # If the interval is greater than expected, we flag freshness issue
    ratio = time_since_last_minutes / expected_interval_minutes
    deviation_pct = (ratio - 1) * 100
    
    if ratio >= critical_multiplier:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.FRESHNESS, severity=FindingSeverity.CRITICAL,
            metric="minutes_late", observed_value=time_since_last_minutes, baseline_value=expected_interval_minutes,
            deviation_pct=deviation_pct, threshold_value=critical_multiplier * 100, status=ObservabilityStatus.CRITICAL,
            message=f"Data arrival is critically late. {time_since_last_minutes:.1f} mins since last success (expected {expected_interval_minutes} mins)."
        ))
    elif ratio >= warning_multiplier:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.FRESHNESS, severity=FindingSeverity.WARNING,
            metric="minutes_late", observed_value=time_since_last_minutes, baseline_value=expected_interval_minutes,
            deviation_pct=deviation_pct, threshold_value=warning_multiplier * 100, status=ObservabilityStatus.WARNING,
            message=f"Data arrival is late. {time_since_last_minutes:.1f} mins since last success (expected {expected_interval_minutes} mins)."
        ))
        
    return findings
