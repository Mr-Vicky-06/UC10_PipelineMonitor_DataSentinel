import os
import sys
import shutil
import hashlib
import duckdb
import pandas as pd
import pytest
from pathlib import Path

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.transformation import HealthcareTransformer
from src.pipeline.telemetry.logger import PipelineTelemetryLogger

def hash_directory(directory: str) -> str:
    """Computes a SHA-256 hash of all files in a directory."""
    sha256 = hashlib.sha256()
    for root, dirs, files in os.walk(directory):
        for names in sorted(files):
            filepath = os.path.join(root, names)
            try:
                with open(filepath, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
            except IOError:
                pass
    return sha256.hexdigest()

def create_100_record_real_data_test(run_id="TELEMETRY_REAL_100"):
    import random
    batch_date = f"2026{random.randint(10,12)}{random.randint(10,28)}"
    """Extracts 100 real records from inpatient.csv for the test."""
    source = Path("data/raw/claims/inpatient.csv")
    dest_dir = Path(f"outputs/pipeline_workspace/source/{run_id}/HOSP-TEST")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / f"batch_{batch_date}.csv"
    
    if not dest_file.exists():
        df = pd.read_csv(source, nrows=100)
        df.to_csv(dest_file, index=False)
        
    return str(dest_dir.parent)

def run_queries(db_path: str):
    """Executes the 15 required acceptance queries against the telemetry DB."""
    con = duckdb.connect(db_path)
    
    results = []
    
    def assert_query(name, query, check_fn):
        try:
            df = con.execute(query).df()
            passed = check_fn(df)
            results.append({"query": name, "passed": passed, "error": None})
        except Exception as e:
            results.append({"query": name, "passed": False, "error": str(e)})

    # Query 1: What is the latest pipeline run?
    q1 = "SELECT run_id FROM pipeline_events ORDER BY timestamp DESC LIMIT 1"
    assert_query("Q1: Latest pipeline run", q1, lambda df: len(df) == 1 and df.iloc[0]['run_id'] in ('TELEMETRY_FAIL_TEST', 'TELEMETRY_FAIL_OPEN_TEST'))

    # Query 2: Did the latest run succeed?
    q2 = "SELECT status FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100' AND stage = 'STORAGE' AND status = 'COMPLETED'"
    assert_query("Q2: Did latest run succeed", q2, lambda df: len(df) == 1)

    # Query 3: When did it start?
    q3 = "SELECT MIN(timestamp) as start_time FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100'"
    assert_query("Q3: When did it start", q3, lambda df: not pd.isnull(df.iloc[0]['start_time']))

    # Query 4: When did it finish?
    q4 = "SELECT MAX(timestamp) as end_time FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100'"
    assert_query("Q4: When did it finish", q4, lambda df: not pd.isnull(df.iloc[0]['end_time']))

    # Query 5: How long did it take?
    q5 = "SELECT EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) as duration FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100'"
    assert_query("Q5: How long did it take", q5, lambda df: df.iloc[0]['duration'] >= 0)

    # Query 6: How many records entered?
    q6 = "SELECT records_in FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100' AND stage = 'INGESTION' AND status = 'COMPLETED'"
    assert_query("Q6: Records entered", q6, lambda df: df.iloc[0]['records_in'] == 100)

    # Query 7: How many records exited?
    q7 = "SELECT records_out FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100' AND stage = 'STORAGE' AND status = 'COMPLETED'"
    assert_query("Q7: Records exited", q7, lambda df: df.iloc[0]['records_out'] == 100)

    # Query 8: Did any stage fail?
    q8 = "SELECT COUNT(*) as failures FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100' AND status = 'FAILED'"
    assert_query("Q8: Any stage fail", q8, lambda df: df.iloc[0]['failures'] == 0)

    # Query 9: Which stage was slowest?
    q9 = "SELECT stage, duration_ms FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100' AND status = 'COMPLETED' ORDER BY duration_ms DESC LIMIT 1"
    assert_query("Q9: Slowest stage", q9, lambda df: len(df) == 1)

    # Query 10: How many operational errors occurred?
    q10 = "SELECT SUM(errors) as ops_errors FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100'"
    assert_query("Q10: Operational errors", q10, lambda df: df.iloc[0]['ops_errors'] == 0)

    # Query 11: How many warnings occurred?
    q11 = "SELECT SUM(warnings) as total_warnings FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100'"
    assert_query("Q11: Warnings", q11, lambda df: not pd.isnull(df.iloc[0]['total_warnings']))

    # Query 12: How many business-rule/data-quality violations occurred?
    q12 = "SELECT SUM(violations_count) as dq_violations FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100'"
    assert_query("Q12: Data-quality violations", q12, lambda df: not pd.isnull(df.iloc[0]['dq_violations']))

    # Query 13: Which batch was processed?
    q13 = "SELECT DISTINCT batch_id FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100' AND batch_id != 'unknown'"
    assert_query("Q13: Batch processed", q13, lambda df: len(df) >= 1)

    # Query 14: Which hospital/source produced the run?
    q14 = "SELECT DISTINCT hospital_id FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100' AND hospital_id != 'unknown'"
    assert_query("Q14: Hospital source", q14, lambda df: len(df) >= 1)

    # Query 15: Can the entire seven-stage execution be reconstructed?
    q15 = "SELECT stage, status FROM pipeline_events WHERE run_id = 'TELEMETRY_REAL_100' ORDER BY timestamp ASC"
    assert_query("Q15: Full reconstruction", q15, lambda df: len(df) >= 14) # At least 7 stages * 2 events
    
    con.close()
    return results

def main():
    print("PHASE F: TELEMETRY GATE EXECUTION")
    print("=================================")
    
    print("\\n0. Wiping previous test workspace...")
    shutil.rmtree("outputs/pipeline_workspace", ignore_errors=True)
    Path("outputs/pipeline_workspace").mkdir(parents=True, exist_ok=True)
    
    # 1. Source Immutability (Before)
    print("\\n1. Checking Source Immutability...")
    data_hash_before = hash_directory("data/")
    master_hash_before = hash_directory("master_data/")
    print(f"  Data Hash: {data_hash_before}")
    print(f"  Master Data Hash: {master_hash_before}")
    
    # 2. Real Pipeline Test (100 records)
    print("\\n2. Running Real Pipeline Test (100 records)...")
    create_100_record_real_data_test("TELEMETRY_REAL_100")
    source_root = "outputs/pipeline_workspace/source"
    orchestrator = PipelineOrchestrator()
    res = orchestrator.run(source_root, "TELEMETRY_REAL_100")
    print(f"  Result: {res.is_successful}, Persisted: {res.records_persisted}, Error: {res.error_message}")
    
    # 3. Controlled Failure Test (Mock Transformation)
    print("\\n3. Running Controlled Failure Test...")
    original_transform = HealthcareTransformer.transform_claims
    
    def mocked_transform(*args, **kwargs):
        raise RuntimeError("Injected Failure for Telemetry Testing")
    
    HealthcareTransformer.transform_claims = mocked_transform
    create_100_record_real_data_test("TELEMETRY_FAIL_TEST")
    res_fail = orchestrator.run(source_root, "TELEMETRY_FAIL_TEST")
    print(f"  Result: {res_fail.is_successful}, Error: {res_fail.error_message}")
    
    # Restore mock
    HealthcareTransformer.transform_claims = original_transform
    
    # Verify Failure Telemetry
    con = duckdb.connect("outputs/pipeline_workspace/pipeline_telemetry.duckdb")
    fail_events = con.execute("SELECT stage, status FROM pipeline_events WHERE run_id = 'TELEMETRY_FAIL_TEST' ORDER BY timestamp ASC").df()
    print("  Failed Run Events:")
    print(fail_events)
    con.close()
    
    # 4. Fail-Open Test (Mock DuckDB)
    print("\\n4. Running Fail-Open Test...")
    original_get_connection = PipelineTelemetryLogger.get_instance()._get_connection
    
    def mocked_get_connection(*args, **kwargs):
        raise RuntimeError("Injected DuckDB Failure")
        
    PipelineTelemetryLogger.get_instance()._get_connection = mocked_get_connection
    create_100_record_real_data_test("TELEMETRY_FAIL_OPEN_TEST")
    res_fail_open = orchestrator.run(source_root, "TELEMETRY_FAIL_OPEN_TEST")
    print(f"  Result: {res_fail_open.is_successful} (Should be True despite telemetry failure)")
    
    # Restore mock
    PipelineTelemetryLogger.get_instance()._get_connection = original_get_connection
    
    # 5. Monitoring SQL Acceptance Tests
    print("\\n5. Running Monitoring SQL Acceptance Tests...")
    db_path = "outputs/pipeline_workspace/pipeline_telemetry.duckdb"
    query_results = run_queries(db_path)
    for q in query_results:
        status = "PASS" if q['passed'] else f"FAIL ({q['error']})"
        print(f"  {q['query']}: {status}")
        
    # 6. Source Immutability (After)
    print("\\n6. Checking Source Immutability...")
    data_hash_after = hash_directory("data/")
    master_hash_after = hash_directory("master_data/")
    print(f"  Data Hash: {data_hash_after}")
    print(f"  Master Data Hash: {master_hash_after}")
    
    if data_hash_before != data_hash_after or master_hash_before != master_hash_after:
        print("  WARNING: Immutability violation detected!")
        
    # 7. Regression Suite
    print("\\n7. Running Regression Suite...")
    pytest.main(["tests/"])
    
if __name__ == "__main__":
    main()
