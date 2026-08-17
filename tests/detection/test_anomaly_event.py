import pytest
import os
import duckdb
from datetime import datetime, timezone
from typing import Dict, Any

from src.monitoring.models import AnomalyEvent, MetricsRepositoryError
from src.monitoring.metrics_repository import MetricsRepository

@pytest.fixture
def repo():
    # Use memory database for tests
    repo = MetricsRepository(db_path=":memory:")
    yield repo
    repo.close()

def test_anomaly_event_creation():
    event = AnomalyEvent(
        run_id="run-1",
        hospital_id="hosp-1",
        batch_id="batch-1",
        stage="validation",
        feature_name="null_rate",
        detector="BusinessRuleEngine",
        model_name="DQ_RULE_ENGINE",
        model_version="1.0.0",
        anomaly_type="DATA_QUALITY_VIOLATION",
        observed_value=1.0,
        expected_value=0.0,
        baseline_value=0.0,
        anomaly_score=1.0,
        confidence_score=1.0,
        severity="ERROR",
        evidence={"rule_id": "DQ-001", "message": "Missing BENE_ID"}
    )
    assert event.run_id == "run-1"
    assert event.evidence["rule_id"] == "DQ-001"
    assert event.anomaly_id is not None
    assert isinstance(event.detected_at, datetime)

def test_anomaly_event_dict_serialization():
    event = AnomalyEvent(
        run_id="run-1",
        hospital_id="hosp-1",
        batch_id="batch-1",
        stage="validation",
        feature_name="null_rate",
        detector="BusinessRuleEngine",
        model_name="DQ_RULE_ENGINE",
        model_version="1.0.0",
        anomaly_type="DATA_QUALITY_VIOLATION",
        observed_value=1.0,
        expected_value=0.0,
        baseline_value=0.0,
        anomaly_score=1.0,
        confidence_score=1.0,
        severity="ERROR",
        evidence={"rule_id": "DQ-001"}
    )
    d = event.to_dict()
    assert d["run_id"] == "run-1"
    assert isinstance(d["detected_at"], str)
    assert isinstance(d["evidence"], str) # Should be JSON string

    reconstructed = AnomalyEvent.from_dict(d)
    assert reconstructed.run_id == event.run_id
    assert reconstructed.evidence["rule_id"] == "DQ-001"
    assert reconstructed.detected_at == event.detected_at

def test_duckdb_persistence(repo):
    event = AnomalyEvent(
        run_id="run-1",
        hospital_id="hosp-1",
        batch_id="batch-1",
        stage="validation",
        feature_name="null_rate",
        detector="BusinessRuleEngine",
        model_name="DQ_RULE_ENGINE",
        model_version="1.0.0",
        anomaly_type="DATA_QUALITY_VIOLATION",
        observed_value=1.0,
        expected_value=0.0,
        baseline_value=0.0,
        anomaly_score=1.0,
        confidence_score=1.0,
        severity="ERROR",
        evidence={"rule_id": "DQ-001"}
    )
    anomaly_id = repo.save_anomaly(event)
    
    # Query back directly
    conn = repo._get_connection()
    row = conn.execute("SELECT anomaly_id, run_id, evidence FROM anomaly_events WHERE anomaly_id = ?", [anomaly_id]).fetchone()
    assert row[0] == anomaly_id
    assert row[1] == "run-1"
    assert "DQ-001" in row[2]

def test_duplicate_handling(repo):
    event = AnomalyEvent(
        run_id="run-1",
        hospital_id="hosp-1",
        batch_id="batch-1",
        stage="validation",
        feature_name="null_rate",
        detector="BusinessRuleEngine",
        model_name="DQ_RULE_ENGINE",
        model_version="1.0.0",
        anomaly_type="DATA_QUALITY_VIOLATION",
        observed_value=1.0,
        expected_value=0.0,
        baseline_value=0.0,
        anomaly_score=1.0,
        confidence_score=1.0,
        severity="ERROR",
        evidence={"rule_id": "DQ-001"}
    )
    repo.save_anomaly(event)
    with pytest.raises(MetricsRepositoryError):
        repo.save_anomaly(event)

def test_save_anomalies_bulk(repo):
    events = [
        AnomalyEvent(
            run_id="run-1", hospital_id="hosp-1", batch_id="batch-1", stage="validation",
            feature_name="f1", detector="BusinessRuleEngine", model_name="M", model_version="1",
            anomaly_type="T", observed_value=1, expected_value=0, baseline_value=0,
            anomaly_score=1, confidence_score=1, severity="S", evidence={}
        ),
        AnomalyEvent(
            run_id="run-1", hospital_id="hosp-1", batch_id="batch-1", stage="validation",
            feature_name="f2", detector="BusinessRuleEngine", model_name="M", model_version="1",
            anomaly_type="T", observed_value=1, expected_value=0, baseline_value=0,
            anomaly_score=1, confidence_score=1, severity="S", evidence={}
        )
    ]
    count = repo.save_anomalies(events)
    assert count == 2
    conn = repo._get_connection()
    c = conn.execute("SELECT COUNT(*) FROM anomaly_events").fetchone()[0]
    assert c == 2
