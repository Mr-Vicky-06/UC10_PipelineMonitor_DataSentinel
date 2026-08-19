import os
import time
import pandas as pd
from pathlib import Path

from src.pipeline.orchestrator import PipelineOrchestrator

def main():
    print("Starting LIVE Demo with full dataset (58k records)...")
    src_file = "data/raw/claims/inpatient.csv"
    
    # Read the full dataset
    print(f"Reading {src_file}...")
    df_full = pd.read_csv(src_file, sep="|", dtype=str)
    total_records = len(df_full)
    print(f"Loaded {total_records} records.")
    
    chunk_size = 2000
    num_chunks = (total_records // chunk_size) + (1 if total_records % chunk_size != 0 else 0)
    
    base_source_dir = Path("outputs/pipeline_workspace/live_demo/source")
    
    orchestrator = PipelineOrchestrator()
    # Ensure orchestrator uses the correct global outputs, not isolated ones
    orchestrator.landing_output = "outputs/pipeline_workspace/landing"
    orchestrator.ingestion_output = "outputs/pipeline_workspace/ingestion"
    orchestrator.duckdb_path = "outputs/pipeline_workspace/processed_claims.duckdb"
    
    print(f"Divided into {num_chunks} batches of up to {chunk_size} records each.")
    print("Beginning live orchestration. Check the Operations Center UI to see live updates!\n")
    
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total_records)
        df_chunk = df_full.iloc[start_idx:end_idx]
        
        run_id = f"RUN_LIVE_BATCH_{i+1:03d}"
        batch_id = f"batch_{20260101 + i}"
        
        # Write chunk to source dir
        hosp_dir = base_source_dir / run_id / "HOSP-TEST"
        hosp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = hosp_dir / f"{batch_id}.csv"
        df_chunk.to_csv(file_path, sep="|", index=False)
        
        print(f"[{i+1}/{num_chunks}] Orchestrating {run_id} ({len(df_chunk)} records)...")
        
        res = orchestrator.run(source_directory=str(base_source_dir), run_id=run_id)
        
        status = "SUCCESS" if res.is_successful else f"FAILED: {res.error_message}"
        print(f"   -> Result: {status} | Duration: {res.duration_ms} ms | Persisted: {res.records_persisted} | Violations: {res.business_rule_violations}")
        
        # Brief pause to let UI fetch and visually update
        time.sleep(2)

    print("\nLive demo complete!")

if __name__ == "__main__":
    main()
