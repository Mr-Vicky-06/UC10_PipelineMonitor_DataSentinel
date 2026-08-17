import pandas as pd
import uuid
from typing import List
from src.observability.models import ObservabilityFinding, FindingCategory, FindingSeverity, ObservabilityStatus


def check_latency(current_events: pd.DataFrame, historical_events: pd.DataFrame, run_id: str, hospital_id: str, batch_id: str, 
                  warning_multiplier: float = 1.5, critical_multiplier: float = 2.0) -> List[ObservabilityFinding]:
    """
    Checks if any stage took significantly longer than its historical baseline.
    historical_events should contain events from previous successful runs.
    """
    findings = []
    if current_events.empty or historical_events.empty:
        return findings
        
    current_durations = current_events[current_events['status'] == 'COMPLETED'].set_index('stage')['duration_ms']
    historical_completed = historical_events[historical_events['status'] == 'COMPLETED']
    
    for stage, current_duration in current_durations.items():
        stage_hist = historical_completed[historical_completed['stage'] == stage]
        if stage_hist.empty:
            continue
            
        baseline_duration = stage_hist['duration_ms'].median()
        if pd.isna(baseline_duration) or baseline_duration <= 0:
            continue
            
        # If current duration is a spike (e.g. baseline is 200ms, warning mult is 1.5 -> 300ms)
        # Let's add a small flat buffer to avoid triggering on very fast stages that fluctuate (e.g. 5ms -> 15ms is 3x but irrelevant)
        # We'll only alert if the absolute difference is also > 1000ms (1 second)
        if current_duration < 1000:
            continue
            
        ratio = current_duration / baseline_duration
        deviation_pct = (ratio - 1) * 100
        
        if ratio >= critical_multiplier:
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.LATENCY, severity=FindingSeverity.CRITICAL,
                metric=f"{stage}_duration_ms", observed_value=current_duration, baseline_value=baseline_duration,
                deviation_pct=deviation_pct, threshold_value=critical_multiplier * 100, status=ObservabilityStatus.CRITICAL,
                message=f"Stage {stage} execution is significantly slower ({ratio:.1f}x) than historical baseline.", stage=stage
            ))
        elif ratio >= warning_multiplier:
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.LATENCY, severity=FindingSeverity.WARNING,
                metric=f"{stage}_duration_ms", observed_value=current_duration, baseline_value=baseline_duration,
                deviation_pct=deviation_pct, threshold_value=warning_multiplier * 100, status=ObservabilityStatus.WARNING,
                message=f"Stage {stage} execution is slower ({ratio:.1f}x) than historical baseline.", stage=stage
            ))
            
    return findings
