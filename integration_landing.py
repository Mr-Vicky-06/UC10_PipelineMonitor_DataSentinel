import time
import yaml
import hashlib
from pathlib import Path
from src.pipeline.landing.service import LandingService
from src.pipeline.landing.models import LandingStatus
from src.pipeline.ingestion.service import IngestionService

def hash_file(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_integration():
    config_path = Path("configs/pipeline_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    source_root = config["landing"]["source_root"]
    landing_output_root = config["landing"]["output_root"]
    active_run_id = config["active_run_id"]
    
    # 1. Pre-hash sample source file
    sample_source = list(Path(f"{source_root}/{active_run_id}/hospital_A").glob("*.csv"))[0]
    pre_hash = hash_file(sample_source)
    print(f"Pre-landing source SHA-256: {pre_hash}")
    
    # 2. Run Landing
    start_time = time.time()
    landing_service = LandingService(source_root, landing_output_root, active_run_id)
    print("\nStarting Landing...")
    landed_batches = landing_service.run()
    landing_duration = time.time() - start_time
    
    # 3. Post-hash sample source file
    post_hash = hash_file(sample_source)
    print(f"Post-landing source SHA-256: {post_hash}")
    print(f"Source Immutability Maintained: {pre_hash == post_hash}")
    
    # 4. Landing Metrics
    total_bytes = sum(b.size_bytes for b in landed_batches)
    print("\n--- LANDING RESULTS ---")
    print(f"Files Copied: {len(landed_batches)}")
    print(f"Total Bytes: {total_bytes / (1024*1024):.2f} MB")
    print(f"Duration: {landing_duration:.2f} s")
    if landing_duration > 0:
        print(f"Files/sec: {len(landed_batches) / landing_duration:.2f}")
        print(f"MB/sec: {(total_bytes / (1024*1024)) / landing_duration:.2f}")
        
    # Check conflicts/status
    statuses = [b.status for b in landed_batches]
    print(f"LANDED: {statuses.count(LandingStatus.LANDED)}")
    print(f"ALREADY_LANDED: {statuses.count(LandingStatus.ALREADY_LANDED)}")
    print(f"CONFLICT: {statuses.count(LandingStatus.CONFLICT)}")

    # 5. Run Ingestion against Landing Directory
    print("\nStarting Ingestion from Landing Directory...")
    ingestion_input_root = config["ingestion"]["input_root"]
    ingestion_output_root = config["ingestion"]["output_root"]
    delimiter = config["ingestion"]["delimiter"]
    
    ingestion_service = IngestionService(
        input_root=ingestion_input_root,
        run_id=active_run_id,
        output_root=ingestion_output_root,
        delimiter=delimiter
    )
    # Clear state so it actually runs
    ingestion_service._state_cache = {}
    
    ingestion_start = time.time()
    ingested_batches = ingestion_service.run()
    ingestion_duration = time.time() - ingestion_start
    
    total_records = sum(b.records_in for b in ingested_batches)
    print("\n--- INGESTION RESULTS ---")
    print(f"Ingested Files: {len(ingested_batches)}")
    print(f"Total Records: {total_records}")
    print(f"Duration: {ingestion_duration:.2f} s")
    
if __name__ == "__main__":
    run_integration()
