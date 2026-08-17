import os
import sys
import time
import datetime
import hashlib
import pandas as pd
import duckdb
import shutil
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.pipeline.orchestrator import PipelineOrchestrator
from src.observability.engine import ObservabilityEngine
from src.observability.repository import ObservabilityRepository
from src.observability.models import ObservabilityStatus, FindingSeverity, FindingCategory

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
    data_hash_before = hash_directory('data/')
    master_hash_before = hash_directory('master_data/')
    results['data_hash_before'] = data_hash_before
    results['master_hash_before'] = master_hash_before
    
    # 3. REAL 1,000-RECORD TEST
    print("\n--- 3. REAL 1,000-RECORD TEST ---")
    run_id = f"OBS_REAL_1000_{int(time.time())}"
    
    # We need exactly 1000 records.
    inpatient_csv = "master_data/claims/claims_master.csv"
    df = pd.read_csv(inpatient_csv)
    df_1000 = df.head(1000)
    
    # Save to a temp file in landing to be ingested
    landing_dir = Path("outputs/pipeline_workspace/landing/OBS_REAL_TEST/HOSP_001")
    landing_dir.mkdir(parents=True, exist_ok=True)
    test_file = landing_dir / "batch_1000.csv"
    df_1000.to_csv(test_file, index=False)
    
    start_time = time.time()
    orchestrator = PipelineOrchestrator()
    result = orchestrator.run_pipeline(
        hospital_id="HOSP_001",
        batch_id="batch_1000",
        file_path=str(test_file),
        run_id=run_id
    )
    real_duration = (time.time() - start_time) * 1000
    results['real_pipeline_duration_ms'] = real_duration
    
    # 4 & 5 VERIFY REAL TELEMETRY & PERSISTENCE
    print("\n--- 4/5. VERIFY REAL TELEMETRY & PERSISTENCE ---")
    repo = ObservabilityRepository()
    telemetry = repo.get_telemetry_events(run_id)
    processed = repo.get_processed_claims(run_id)
    rules = repo.get_rule_results(run_id)
    
    print(f"Telemetry stages found: {telemetry['stage'].unique()}")
    print(f"Processed Claims count: {len(processed)}")
    print(f"Rule violations count: {len(rules)}")
    results['real_telemetry_count'] = len(telemetry)
    results['real_processed_count'] = len(processed)
    
    # 6. RUN OBSERVABILITY ENGINE
    print("\n--- 6. RUN OBSERVABILITY ENGINE ON REAL RUN ---")
    engine = ObservabilityEngine(repo)
    obs_start = time.time()
    obs_res = engine.analyze_run(run_id)
    obs_duration = (time.time() - obs_start) * 1000
    results['real_obs_duration_ms'] = obs_duration
    print(f"Real run observability status: {obs_res.overall_status.name}")
    results['real_obs_status'] = obs_res.overall_status.name
    
    # 8. SYNTHETIC OBSERVABILITY TEST DATA
    print("\n--- 8-19. SYNTHETIC ADVERSARIAL TESTS ---")
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
        con.execute("CREATE TABLE rule_results (rule_id VARCHAR, run_id VARCHAR, status VARCHAR)")
        
    # Create historical runs
    test_repo = ObservabilityRepository(str(test_telemetry_db), str(test_processed_db), str(test_observability_db))
    test_engine = ObservabilityEngine(test_repo)
    
    def insert_synthetic_run(r_id, records=1000, duration_mult=1.0, missing=None, fail=None, schema_drift=False, null_spike=False, dq_spike=False):
        stages = ["LANDING", "INGESTION", "VALIDATION", "CLEANING", "TRANSFORMATION", "BUSINESS_RULES", "STORAGE"]
        events = []
        ts = datetime.datetime.utcnow()
        for stage in stages:
            if stage == missing: continue
            dur = int(200 * duration_mult)
            st = 'COMPLETED'
            if stage == fail: st = 'FAILED'
            events.append((f"e1_{stage}", "c1", ts, r_id, "H1", "b1", "file.csv", None, stage, "STARTED", 0, records, records, 0, 0, 0, 0, 0, 0, 0, None, None, None))
            ts += datetime.timedelta(milliseconds=dur)
            events.append((f"e2_{stage}", "c1", ts, r_id, "H1", "b1", "file.csv", None, stage, st, dur, records, records, 0, 0, 0, 0, 0, 1 if st=='FAILED' else 0, 0, None, None, "Error" if st=='FAILED' else None))
            if st == 'FAILED': break
            
        with duckdb.connect(str(test_telemetry_db)) as con:
            con.executemany("INSERT INTO pipeline_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", events)
            
        # Processed Claims
        claims = []
        for i in range(records):
            bene_id = "BENE1" if not null_spike else (None if i < records*0.3 else "BENE1")
            claims.append((r_id, f"C{i}", "1", bene_id, "P1", "H1", "2023-01-01", 100.0))
            
        with duckdb.connect(str(test_processed_db)) as con:
            if schema_drift:
                # create new table with unexpected field
                try:
                    con.execute("ALTER TABLE processed_claims ADD COLUMN UNEXPECTED_FIELD VARCHAR")
                except:
                    pass
                con.executemany("INSERT INTO processed_claims VALUES (?,?,?,?,?,?,?,?, 'NEW_VAL')", [c + ('NEW_VAL',) for c in claims])
            else:
                con.executemany("INSERT INTO processed_claims (run_id, CLM_ID, CLM_LINE_NUM, BENE_ID, PRVDR_NUM, HCPCS_CD, CLM_FROM_DT, CLM_PMT_AMT) VALUES (?,?,?,?,?,?,?,?)", claims)
                
        # DQ
        dq = []
        dq_count = 50 if not dq_spike else 500
        for i in range(dq_count):
            dq.append(("R1", r_id, "FAIL"))
        with duckdb.connect(str(test_processed_db)) as con:
            con.executemany("INSERT INTO rule_results VALUES (?,?,?)", dq)
            
    print("Generating 30 baselines...")
    synth_start = time.time()
    for i in range(30):
        insert_synthetic_run(f"RUN_BASELINE_{i:03d}")
    results['synth_baseline_duration_ms'] = (time.time() - synth_start) * 1000
    
    # SCENARIOS
    scenarios = {
        "HEALTHY": lambda: insert_synthetic_run("RUN_HEALTHY"),
        "VOLUME_DROP": lambda: insert_synthetic_run("RUN_VOLUME_DROP", records=600),
        "LATENCY_SPIKE": lambda: insert_synthetic_run("RUN_LATENCY_SPIKE", duration_mult=4.0),
        "MISSING_STAGE": lambda: insert_synthetic_run("RUN_MISSING_STAGE", missing="TRANSFORMATION"),
        "OPERATIONAL_FAILURE": lambda: insert_synthetic_run("RUN_OPERATIONAL_FAILURE", fail="BUSINESS_RULES"),
        "SCHEMA_DRIFT": lambda: insert_synthetic_run("RUN_SCHEMA_DRIFT", schema_drift=True),
        "NULL_SPIKE": lambda: insert_synthetic_run("RUN_NULL_SPIKE", null_spike=True),
        "DQ_SPIKE": lambda: insert_synthetic_run("RUN_DQ_SPIKE", dq_spike=True),
        "COMBINED": lambda: insert_synthetic_run("RUN_COMBINED", records=500, duration_mult=5.0, null_spike=True)
    }
    
    scenario_results = {}
    for name, func in scenarios.items():
        func()
        res = test_engine.analyze_run(f"RUN_{name}")
        scenario_results[name] = {
            'status': res.overall_status.name,
            'findings': [(f.category.name, f.severity.name, f.deviation_pct) for f in res.findings]
        }
        
    results['scenarios'] = scenario_results
    
    # 23. IDEMPOTENCY & REOPEN
    test_engine.analyze_run("RUN_HEALTHY")  # Run again
    with duckdb.connect(str(test_observability_db)) as con:
        run_counts = con.execute("SELECT COUNT(*) FROM observability_runs WHERE run_id='RUN_HEALTHY'").fetchone()[0]
        results['idempotency_run_count'] = run_counts
        
    print("Hashing directories AFTER tests...")
    results['data_hash_after'] = hash_directory('data/')
    results['master_hash_after'] = hash_directory('master_data/')
    
    print("\nSUMMARY:")
    import pprint
    pprint.pprint(results)

if __name__ == '__main__':
    main()
