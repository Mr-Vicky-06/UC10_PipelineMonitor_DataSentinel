import os
import json
import pytest
from src.action.engine import ActionEngine

@pytest.fixture
def temp_alerts_path(tmp_path):
    return str(tmp_path / "alerts.jsonl")

def test_alert_creation_and_priority(temp_alerts_path):
    engine = ActionEngine(alerts_path=temp_alerts_path)
    
    alert1 = engine.evaluate_and_alert(
        incident_id="INC-123",
        run_id="run_1",
        batch_id="batch_1",
        stage="INGESTION",
        rca_summary="Test breach",
        evidence_ids=["ev_1"],
        sla_status="BREACHED",
        anomaly_type="SLA_BREACH"
    )
    
    assert alert1 is not None
    assert alert1.severity == "CRITICAL"
    assert alert1.alert_type == "SLA_BREACH"
    
def test_alert_deduplication(temp_alerts_path):
    engine = ActionEngine(alerts_path=temp_alerts_path)
    
    alert1 = engine.evaluate_and_alert(
        incident_id="INC-123",
        run_id="run_1",
        batch_id="batch_1",
        stage="INGESTION",
        rca_summary="Test anomaly",
        evidence_ids=["ev_1"],
        sla_status="ON_TRACK",
        anomaly_type="DATA_QUALITY"
    )
    assert alert1 is not None
    
    alert2 = engine.evaluate_and_alert(
        incident_id="INC-124",
        run_id="run_1",
        batch_id="batch_1",
        stage="INGESTION",
        rca_summary="Test anomaly again",
        evidence_ids=["ev_2"],
        sla_status="ON_TRACK",
        anomaly_type="DATA_QUALITY"
    )
    assert alert2 is None  # Should be deduplicated

def test_alert_loading_deduplication(temp_alerts_path):
    # Write a fake alert manually
    with open(temp_alerts_path, "w") as f:
        f.write(json.dumps({
            "run_id": "run_99",
            "batch_id": "batch_99",
            "alert_type": "MULTIVARIATE_ANOMALY",
            "stage": "TRANSFORMATION"
        }) + "\n")
        
    engine = ActionEngine(alerts_path=temp_alerts_path)
    
    alert = engine.evaluate_and_alert(
        incident_id="INC-99",
        run_id="run_99",
        batch_id="batch_99",
        stage="TRANSFORMATION",
        rca_summary="Existing anomaly",
        evidence_ids=["ev_x"],
        sla_status="UNKNOWN",
        anomaly_type="MULTIVARIATE_ANOMALY"
    )
    assert alert is None # Suppressed due to loaded deduplication key
