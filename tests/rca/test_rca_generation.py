import pytest
import datetime
from unittest.mock import Mock

from src.rag.models.evidence import EvidencePack, Evidence
from src.rag.generation.rca_generator import RCAGenerator

def build_mock_evidence(ev_type: str, severity: str, obs_value: str, id_prefix: str) -> Evidence:
    return Evidence(
        evidence_id=f"{id_prefix}_1",
        run_id="run_1",
        hospital_id="H1",
        batch_id="B1",
        stage="INGESTION",
        timestamp=datetime.datetime.utcnow(),
        source="mock_src",
        evidence_type=ev_type,
        identifier="test_rule",
        observed_value=obs_value,
        severity=severity
    )

@pytest.fixture
def mock_provider():
    provider = Mock()
    # By default, mock the LLM output. The RCAGenerator's `generate` will call this.
    # The deterministic fields (severity, confidence) will be overwritten anyway.
    provider.generate_structured_rca.return_value = {
        "summary": "Mock LLM Summary",
        "what_happened": "Mock LLM What Happened",
        "facts": [{"description": "Fact 1", "evidence_ids": ["ev_1"]}],
        "confirmed_findings": [],
        "correlated_findings": [],
        "likely_causes": [],
        "recommended_investigation": "Check the system"
    }
    return provider

def test_rca_normal_run(mock_provider):
    gen = RCAGenerator(mock_provider)
    ev = build_mock_evidence("operational_metric", "INFO", "Success", "ev")
    pack = EvidencePack(query="Analyze run", intent="RCA", evidence=[ev])
    
    res = gen.generate(pack)
    assert res.severity == "INFO"
    assert res.confidence == "ZERO" # Only operational_metric, not DQ/ML/SLA/Fail
    
def test_rca_dq_violation(mock_provider):
    gen = RCAGenerator(mock_provider)
    ev = build_mock_evidence("rule_violation", "WARNING", "DQ Error", "ev")
    pack = EvidencePack(query="Analyze run", intent="RCA", evidence=[ev])
    
    res = gen.generate(pack)
    assert res.severity == "WARNING"
    assert res.confidence == "HIGH" # DQ -> HIGH

def test_rca_ml_anomaly(mock_provider):
    gen = RCAGenerator(mock_provider)
    ev = build_mock_evidence("statistical_anomaly", "WARNING", "ML Anomaly", "ev")
    pack = EvidencePack(query="Analyze run", intent="RCA", evidence=[ev])
    
    res = gen.generate(pack)
    assert res.severity == "WARNING"
    assert res.confidence == "LOW" # ML only -> LOW

def test_rca_operational_failure(mock_provider):
    gen = RCAGenerator(mock_provider)
    ev = build_mock_evidence("pipeline_failure", "CRITICAL", "DB Crash", "ev")
    pack = EvidencePack(query="Analyze run", intent="RCA", evidence=[ev])
    
    res = gen.generate(pack)
    assert res.severity == "CRITICAL"
    assert res.confidence == "HIGH" # Pipeline fail -> HIGH

def test_rca_sla_breach(mock_provider):
    gen = RCAGenerator(mock_provider)
    ev = build_mock_evidence("sla_status", "ERROR", "BREACHED", "ev")
    pack = EvidencePack(query="Analyze run", intent="RCA", evidence=[ev])
    
    res = gen.generate(pack)
    assert res.severity == "ERROR"
    assert res.confidence == "LOW" # SLA only -> LOW

def test_rca_multi_signal(mock_provider):
    gen = RCAGenerator(mock_provider)
    ev1 = build_mock_evidence("statistical_anomaly", "WARNING", "Anomaly", "ev1")
    ev2 = build_mock_evidence("sla_status", "ERROR", "BREACHED", "ev2")
    
    pack = EvidencePack(query="Analyze run", intent="RCA", evidence=[ev1, ev2])
    
    mock_provider.generate_structured_rca.return_value["facts"] = [
        {"description": "f1", "evidence_ids": ["ev1_1"]},
        {"description": "f2", "evidence_ids": ["ev2_1"]}
    ]
    
    res = gen.generate(pack)
    assert res.severity == "ERROR" # Max of WARNING and ERROR
    assert res.confidence == "MEDIUM" # ML + SLA = 2 signals -> MEDIUM

def test_rca_missing_evidence(mock_provider):
    gen = RCAGenerator(mock_provider)
    pack = EvidencePack(query="Analyze run", intent="RCA", evidence=[])
    
    res = gen.generate(pack)
    assert res.severity == "INFO"
    assert res.confidence == "ZERO"
    assert "Insufficient evidence" in res.what_happened

def test_rca_hallucinated_citation(mock_provider):
    gen = RCAGenerator(mock_provider)
    ev = build_mock_evidence("operational_metric", "INFO", "Success", "ev")
    pack = EvidencePack(query="Analyze run", intent="RCA", evidence=[ev])
    
    # LLM hallucinating 'ev_999'
    mock_provider.generate_structured_rca.return_value["facts"] = [{"description": "Fact", "evidence_ids": ["ev_999"]}]
    
    res = gen.generate(pack)
    
    # Should be caught by CitationValidator and return the fallback
    assert "Insufficient evidence" in res.what_happened or "Gemini API unavailable" in res.summary
    assert res.confidence == "ZERO" # Recalculated for fallback
