import pytest
import datetime
import polars as pl
from pathlib import Path
from src.pipeline.ingestion.discovery import BatchDiscoverer
from src.pipeline.ingestion.reader import BatchReader
from src.pipeline.ingestion.models import DiscoveredBatchSource
from src.pipeline.ingestion.errors import FileFormatError

@pytest.fixture
def synthetic_workspace(tmp_path):
    run_dir = tmp_path / "run_synthetic"
    hosp = run_dir / "hospital_A"
    hosp.mkdir(parents=True)
    return {
        "run_dir": run_dir,
        "hosp_dir": hosp,
        "tmp_path": tmp_path
    }

def test_missing_file_discovery(synthetic_workspace):
    # Empty directory
    discoverer = BatchDiscoverer(synthetic_workspace["tmp_path"], "run_synthetic")
    sources = discoverer.discover()
    assert len(sources) == 0

def test_empty_file(synthetic_workspace):
    file_path = synthetic_workspace["hosp_dir"] / "batch_20230101.csv"
    file_path.write_text("")
    
    source = DiscoveredBatchSource(
        source_file=str(file_path), hospital_id="hospital_A", batch_id="batch_20230101.csv",
        service_date=datetime.date(2023, 1, 1), file_size=0, file_format="csv", delimiter="|"
    )
    # Polars raises NoDataError for empty file, wrapped in FileFormatError
    with pytest.raises(FileFormatError):
        BatchReader.read(source)

def test_malformed_filename(synthetic_workspace):
    file_path = synthetic_workspace["hosp_dir"] / "claims.csv"
    file_path.write_text("CLM_ID\n1")
    
    discoverer = BatchDiscoverer(synthetic_workspace["tmp_path"], "run_synthetic")
    sources = discoverer.discover()
    assert len(sources) == 0, "Malformed filenames should be ignored by discovery"

def test_wrong_delimiter(synthetic_workspace):
    file_path = synthetic_workspace["hosp_dir"] / "batch_20230101.csv"
    # Comma delimited instead of pipe
    file_path.write_text("CLM_ID,BENE_ID\n1,2")
    
    source = DiscoveredBatchSource(
        source_file=str(file_path), hospital_id="hospital_A", batch_id="batch_20230101.csv",
        service_date=datetime.date(2023, 1, 1), file_size=20, file_format="csv", delimiter="|"
    )
    batch = BatchReader.read(source)
    # Polars with wrong delimiter might parse it as 1 column
    assert len(batch.dataframe.columns) == 1
    assert batch.dataframe.columns[0] == "CLM_ID,BENE_ID"

def test_missing_column(synthetic_workspace):
    file_path = synthetic_workspace["hosp_dir"] / "batch_20230101.csv"
    # Only one column instead of all expected
    file_path.write_text("CLM_ID\n1")
    
    source = DiscoveredBatchSource(
        source_file=str(file_path), hospital_id="hospital_A", batch_id="batch_20230101.csv",
        service_date=datetime.date(2023, 1, 1), file_size=20, file_format="csv", delimiter="|"
    )
    batch = BatchReader.read(source)
    assert batch.dataframe.columns == ["CLM_ID"]
    # Structural handling is deferred to Validation. Ingestion preserves it.

def test_duplicate_clm_id(synthetic_workspace):
    file_path = synthetic_workspace["hosp_dir"] / "batch_20230101.csv"
    file_path.write_text("CLM_ID|CLM_LINE_NUM\nC1|1\nC1|2\nC1|3\n")
    
    source = DiscoveredBatchSource(
        source_file=str(file_path), hospital_id="hospital_A", batch_id="batch_20230101.csv",
        service_date=datetime.date(2023, 1, 1), file_size=40, file_format="csv", delimiter="|"
    )
    batch = BatchReader.read(source)
    assert batch.records_in == 3
    assert batch.dataframe["CLM_ID"].to_list() == ["C1", "C1", "C1"]
    
def test_missing_bene_id_and_invalid_date(synthetic_workspace):
    file_path = synthetic_workspace["hosp_dir"] / "batch_20230101.csv"
    # BENE_ID is missing (empty), date is invalid (9999-99-99)
    file_path.write_text("CLM_ID|BENE_ID|CLM_FROM_DT\nC1||9999-99-99\n")
    
    source = DiscoveredBatchSource(
        source_file=str(file_path), hospital_id="hospital_A", batch_id="batch_20230101.csv",
        service_date=datetime.date(2023, 1, 1), file_size=40, file_format="csv", delimiter="|"
    )
    batch = BatchReader.read(source)
    # Types must be string, not crashing on parse
    assert batch.dataframe.schema["BENE_ID"] == pl.String
    assert batch.dataframe.schema["CLM_FROM_DT"] == pl.String
    assert batch.dataframe["BENE_ID"].to_list() == [None]  # Polars parses empty string as null if null_values=[""]
    assert batch.dataframe["CLM_FROM_DT"].to_list() == ["9999-99-99"]

def test_path_traversal_safety(synthetic_workspace):
    # Try discovering outside of the configured root
    discoverer = BatchDiscoverer(str(synthetic_workspace["tmp_path"] / "nonexistent"), "run_synthetic")
    with pytest.raises(Exception):
        discoverer.discover()
