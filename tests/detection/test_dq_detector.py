import pytest
from datetime import datetime
from src.detection.dq_detector import DQDetector
from src.monitoring.models import AnomalyEvent

def test_dq_detector_creation():
    detector = DQDetector(rule_version="1.0.0")
    
    rule_results = [
        {
            "run_id": "run-1",
            "CLM_ID": "CLM-001",
            "CLM_LINE_NUM": "1",
            "rule_id": "DQ-COMP-001",
            "rule_name": "mandatory_beneficiary_id",
            "status": "FAIL",
            "severity": "ERROR",
            "message": "Missing BENE_ID",
            "field_values": {"BENE_ID": None},
            "evaluation_timestamp": datetime.utcnow().isoformat()
        },
        {
            "run_id": "run-1",
            "CLM_ID": "CLM-002",
            "CLM_LINE_NUM": "1",
            "rule_id": "DQ-COMP-002",
            "rule_name": "mandatory_claim_id",
            "status": "PASSED",
            "severity": "ERROR",
            "message": "",
            "field_values": {"CLM_ID": "CLM-002"},
            "evaluation_timestamp": datetime.utcnow().isoformat()
        }
    ]
    
    anomalies = detector.detect(rule_results, hospital_id="hosp-1", batch_id="batch-1")
    
    # Should only create anomaly for the FAIL record
    assert len(anomalies) == 1
    anomaly = anomalies[0]
    
    assert isinstance(anomaly, AnomalyEvent)
    assert anomaly.anomaly_type == "DATA_QUALITY_VIOLATION"
    assert anomaly.detector == "BusinessRuleEngine"
    assert anomaly.model_name == "DQ_RULE_ENGINE"
    assert anomaly.feature_name == "DQ-COMP-001"
    assert anomaly.observed_value == 1.0
    assert anomaly.evidence["rule_id"] == "DQ-COMP-001"
    assert anomaly.evidence["claim_identity"]["CLM_ID"] == "CLM-001"
    assert anomaly.evidence["claim_identity"]["CLM_LINE_NUM"] == "1"
    assert anomaly.evidence["severity"] == "ERROR"
    assert anomaly.evidence["field_values"] == {"BENE_ID": None}
    assert anomaly.hospital_id == "hosp-1"
    assert anomaly.batch_id == "batch-1"
