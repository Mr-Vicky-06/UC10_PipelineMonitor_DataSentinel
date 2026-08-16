import os
import csv
import time
import yaml
import hashlib
import psutil
from pathlib import Path
from collections import defaultdict
from src.pipeline.ingestion import IngestionService

def hash_file(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_benchmark_and_reconciliation():
    config_path = Path("configs/pipeline_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    input_root = config["input_root"]
    active_run_id = config["active_run_id"]
    output_root = config["output_root"]
    delimiter = config["ingestion"]["delimiter"]
    
    # 1. Hash Source File Before (sample first hospital)
    sample_file = list(Path(f"{input_root}/{active_run_id}/hospital_A").glob("*.csv"))[0]
    hash_before = hash_file(sample_file)
    print(f"Pre-ingestion SHA-256 of {sample_file.name}: {hash_before}")

    service = IngestionService(input_root, active_run_id, output_root, delimiter)
    
    # Force state to empty to avoid idempotency skip
    service._state_cache = {} 

    start_time = time.time()
    process = psutil.Process(os.getpid())
    peak_memory = 0
    
    print("\nRunning full 1,137 file ingestion...")
    batches = service.run()
    
    end_time = time.time()
    
    peak_memory = process.memory_info().rss / (1024 * 1024)
    duration = end_time - start_time
    total_files = len(batches)
    total_records = sum(b.records_in for b in batches)
    
    print("\n--- PERFORMANCE ---")
    print(f"Total Files: {total_files}")
    print(f"Total Records: {total_records}")
    print(f"Runtime: {duration:.2f} seconds")
    if duration > 0:
        print(f"Files/sec: {total_files / duration:.2f}")
        print(f"Records/sec: {total_records / duration:.2f}")
    print(f"Peak Memory: {peak_memory:.2f} MB")
    
    # 2. Hash Source File After
    hash_after = hash_file(sample_file)
    print(f"\nPost-ingestion SHA-256 of {sample_file.name}: {hash_after}")
    print(f"Source Hash Intact? {hash_before == hash_after}")

    # 3. Fingerprinting & Reconciliation (on sample_file)
    print("\n--- FINGERPRINTING & RECONCILIATION ---")
    
    # Raw python CSV reader counts
    source_rows = 0
    clm_id_index = None
    with open(sample_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = next(reader)
        if "CLM_ID" in header:
            clm_id_index = header.index("CLM_ID")
        for row in reader:
            source_rows += 1
            
    # Find ingested batch for that file
    sample_batch = next(b for b in batches if b.source_file == str(sample_file.absolute()))
    
    print(f"Source rows (raw): {source_rows}")
    print(f"Ingested rows (polars): {sample_batch.records_in}")
    print(f"Difference: {source_rows - sample_batch.records_in}")
    
    # Logical claim grain check
    clm_ids_in_polars = sample_batch.dataframe["CLM_ID"].to_list()
    distinct_clm = set(clm_ids_in_polars)
    print(f"Total claim lines in ingested: {len(clm_ids_in_polars)}")
    print(f"Distinct CLM_IDs in ingested: {len(distinct_clm)}")
    
    # Quick BENE_ID count
    bene_ids_in_polars = sample_batch.dataframe["BENE_ID"].to_list()
    print(f"Distinct BENE_IDs in ingested: {len(set(bene_ids_in_polars))}")

if __name__ == "__main__":
    run_benchmark_and_reconciliation()
