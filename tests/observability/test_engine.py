import pytest
import pandas as pd
import datetime
from unittest.mock import MagicMock, patch
from src.observability.models import ObservabilityStatus, FindingSeverity, FindingCategory
from src.observability.engine import ObservabilityEngine


def create_mock_events(run_id, is_healthy=True, missing_stage=None, failed_stage=None, 
                       slow_stage=None, volume_drop=False):
    """Generates a mock dataframe of telemetry events for adversarial testing."""
    stages = ["LANDING", "INGESTION", "VALIDATION", "CLEANING", "TRANSFORMATION", "BUSINESS_RULES", "STORAGE"]
    events = []
    ts = datetime.datetime.utcnow()
    
    records = 1000
    if volume_drop:
        records = 600
        
    for stage in stages:
        if stage == missing_stage:
            continue
            
        duration = 200
        if stage == slow_stage:
            duration = 5000
            
        status_event = 'COMPLETED'
        if stage == failed_stage:
            status_event = 'FAILED'
            
        events.append({
            'event_id': f'e1_{stage}', 'correlation_id': 'c1', 'timestamp': ts, 'run_id': run_id, 'hospital_id': 'H1', 'batch_id': 'b1',
            'source_file': 'test.csv', 'service_date': None, 'stage': stage, 'status': 'STARTED', 'duration_ms': 0,
            'records_in': records, 'records_out': records, 'records_failed': 0, 'records_rejected': 0, 'records_skipped': 0,
            'records_corrected': 0, 'violations_count': 0, 'errors': 0, 'warnings': 0, 'message': None, 'error_type': None, 'error_message': None
        })
        events.append({
            'event_id': f'e2_{stage}', 'correlation_id': 'c1', 'timestamp': ts + datetime.timedelta(milliseconds=duration), 
            'run_id': run_id, 'hospital_id': 'H1', 'batch_id': 'b1', 'source_file': 'test.csv', 'service_date': None, 
            'stage': stage, 'status': status_event, 'duration_ms': duration,
            'records_in': records, 'records_out': records, 'records_failed': 0, 'records_rejected': 0, 'records_skipped': 0,
            'records_corrected': 0, 'violations_count': 0, 'errors': 1 if status_event == 'FAILED' else 0, 'warnings': 0, 
            'message': None, 'error_type': None, 'error_message': "Failed" if status_event == 'FAILED' else None
        })
        if status_event == 'FAILED':
            break
            
    return pd.DataFrame(events)


def create_mock_historical_events():
    return create_mock_events('HIST_RUN_1', is_healthy=True)

def create_mock_historical_runs():
    return pd.DataFrame([{'run_id': 'HIST_RUN_1', 'last_ts': datetime.datetime.utcnow() - datetime.timedelta(minutes=60)}])


@patch('src.observability.repository.ObservabilityRepository')
def test_healthy_run(MockRepo):
    repo = MockRepo()
    repo.get_telemetry_events.return_value = create_mock_events('RUN_HEALTHY')
    repo.get_historical_successful_runs.return_value = create_mock_historical_runs()
    
    engine = ObservabilityEngine(repo=repo)
    result = engine.analyze_run('RUN_HEALTHY')
    
    assert result.overall_status == ObservabilityStatus.HEALTHY
    assert not any(f.severity == FindingSeverity.CRITICAL for f in result.findings if f.category == FindingCategory.PIPELINE_HEALTH)


@patch('src.observability.repository.ObservabilityRepository')
def test_volume_drop(MockRepo):
    repo = MockRepo()
    repo.get_telemetry_events.side_effect = lambda run_id=None: create_mock_events('RUN_VOL', volume_drop=True) if run_id == 'RUN_VOL' else create_mock_historical_events()
    repo.get_historical_successful_runs.return_value = create_mock_historical_runs()
    
    engine = ObservabilityEngine(repo=repo)
    result = engine.analyze_run('RUN_VOL')
    
    # Overall pipeline should still be healthy because it completed
    assert result.overall_status == ObservabilityStatus.HEALTHY
    vol_findings = [f for f in result.findings if f.category == FindingCategory.VOLUME]
    assert len(vol_findings) > 0
    assert any(f.severity == FindingSeverity.CRITICAL for f in vol_findings)


@patch('src.observability.repository.ObservabilityRepository')
def test_latency_spike(MockRepo):
    repo = MockRepo()
    repo.get_telemetry_events.side_effect = lambda run_id=None: create_mock_events('RUN_LAT', slow_stage="BUSINESS_RULES") if run_id == 'RUN_LAT' else create_mock_historical_events()
    repo.get_historical_successful_runs.return_value = create_mock_historical_runs()
    
    engine = ObservabilityEngine(repo=repo)
    result = engine.analyze_run('RUN_LAT')
    
    lat_findings = [f for f in result.findings if f.category == FindingCategory.LATENCY]
    assert len(lat_findings) > 0
    assert any(f.severity == FindingSeverity.CRITICAL and f.stage == "BUSINESS_RULES" for f in lat_findings)


@patch('src.observability.repository.ObservabilityRepository')
def test_missing_stage(MockRepo):
    repo = MockRepo()
    repo.get_telemetry_events.side_effect = lambda run_id=None: create_mock_events('RUN_MISS', missing_stage="CLEANING") if run_id == 'RUN_MISS' else create_mock_historical_events()
    repo.get_historical_successful_runs.return_value = create_mock_historical_runs()
    
    engine = ObservabilityEngine(repo=repo)
    result = engine.analyze_run('RUN_MISS')
    
    assert result.overall_status == ObservabilityStatus.INCOMPLETE


@patch('src.observability.repository.ObservabilityRepository')
def test_operational_failure(MockRepo):
    repo = MockRepo()
    repo.get_telemetry_events.side_effect = lambda run_id=None: create_mock_events('RUN_FAIL', failed_stage="TRANSFORMATION") if run_id == 'RUN_FAIL' else create_mock_historical_events()
    repo.get_historical_successful_runs.return_value = create_mock_historical_runs()
    
    engine = ObservabilityEngine(repo=repo)
    result = engine.analyze_run('RUN_FAIL')
    
    assert result.overall_status == ObservabilityStatus.FAILED


@patch('src.observability.repository.ObservabilityRepository')
def test_data_quality_spike_without_failure(MockRepo):
    repo = MockRepo()
    repo.get_telemetry_events.side_effect = lambda run_id=None: create_mock_events('RUN_DQ') if run_id == 'RUN_DQ' else create_mock_historical_events()
    repo.get_historical_successful_runs.return_value = create_mock_historical_runs()
    
    # Mock processed claims for length
    repo.get_processed_claims.return_value = pd.DataFrame([{'a':1}] * 1000)
    
    # Mock rule results (current has 700 fails, hist has 50)
    repo.get_rule_results.side_effect = lambda run_id=None: pd.DataFrame([{'status': 'FAIL'}] * 700) if run_id == 'RUN_DQ' else pd.DataFrame([{'status': 'FAIL'}] * 50)

    engine = ObservabilityEngine(repo=repo)
    result = engine.analyze_run('RUN_DQ')
    
    assert result.overall_status == ObservabilityStatus.HEALTHY
    assert result.operational_errors == 0
    
    dq_findings = [f for f in result.findings if f.category == FindingCategory.DATA_QUALITY]
    assert len(dq_findings) > 0
    assert any(f.severity == FindingSeverity.CRITICAL for f in dq_findings)
