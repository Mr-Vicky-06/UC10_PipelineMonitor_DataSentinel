import pandas as pd
import uuid
from typing import List, Dict, Tuple
from src.observability.models import ObservabilityFinding, FindingCategory, FindingSeverity, ObservabilityStatus


def check_schema_drift(current_schema: Dict[str, str], historical_schema: Dict[str, str], run_id: str, hospital_id: str, batch_id: str) -> List[ObservabilityFinding]:
    """
    Checks if the current schema (columns and types) differs from the historical baseline schema.
    Expected schemas are dicts mapping column_name -> data_type.
    """
    findings = []
    if not historical_schema:
        return findings
        
    current_cols = set(current_schema.keys())
    historical_cols = set(historical_schema.keys())
    
    added_cols = current_cols - historical_cols
    removed_cols = historical_cols - current_cols
    
    if added_cols:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.SCHEMA_DRIFT, severity=FindingSeverity.WARNING,
            metric="schema_added_columns", observed_value=list(added_cols), baseline_value=[],
            deviation_pct=None, threshold_value=None, status=ObservabilityStatus.WARNING,
            message=f"Schema drift detected: New columns added {list(added_cols)}."
        ))
        
    if removed_cols:
        findings.append(ObservabilityFinding(
            finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            category=FindingCategory.SCHEMA_DRIFT, severity=FindingSeverity.WARNING,
            metric="schema_removed_columns", observed_value=list(removed_cols), baseline_value=[],
            deviation_pct=None, threshold_value=None, status=ObservabilityStatus.WARNING,
            message=f"Schema drift detected: Columns removed {list(removed_cols)}."
        ))
        
    # Check type changes for common columns
    common_cols = current_cols.intersection(historical_cols)
    for col in common_cols:
        if current_schema[col] != historical_schema[col]:
            findings.append(ObservabilityFinding(
                finding_id=str(uuid.uuid4()), run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                category=FindingCategory.SCHEMA_DRIFT, severity=FindingSeverity.WARNING,
                metric=f"schema_type_change_{col}", observed_value=current_schema[col], baseline_value=historical_schema[col],
                deviation_pct=None, threshold_value=None, status=ObservabilityStatus.WARNING,
                message=f"Schema drift detected: Column {col} changed type from {historical_schema[col]} to {current_schema[col]}."
            ))
            
    return findings
