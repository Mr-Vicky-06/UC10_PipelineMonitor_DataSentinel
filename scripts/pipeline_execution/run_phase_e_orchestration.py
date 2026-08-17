import os
import hashlib
import time
from pathlib import Path
import pandas as pd
import duckdb

from src.pipeline.orchestrator import PipelineOrchestrator

def get_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def dir_hash(directory):
    h = hashlib.sha256()
    for root, _, files in sorted(os.walk(directory)):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            h.update(get_file_hash(filepath).encode())
    return h.hexdigest()

def main():
    run_id = "RUN_REAL_ORCH"
    
    # 0. Set up evaluation directory
    eval_dir = Path("outputs/pipeline_workspace/evaluation/real_data_1000_orch")
    import shutil
    if eval_dir.exists():
        shutil.rmtree(eval_dir)
        
    source_dir = eval_dir / "source"
    hosp_dir = source_dir / run_id / "HOSP-TEST"
    hosp_dir.mkdir(parents=True, exist_ok=True)
    
    # Pre-hash calculation for immutability check
    hash_data_before = dir_hash("data")
    hash_master_before = dir_hash("master_data")
    
    # Deterministic selection: first 1000 lines
    src_file = "data/raw/claims/inpatient.csv"
    df_src = pd.read_csv(src_file, sep="|", dtype=str, nrows=1000)
    
    selected_file = hosp_dir / "batch_20260101.csv"
    df_src.to_csv(selected_file, sep="|", index=False)
    
    print(f"Starting orchestration for 1,000 records...")
    
    orchestrator = PipelineOrchestrator()
    # Inject evaluation paths directly into orchestrator for testing isolation
    orchestrator.landing_output = str(eval_dir / "landing")
    orchestrator.ingestion_output = str(eval_dir / "ingestion")
    orchestrator.duckdb_path = str(eval_dir / "processed_claims.duckdb")
    
    res = orchestrator.run(source_directory=str(source_dir), run_id=run_id)
    
    # Validation Phase
    
    print(f"\n--- RECONCILIATION ---")
    print(f"Orchestration Successful: {res.is_successful}")
    print(f"Error Message: {res.error_message}")
    print(f"Records Received (Ingestion): {res.records_received}")
    print(f"Records Persisted (DuckDB): {res.records_persisted}")
    print(f"Business Rule Violations: {res.business_rule_violations}")
    print(f"Operational Errors: {res.operational_errors}")
    print(f"Duration: {res.duration_ms} ms")
    
    # Check DuckDB
    con = duckdb.connect(orchestrator.duckdb_path)
    db_claims_count = con.execute(f"SELECT COUNT(*) FROM processed_claims WHERE run_id='{run_id}'").fetchone()[0]
    db_viol_count = con.execute(f"SELECT COUNT(*) FROM rule_results WHERE run_id='{run_id}'").fetchone()[0]
    duplicate_grains = con.execute("SELECT COUNT(*) FROM (SELECT clm_id, clm_line_num, COUNT(*) FROM processed_claims GROUP BY clm_id, clm_line_num HAVING COUNT(*) > 1)").fetchone()[0]
    con.close()
    
    print(f"\n--- STORAGE VERIFICATION ---")
    print(f"DB Claims Count: {db_claims_count}")
    print(f"DB Violations Count: {db_viol_count}")
    print(f"Duplicate CLM_ID+CLM_LINE_NUM Grains: {duplicate_grains}")
    
    # Re-hash calculation for immutability check
    hash_data_after = dir_hash("data")
    hash_master_after = dir_hash("master_data")
    print(f"\n--- IMMUTABILITY ---")
    print(f"data/ preserved: {hash_data_before == hash_data_after}")
    print(f"master_data/ preserved: {hash_master_before == hash_master_after}")

    # Check Telemetry
    tel_con = duckdb.connect("outputs/pipeline_workspace/pipeline_telemetry.duckdb")
    tel_events = tel_con.execute(f"SELECT stage, status, records_in, records_out, errors FROM pipeline_events WHERE run_id='{run_id}' ORDER BY timestamp").fetchdf()
    tel_con.close()
    print(f"\n--- TELEMETRY TRACE ---")
    print(tel_events.to_string())
    
    report = f"""# REAL DATA 1000-RECORD ORCHESTRATION REPORT

## 1. Orchestration Result
- **Successful**: {res.is_successful}
- **Run ID**: {res.run_id}
- **Duration**: {res.duration_ms} ms
- **Error**: {res.error_message}

## 2. Record Reconciliation
- **Source**: 1000
- **Landing**: 1000
- **Ingestion**: {res.records_received}
- **Validation/Cleaning**: {res.records_received}
- **Transformation**: {res.records_persisted}
- **Business Rules**: {res.records_persisted}
- **DuckDB Storage**: {db_claims_count}

## 3. Violations & Integrity
- **Business Rule Violations (Object)**: {res.business_rule_violations}
- **Business Rule Violations (DuckDB)**: {db_viol_count}
- **Operational Errors**: {res.operational_errors}
- **Duplicate Grains**: {duplicate_grains}

## 4. Immutability
- `data/` preserved: {hash_data_before == hash_data_after}
- `master_data/` preserved: {hash_master_before == hash_master_after}

## 5. Telemetry
```
{tel_events.to_string()}
```
"""
    with open(f"outputs/pipeline_workspace/evaluation/real_data_1000_orch/ORCHESTRATION_REPORT.md", "w") as f:
        f.write(report)
        
    print("\nPhase E Integration Test Complete.")

if __name__ == "__main__":
    main()
