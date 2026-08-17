import pandas as pd
import uuid
from typing import List
from src.observability.models import ObservabilityFinding, FindingCategory, FindingSeverity, ObservabilityStatus


def check_data_quality_trend(current_rules: pd.DataFrame, historical_rules: pd.DataFrame, current_claims_count: int, hist_claims_count: int, 
                             run_id: str, hospital_id: str, batch_id: str,
                             warning_multiplier: float = 2.0, critical_multiplier: float = 5.0) -> List[ObservabilityFinding]:
    """
    Identifies unusual changes in business-rule violation rates (not operational failures).
    """
    findings = []
    if current_claims_count == 0 or hist_claims_count == 0:
        return findings
        
    # Only look at FAIL results
    if not current_rules.empty:
        current_fails = len(current_rules[current_rules['status'] == 'FAIL'])
    else:
        current_fails = 0
        
    if not historical_rules.empty:
        hist_fails = len(historical_rules[historical_rules['status'] == 'FAIL'])
    else:
        hist_fails = 0
        
    # Normalize violation rate per 10,000 records (as in requirement example)
    current_rate = (current_fails / current_claims_count) * 10000
    hist_rate = (hist_fails / hist_claims_count) * 10000
    
    if hist_rate <= 0:
        # Prevent division by zero; if we went from 0 to something large, treat as a spike if current_fails > 10
        if current_rate > 50:
             findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.DATA_QUALITY, severity=FindingSeverity.WARNING,
                metric="dq_violation_rate_per_10k", observed_value=current_rate, baseline_value=hist_rate,
                deviation_pct=None, threshold_value=None, status=ObservabilityStatus.WARNING,
                message=f"Data Quality spike: {current_fails} violations detected on {current_claims_count} records (baseline was 0)."
            ))
        return findings
        
    ratio = current_rate / hist_rate
    deviation_pct = (ratio - 1) * 100
    
    if ratio >= critical_multiplier:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.DATA_QUALITY, severity=FindingSeverity.CRITICAL,
            metric="dq_violation_rate_per_10k", observed_value=current_rate, baseline_value=hist_rate,
            deviation_pct=deviation_pct, threshold_value=critical_multiplier * 100, status=ObservabilityStatus.CRITICAL,
            message=f"Critical Data Quality spike: Violation rate is {ratio:.1f}x higher than historical baseline."
        ))
    elif ratio >= warning_multiplier:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.DATA_QUALITY, severity=FindingSeverity.WARNING,
            metric="dq_violation_rate_per_10k", observed_value=current_rate, baseline_value=hist_rate,
            deviation_pct=deviation_pct, threshold_value=warning_multiplier * 100, status=ObservabilityStatus.WARNING,
            message=f"Data Quality spike: Violation rate is {ratio:.1f}x higher than historical baseline."
        ))
        
    return findings
