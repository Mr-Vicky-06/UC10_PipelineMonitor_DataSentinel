import pandas as pd
import uuid
from typing import List, Dict
from src.observability.models import ObservabilityFinding, ObservabilityMetric, FindingCategory, FindingSeverity, ObservabilityStatus


KEY_FIELDS = ['CLM_ID', 'CLM_LINE_NUM', 'BENE_ID', 'PRVDR_NUM', 'HCPCS_CD', 'CLM_FROM_DT', 'CLM_PMT_AMT']


def check_completeness(current_claims: pd.DataFrame, historical_claims: pd.DataFrame, run_id: str, hospital_id: str, batch_id: str,
                       warning_threshold: float = 10.0, critical_threshold: float = 20.0) -> List[ObservabilityFinding]:
    """
    Calculates null rates for key fields and compares against the historical baseline.
    """
    findings = []
    if current_claims.empty or historical_claims.empty:
        return findings
        
    current_total = len(current_claims)
    hist_total = len(historical_claims)
    
    for field in KEY_FIELDS:
        if field not in current_claims.columns or field not in historical_claims.columns:
            continue
            
        # Current null rate
        current_nulls = current_claims[field].isna().sum()
        current_rate = (current_nulls / current_total) * 100
        
        # Historical null rate
        hist_nulls = historical_claims[field].isna().sum()
        hist_rate = (hist_nulls / hist_total) * 100
        
        # Deviation (absolute percentage points or relative? Usually absolute points or relative. Let's do relative % deviation for spikes, 
        # or absolute diff. Let's do absolute percentage points: current 25% vs historical 1% -> +24% absolute deviation)
        deviation_pct = current_rate - hist_rate
        
        if deviation_pct >= critical_threshold:
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.COMPLETENESS, severity=FindingSeverity.CRITICAL,
                metric=f"{field}_null_rate", observed_value=current_rate, baseline_value=hist_rate,
                deviation_pct=deviation_pct, threshold_value=critical_threshold, status=ObservabilityStatus.CRITICAL,
                message=f"Completeness spike for {field}: null rate is {current_rate:.1f}% (historical {hist_rate:.1f}%)."
            ))
        elif deviation_pct >= warning_threshold:
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.COMPLETENESS, severity=FindingSeverity.WARNING,
                metric=f"{field}_null_rate", observed_value=current_rate, baseline_value=hist_rate,
                deviation_pct=deviation_pct, threshold_value=warning_threshold, status=ObservabilityStatus.WARNING,
                message=f"Completeness drop for {field}: null rate is {current_rate:.1f}% (historical {hist_rate:.1f}%)."
            ))
            
    return findings
