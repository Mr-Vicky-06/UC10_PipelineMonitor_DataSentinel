import pandas as pd
import uuid
from typing import List, Optional
from src.observability.models import ObservabilityFinding, ObservabilityMetric, FindingCategory, FindingSeverity, ObservabilityStatus


def check_volume(current_records: int, historical_runs: pd.DataFrame, run_id: str, hospital_id: str, batch_id: str, 
                 warning_threshold_pct: float = 10.0, critical_threshold_pct: float = 20.0) -> List[ObservabilityFinding]:
    """
    Checks if the incoming volume drops significantly below historical baselines.
    We expect 'historical_runs' to have a 'records_persisted' or 'records_in' column depending on what we track. 
    Since we pass current_records, we should compare it to historical records for the same stage or overall.
    """
    findings = []
    if historical_runs.empty or 'records_in' not in historical_runs.columns:
        return findings
        
    # Calculate baseline (median is robust against outliers)
    baseline_volume = historical_runs['records_in'].median()
    if pd.isna(baseline_volume) or baseline_volume == 0:
        return findings
        
    deviation = baseline_volume - current_records
    deviation_pct = (deviation / baseline_volume) * 100
    
    # We only alert on volume drops, not surges, per requirement example (unless surges are also bad, but drops are the primary concern).
    # We'll alert if current is X% below baseline.
    if deviation_pct >= critical_threshold_pct:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.VOLUME, severity=FindingSeverity.CRITICAL,
            metric="records_in_volume_drop", observed_value=current_records, baseline_value=baseline_volume,
            deviation_pct=-deviation_pct, threshold_value=critical_threshold_pct, status=ObservabilityStatus.CRITICAL,
            message=f"Incoming pipeline volume is approximately {deviation_pct:.1f}% below the historical baseline."
        ))
    elif deviation_pct >= warning_threshold_pct:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.VOLUME, severity=FindingSeverity.WARNING,
            metric="records_in_volume_drop", observed_value=current_records, baseline_value=baseline_volume,
            deviation_pct=-deviation_pct, threshold_value=warning_threshold_pct, status=ObservabilityStatus.WARNING,
            message=f"Incoming pipeline volume is approximately {deviation_pct:.1f}% below the historical baseline."
        ))
        
    return findings
