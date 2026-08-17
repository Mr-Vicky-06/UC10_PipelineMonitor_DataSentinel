import os
import pytest
import shutil
import pandas as pd
from pathlib import Path
from src.pipeline.orchestrator import PipelineOrchestrator

@pytest.fixture
def mock_pipeline_workspace(tmp_path, monkeypatch):
    df = pd.DataFrame({
        'CLM_ID': ['C1', 'C2'],
        'CLM_LINE_NUM': ['1', '1'],
        'BENE_ID': ['B1', 'B2'],
        'PRVDR_ID': ['P1', 'P2'],
        'CLM_FROM_DT': ['20230101', '20230102'],
        'CLM_THRU_DT': ['20230105', '20230106'],
        'CLM_PMT_AMT': ['100.0', '200.0'],
        'BENE_AGE_CNT': ['65', '70']
    })
    
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    def mock_init(self, config_path=""):
        self.config_path = "src/pipeline/config.yaml"
        self.landing_output = str(workspace / "landing")
        self.ingestion_output = str(workspace / "ingestion")
        self.duckdb_path = str(workspace / "processed_claims.duckdb")
        
    monkeypatch.setattr("src.pipeline.orchestrator.PipelineOrchestrator.__init__", mock_init)
    
    def mock_clean_dataset(*args, **kwargs):
        from src.cleaning.models import CleaningResult, CleaningReport, CleaningMetrics, CleaningStatus
        from datetime import datetime
        
        report = CleaningReport(
            run_id="test", dataset="claims", input_file="test", output_file="test",
            start_time=datetime.now().isoformat(), end_time=datetime.now().isoformat(),
            status=CleaningStatus.SUCCESS, metrics=CleaningMetrics()
        )
        df_in = kwargs.get('input_path_or_df')
        
        # If it's the bad dataset, simulate validation failure
        if 'CLM_ID' not in df_in.columns:
            return CleaningResult(cleaned_df=df_in, report=report, passed=False)
            
        return CleaningResult(cleaned_df=df_in, report=report, passed=True)
        
    monkeypatch.setattr("src.pipeline.orchestrator.clean_dataset", mock_clean_dataset)
    
    return tmp_path, df

def test_successful_execution(mock_pipeline_workspace):
    tmp_path, df = mock_pipeline_workspace
    
    # Create source
    run_id = "TEST_RUN_1"
    source = tmp_path / "source"
    batch_dir = source / run_id / "HOSP-TEST"
    batch_dir.mkdir(parents=True)
    df.to_csv(batch_dir / "batch_20230101.csv", sep='|', index=False)
    
    orchestrator = PipelineOrchestrator()
    res = orchestrator.run(source_directory=str(source), run_id=run_id)
    
    assert res.is_successful is True
    assert res.records_received == 2
    assert res.records_persisted == 2
    assert res.operational_errors == 0
    assert res.run_id == run_id
    
def test_idempotency_handling(mock_pipeline_workspace):
    tmp_path, df = mock_pipeline_workspace
    
    run_id = "TEST_RUN_2"
    source = tmp_path / "source"
    batch_dir = source / run_id / "HOSP-TEST"
    batch_dir.mkdir(parents=True)
    df.to_csv(batch_dir / "batch_20230101.csv", sep='|', index=False)
    
    orchestrator = PipelineOrchestrator()
    # First run
    res1 = orchestrator.run(source_directory=str(source), run_id=run_id)
    assert res1.is_successful is True
    assert res1.records_persisted == 2
    
    run_id_3 = "TEST_RUN_3"
    batch_dir_3 = source / run_id_3 / "HOSP-TEST"
    batch_dir_3.mkdir(parents=True)
    df.to_csv(batch_dir_3 / "batch_20230101.csv", sep='|', index=False)
    
    # Second run with same batch ID (batch_20230101.csv) should skip due to idempotency registry
    res2 = orchestrator.run(source_directory=str(source), run_id=run_id_3)
    assert res2.is_successful is True
    assert "Idempotency skip" in str(res2.error_message) or "No batches ingested" in str(res2.error_message)
    assert res2.records_received == 0
    
def test_validation_failure(mock_pipeline_workspace):
    tmp_path, df = mock_pipeline_workspace
    
    run_id = "TEST_RUN_BAD"
    source = tmp_path / "source"
    batch_dir = source / run_id / "HOSP-TEST"
    batch_dir.mkdir(parents=True)
    
    # Intentionally corrupt the dataset to fail schema validation
    df_bad = pd.DataFrame({
        'CLM_LINE_NUM': ['1']
    })
    df_bad.to_csv(batch_dir / "batch_20230102.csv", sep='|', index=False)
    
    orchestrator = PipelineOrchestrator()
    res = orchestrator.run(source_directory=str(source), run_id=run_id)
    
    assert res.is_successful is False
    assert "Validation/Cleaning failed" in res.error_message
    assert res.operational_errors == 1
