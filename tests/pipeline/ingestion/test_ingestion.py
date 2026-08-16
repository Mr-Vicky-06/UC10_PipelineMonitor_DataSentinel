import pytest
import datetime
import polars as pl
from pathlib import Path
from src.pipeline.ingestion.discovery import BatchDiscoverer
from src.pipeline.ingestion.models import DiscoveredBatchSource
from src.pipeline.ingestion.reader import BatchReader
from src.pipeline.ingestion.service import IngestionService
from src.pipeline.ingestion.errors import FileFormatError

@pytest.fixture
def mock_ingestion_env(tmp_path):
    """Sets up a mock master_data and output environment."""
    run_id = "test_run_123"
    input_root = tmp_path / "master_data" / "batches"
    run_dir = input_root / run_id
    run_dir.mkdir(parents=True)
    
    # Create hospital directories
    hosp_a = run_dir / "hospital_A"
    hosp_a.mkdir()
    
    # Create valid batch file
    batch_1 = hosp_a / "batch_20230101.csv"
    batch_1.write_text("CLM_ID|CLM_LINE_NUM|HCPCS_CD\nC1|1|99213\nC1|2|99214\n")
    
    # Create valid batch file 2
    batch_2 = hosp_a / "batch_20230102.csv"
    batch_2.write_text("CLM_ID|CLM_LINE_NUM|HCPCS_CD\nC2|1|99215\n")
    
    # Create an invalid named file (should be ignored by discovery)
    bad_file = hosp_a / "not_a_batch.csv"
    bad_file.write_text("dummy")

    output_root = tmp_path / "outputs" / "pipeline_workspace"
    
    return {
        "input_root": str(input_root),
        "run_id": run_id,
        "output_root": str(output_root),
        "batch_1_path": str(batch_1),
        "batch_2_path": str(batch_2)
    }

def test_file_discovery(mock_ingestion_env):
    """Tests that files are discovered and metadata is extracted correctly."""
    discoverer = BatchDiscoverer(
        input_root=mock_ingestion_env["input_root"],
        run_id=mock_ingestion_env["run_id"]
    )
    sources = discoverer.discover()
    
    assert len(sources) == 2, "Should discover exactly 2 correctly named batch files"
    
    dates = [s.service_date for s in sources]
    assert datetime.date(2023, 1, 1) in dates
    assert datetime.date(2023, 1, 2) in dates
    
    hospitals = [s.hospital_id for s in sources]
    assert all(h == "hospital_A" for h in hospitals)

def test_reader_claim_line_preservation(mock_ingestion_env):
    """Tests that the reader exactly preserves claim grain and all strings."""
    source = DiscoveredBatchSource(
        source_file=mock_ingestion_env["batch_1_path"],
        hospital_id="hospital_A",
        batch_id="batch_20230101.csv",
        service_date=datetime.date(2023, 1, 1),
        file_size=100,
        file_format="csv",
        delimiter="|"
    )
    
    batch = BatchReader.read(source)
    
    assert batch.records_in == 2, "Should have 2 lines, preserving claim-line grain"
    # Ensure types are strings (preserve source representation)
    assert batch.dataframe.schema["CLM_ID"] == pl.String
    assert batch.dataframe.schema["CLM_LINE_NUM"] == pl.String
    assert batch.dataframe.schema["HCPCS_CD"] == pl.String
    
    # Ensure repeated CLM_ID is not deduplicated
    clm_ids = batch.dataframe["CLM_ID"].to_list()
    assert clm_ids == ["C1", "C1"]

def test_service_idempotency(mock_ingestion_env):
    """Tests that idempotency state blocks duplicate ingestion."""
    service = IngestionService(
        input_root=mock_ingestion_env["input_root"],
        run_id=mock_ingestion_env["run_id"],
        output_root=mock_ingestion_env["output_root"]
    )
    
    # First run
    batches_1 = service.run()
    assert len(batches_1) == 2
    
    # Second run should skip everything due to idempotency
    batches_2 = service.run()
    assert len(batches_2) == 0

