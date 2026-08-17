import pytest
from pathlib import Path
from src.pipeline.landing.service import LandingService
from src.pipeline.landing.errors import ConflictError, PathViolationError

@pytest.fixture
def temp_workspace(tmp_path):
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    run_id = "run_test"
    
    run_dir = source_root / run_id
    hosp_a = run_dir / "hospital_A"
    hosp_a.mkdir(parents=True)
    
    file1 = hosp_a / "batch_20230101.csv"
    file1.write_text("CLM_ID|BENE_ID\n1|A")
    
    return {
        "source_root": source_root,
        "output_root": output_root,
        "run_id": run_id,
        "file1": file1,
        "run_dir": run_dir,
        "hosp_dir": hosp_a,
        "tmp_path": tmp_path
    }

def test_landing_conflict(temp_workspace):
    service = LandingService(
        source_root=str(temp_workspace["source_root"]),
        output_root=str(temp_workspace["output_root"]),
        run_id=temp_workspace["run_id"]
    )
    
    # Pre-create the destination file with DIFFERENT content
    dest_file = temp_workspace["output_root"] / temp_workspace["run_id"] / "hospital_A" / "batch_20230101.csv"
    dest_file.parent.mkdir(parents=True)
    dest_file.write_text("DIFFERENT_CONTENT")
    
    with pytest.raises(ConflictError):
        service.run()

def test_path_traversal(temp_workspace):
    service = LandingService(
        source_root=str(temp_workspace["source_root"]),
        output_root=str(temp_workspace["output_root"]),
        run_id=temp_workspace["run_id"]
    )
    
    # Try to trick copier into copying outside landing root by overriding internal properties
    # using a malicious source path.
    # In practice, service.run() constructs paths internally so this is a unit test of the copier.
    from src.pipeline.landing.copier import BatchCopier
    copier = BatchCopier(str(temp_workspace["source_root"]), str(temp_workspace["output_root"]))
    
    malicious_dest = temp_workspace["tmp_path"] / "outside_root.csv"
    
    with pytest.raises(PathViolationError):
        copier.safe_copy(temp_workspace["file1"], malicious_dest)

def test_missing_source_directory(temp_workspace):
    service = LandingService(
        source_root=str(temp_workspace["source_root"]),
        output_root=str(temp_workspace["output_root"]),
        run_id="nonexistent_run"
    )
    
    with pytest.raises(FileNotFoundError):
        service.run()
