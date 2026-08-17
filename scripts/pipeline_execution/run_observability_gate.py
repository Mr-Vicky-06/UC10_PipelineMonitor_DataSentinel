import os
import sys
import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.observability.engine import ObservabilityEngine
from src.observability.repository import ObservabilityRepository
import duckdb

def main():
    print("\n============================================================")
    print("PHASE G — DATA OBSERVABILITY GATE VALIDATION")
    print("============================================================\n")
    
    repo = ObservabilityRepository()
    # get the latest run
    telemetry = repo.get_telemetry_events()
    if telemetry.empty:
        print("No telemetry available. Please run pipeline first.")
        return
        
    last_run_id = telemetry['run_id'].iloc[-1]
    print(f"Analyzing run: {last_run_id}")
    
    engine = ObservabilityEngine(repo)
    result = engine.analyze_run(last_run_id)
    
    print(f"Overall Status: {result.overall_status.name}")
    print(f"Records Persisted: {result.records_persisted}")
    print(f"Operational Errors: {result.operational_errors}")
    print(f"Slowest Stage: {result.slowest_stage}")
    print(f"Findings Count: {result.finding_count} (CRITICAL: {result.critical_count}, WARNING: {result.warning_count})")
    
    if result.finding_count > 0:
        print("\n--- FINDINGS ---")
        for f in result.findings:
            print(f"[{f.severity.name}] {f.category.name} ({f.stage if f.stage else 'GLOBAL'}): {f.message}")
            
    print("\nValidating SQL Interface...")
    try:
        with duckdb.connect(repo.observability_db_path) as con:
            df = con.execute("SELECT run_id, overall_status, finding_count FROM observability_runs").df()
            print("\nObservability Runs Table:")
            print(df.to_string())
    except Exception as e:
        print(f"SQL query failed: {e}")

if __name__ == '__main__':
    main()
