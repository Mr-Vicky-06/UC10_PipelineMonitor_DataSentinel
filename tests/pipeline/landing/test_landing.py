import pytest
import json
from pathlib import Path
from src.pipeline.landing.service import LandingService
from src.pipeline.landing.models import LandingStatus

@pytest.fixture
def temp_workspace(tmp_path):
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    run_id = "run_test"
    
    # Create source data
    run_dir = source_root / run_id
    hosp_a = run_dir / "hospital_A"
    hosp_a.mkdir(parents=True)
    
    file1 = hosp_a / "batch_20230101.csv"
    file1.write_text("CLM_ID|BENE_ID\n1|A")
    
    file2 = hosp_a / "batch_20230102.csv"
    file2.write_text("CLM_ID|BENE_ID\n2|B")
    
    return {
        "source_root": source_root,
        "output_root": output_root,
        "run_id": run_id,
        "file1": file1,
        "file2": file2
    }

def test_landing_success(temp_workspace):
    service = LandingService(
        source_root=str(temp_workspace["source_root"]),
        output_root=str(temp_workspace["output_root"]),
        run_id=temp_workspace["run_id"]
    )
    
    batches = service.run()
    
    assert len(batches) == 2
    for b in batches:
        assert b.status == LandingStatus.LANDED
        assert b.source_sha256 == b.landing_sha256
        assert Path(b.landing_path).exists()
        
    manifest_path = temp_workspace["output_root"] / temp_workspace["run_id"] / "landing_manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        assert manifest["total_source_files"] == 2
        assert manifest["total_landed_files"] == 2

def test_landing_idempotency(temp_workspace):
    service = LandingService(
        source_root=str(temp_workspace["source_root"]),
        output_root=str(temp_workspace["output_root"]),
        run_id=temp_workspace["run_id"]
    )
    
    # Run 1
    batches1 = service.run()
    assert all(b.status == LandingStatus.LANDED for b in batches1)
    
    # Run 2
    batches2 = service.run()
    assert all(b.status == LandingStatus.ALREADY_LANDED for b in batches2)
