import os
import sys
import time
import datetime
import hashlib
import pandas as pd
import duckdb
from pathlib import Path
import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.pipeline.orchestrator import PipelineOrchestrator
from src.observability.engine import ObservabilityEngine
from src.observability.repository import ObservabilityRepository
from src.observability.models import FindingCategory, FindingSeverity, ObservabilityStatus

def hash_directory(directory: str) -> str:
    sha256_hash = hashlib.sha256()
    for root, dirs, files in os.walk(directory):
        for names in sorted(files):
            filepath = os.path.join(root, names)
            try:
                with open(filepath, 'rb') as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
            except Exception:
                pass
    return sha256_hash.hexdigest()


def main():
    results = {}
    print("Hashing directories BEFORE tests...")
    results['data_hash_before'] = hash_directory('data/')
    results['master_hash_before'] = hash_directory('master_data/')
    
    # 1. Architecture map is text, we'll write it in the report.
    
    # 2. Identify real DQ data globally
    repo = ObservabilityRepository()
    try:
        all_claims = repo.get_processed_claims("") # passing empty string gets all or we can use duckdb directly
    except:
        pass
    
    print("\n--- 4/5. RUNNING COMPLETE PIPELINE (REAL 1,000-RECORD DATASET) ---")
    run_id = f"OBS_DQ_REAL_1000_{int(time.time())}"
    inpatient_csv = "master_data/claims/claims_master.csv"
    df = pd.read_csv(inpatient_csv).head(1000)
    source_dir = Path("outputs/pipeline_workspace/source")
    hosp_dir = source_dir / run_id / "HOSP_001"
    hosp_dir.mkdir(parents=True, exist_ok=True)
    test_file = hosp_dir / "batch_20260101.csv"
    df.to_csv(test_file, index=False)
    
    orchestrator = PipelineOrchestrator()
    orchestrator.run(
        source_directory=str(source_dir),
        run_id=run_id
    )
    
    print("\n--- 6. SHOW WHAT THE DQ ENGINE PRODUCED ---")
    processed = repo.get_processed_claims(run_id)
    rules = repo.get_rule_results(run_id)
    
    total_claims = len(processed)
    total_violations = len(rules)
    if not rules.empty:
        clean_claims = total_claims - rules['CLM_ID'].nunique()
        print(f"Total Claims: {total_claims}")
        print(f"Total Violations: {total_violations}")
        print(f"Clean Claims: {clean_claims}")
        print("Violations by Rule:")
        print(rules.groupby('rule_id').size())
    else:
        print("No rule violations found.")
        clean_claims = total_claims
        
    results['real_run'] = {
        'total_claims': total_claims,
        'total_violations': total_violations,
        'clean_claims': clean_claims
    }
    
    print("\n--- 7. RUN OBSERVABILITY ENGINE ---")
    engine = ObservabilityEngine(repo)
    obs_res = engine.analyze_run(run_id)
    print(f"Overall Status: {obs_res.overall_status.name}")
    print(f"Operational Errors: {obs_res.operational_errors}")
    for f in obs_res.findings:
        print(f"[{f.category.name}] {f.severity.name}: {f.message}")
        
    results['obs_res_real'] = {
        'status': obs_res.overall_status.name,
        'op_errors': obs_res.operational_errors,
        'findings': len(obs_res.findings)
    }
    
    print("\n--- 8. PROVE DQ != OPERATIONAL FAILURE ---")
    # We create a synthetic test DB to prove this.
    test_dir = Path("outputs/pipeline_workspace/observability_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_telemetry_db = test_dir / "test_telemetry.duckdb"
    test_processed_db = test_dir / "test_claims.duckdb"
    test_observability_db = test_dir / "test_observability.duckdb"
    
    if test_telemetry_db.exists(): test_telemetry_db.unlink()
    if test_processed_db.exists(): test_processed_db.unlink()
    if test_observability_db.exists(): test_observability_db.unlink()
    
    with duckdb.connect(str(test_telemetry_db)) as con:
        con.execute("CREATE TABLE pipeline_events (event_id VARCHAR, correlation_id VARCHAR, timestamp TIMESTAMP, run_id VARCHAR, hospital_id VARCHAR, batch_id VARCHAR, source_file VARCHAR, service_date VARCHAR, stage VARCHAR, status VARCHAR, duration_ms BIGINT, records_in BIGINT, records_out BIGINT, records_failed BIGINT, records_rejected BIGINT, records_skipped BIGINT, records_corrected BIGINT, violations_count BIGINT, errors BIGINT, warnings BIGINT, message VARCHAR, error_type VARCHAR, error_message VARCHAR)")
    with duckdb.connect(str(test_processed_db)) as con:
        con.execute("CREATE TABLE processed_claims (run_id VARCHAR, CLM_ID VARCHAR, CLM_LINE_NUM VARCHAR, BENE_ID VARCHAR, PRVDR_NUM VARCHAR, HCPCS_CD VARCHAR, CLM_FROM_DT VARCHAR, CLM_PMT_AMT DOUBLE)")
        con.execute("CREATE TABLE rule_results (run_id VARCHAR, CLM_ID VARCHAR, CLM_LINE_NUM VARCHAR, rule_id VARCHAR, rule_name VARCHAR, status VARCHAR, severity VARCHAR, message VARCHAR, field_values JSON, evaluation_timestamp TIMESTAMP)")
        
    test_repo = ObservabilityRepository(str(test_telemetry_db), str(test_processed_db), str(test_observability_db))
    test_engine = ObservabilityEngine(test_repo)
    
    def insert_synthetic_run(r_id, records=1000, missing=None, fail=None, dq_fails=0):
        stages = ["LANDING", "INGESTION", "VALIDATION", "CLEANING", "TRANSFORMATION", "BUSINESS_RULES", "STORAGE"]
        events = []
        ts = datetime.datetime.utcnow()
        for stage in stages:
            if stage == missing: continue
            dur = 200
            st = 'COMPLETED'
            if stage == fail: st = 'FAILED'
            events.append((f"e1_{stage}", "c1", ts, r_id, "H1", "b1", "file.csv", None, stage, "STARTED", 0, records, records, 0, 0, 0, 0, 0, 0, 0, None, None, None))
            ts += datetime.timedelta(milliseconds=dur)
            events.append((f"e2_{stage}", "c1", ts, r_id, "H1", "b1", "file.csv", None, stage, st, dur, records, records, 0, 0, 0, 0, 0, 1 if st=='FAILED' else 0, 0, None, None, "Error" if st=='FAILED' else None))
            if st == 'FAILED': break
            
        with duckdb.connect(str(test_telemetry_db)) as con:
            con.executemany("INSERT INTO pipeline_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", events)
            
        claims = []
        for i in range(records):
            claims.append((r_id, f"C{i}", "1", "B1", "P1", "H1", "2023-01-01", 100.0))
        with duckdb.connect(str(test_processed_db)) as con:
            con.executemany("INSERT INTO processed_claims VALUES (?,?,?,?,?,?,?,?)", claims)
            
        dq = []
        for i in range(dq_fails):
            dq.append((r_id, f"C{i}", "1", "BR-REF-003", "Rule Name", "FAIL", "CRITICAL", "Message", None, ts))
        if dq:
            with duckdb.connect(str(test_processed_db)) as con:
                con.executemany("INSERT INTO rule_results VALUES (?,?,?,?,?,?,?,?,?,?)", dq)
                
    # Generate baseline
    for i in range(5):
        insert_synthetic_run(f"BASE_{i}", dq_fails=10)
        
    insert_synthetic_run("RUN_DQ_SPIKE", dq_fails=500)
    res_dq = test_engine.analyze_run("RUN_DQ_SPIKE")
    print(f"\nDQ Spike - Operational Status: {res_dq.overall_status.name}")
    for f in res_dq.findings:
        if f.category.name == 'DATA_QUALITY':
            print(f"Found DQ Spike: {f.message}")
            
    insert_synthetic_run("RUN_OP_FAIL", fail="TRANSFORMATION")
    res_op = test_engine.analyze_run("RUN_OP_FAIL")
    print(f"\nOp Fail - Operational Status: {res_op.overall_status.name}")
    
    insert_synthetic_run("RUN_HEALTHY")
    res_healthy = test_engine.analyze_run("RUN_HEALTHY")
    print(f"\nHealthy - Operational Status: {res_healthy.overall_status.name}")
    
    # 13. IDEMPOTENCY & DB CHECK
    test_engine.analyze_run("RUN_HEALTHY")
    with duckdb.connect(str(test_observability_db)) as con:
        run_counts = con.execute("SELECT COUNT(*) FROM observability_runs WHERE run_id='RUN_HEALTHY'").fetchone()[0]
        print(f"\nIdempotency check: {run_counts} records for RUN_HEALTHY")
        
    print("Hashing directories AFTER tests...")
    results['data_hash_after'] = hash_directory('data/')
    results['master_hash_after'] = hash_directory('master_data/')
    
if __name__ == '__main__':
    main()
