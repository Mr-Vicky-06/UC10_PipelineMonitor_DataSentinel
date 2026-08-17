import duckdb
import pandas as pd
import json
import logging
from pathlib import Path
from datetime import datetime

from src.business_rules.models import BusinessRuleResult, BusinessRuleViolation
from src.business_rules.engine import BusinessRuleEngine
from src.business_rules.phase_c_rules import ICDValidityRule
from src.business_rules.rules import ClaimChronologyRule
from src.pipeline.storage import ProcessedClaimsStore

def run_audit():
    db_path = "outputs/pipeline_workspace/processed_claims.duckdb"
    
    print("--- PHASE D FINAL AUDIT ---")
    
    # Check 1: Record counts and grain
    with duckdb.connect(db_path) as con:
        # Processed claims count
        claims_count = con.execute("SELECT count(*) FROM processed_claims").fetchone()[0]
        # rule results count
        rules_count = con.execute("SELECT count(*) FROM rule_results").fetchone()[0]
        
        print(f"Total processed_claims: {claims_count}")
        print(f"Total rule_results: {rules_count}")
        
        # Grain check processed_claims
        dup_claims = con.execute("""
            SELECT run_id, CLM_ID, CLM_LINE_NUM, count(*) as c 
            FROM processed_claims 
            GROUP BY run_id, CLM_ID, CLM_LINE_NUM 
            HAVING count(*) > 1
        """).fetchdf()
        
        # Grain check rule_results
        dup_rules = con.execute("""
            SELECT run_id, CLM_ID, CLM_LINE_NUM, rule_id, count(*) as c 
            FROM rule_results 
            GROUP BY run_id, CLM_ID, CLM_LINE_NUM, rule_id
            HAVING count(*) > 1
        """).fetchdf()
        
        print(f"Duplicate processed_claims grain violations: {len(dup_claims)}")
        print(f"Duplicate rule_results grain violations: {len(dup_rules)}")
        
        # Check 2: Content of rule_results
        status_dist = con.execute("SELECT status, count(*) FROM rule_results GROUP BY status").fetchall()
        print(f"Rule result status distribution:")
        for status, count in status_dist:
            print(f"  {status}: {count}")
            
    # The 100,000 rule_results mystery.
    # We saw in the smoke test log: "100000 violations found." and "Persisted 100000 claims successfully."
    # Let's see what status is there.
    
    # Check 3: Transaction Rollback Verification
    print("\nTesting Transaction Rollback...")
    store = ProcessedClaimsStore(db_path=db_path)
    # mock a failure during save
    df_fake = pd.DataFrame([{"CLM_ID": "FAIL_TEST", "CLM_LINE_NUM": "1", "VAL": "v1"}])
    res_fake = BusinessRuleResult(df_fake, [], "2023-01-01", {}, "SUCCESS")
    
    # We'll monkeypatch duckdb connection to raise an exception after delete, before insert
    class MockException(Exception): pass
    
    original_get_connection = store._get_connection
    
    class FakeConnection:
        def __init__(self, real_con):
            self.real_con = real_con
            self.query_count = 0
            
        def __enter__(self):
            self.real_con.__enter__()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.real_con.__exit__(exc_type, exc_val, exc_tb)
            
        def execute(self, query, params=None):
            if "INSERT INTO processed_claims" in query:
                raise MockException("Simulated failure during INSERT")
            if params:
                return self.real_con.execute(query, params)
            return self.real_con.execute(query)
            
    try:
        def fake_get_connection():
            return FakeConnection(duckdb.connect(db_path))
        
        store._get_connection = fake_get_connection
        try:
            store.save(df_fake, res_fake, "rollback_run", "H-1", "B-1")
            print("  FAIL: Expected an exception!")
        except MockException:
            pass
    finally:
        store._get_connection = original_get_connection
        
    with duckdb.connect(db_path) as con:
        fail_claims = con.execute("SELECT count(*) FROM processed_claims WHERE run_id = 'rollback_run'").fetchone()[0]
        print(f"  Rollback claims count for 'rollback_run': {fail_claims} (Expected 0)")

    # Check 4: Reopen Verification
    print("\nTesting Database Reopen Persistence...")
    con1 = duckdb.connect(db_path)
    count1 = con1.execute("SELECT count(*) FROM processed_claims").fetchone()[0]
    con1.close()
    
    con2 = duckdb.connect(db_path)
    count2 = con2.execute("SELECT count(*) FROM processed_claims").fetchone()[0]
    con2.close()
    
    print(f"  Closed and reopened. Count matches: {count1 == count2} ({count2} rows)")

    # Check 5: Data integrity & round-tripping
    print("\nTesting Data Round-tripping...")
    with duckdb.connect(db_path) as con:
        # Get one row from rule_results
        row = con.execute("SELECT field_values FROM rule_results WHERE field_values != '{}' LIMIT 1").fetchone()
        if row:
            parsed = json.loads(row[0])
            print(f"  Successfully parsed field_values JSON: {type(parsed)}")
        else:
            print("  No field_values JSON found to parse.")
            
        # Get one row from processed_claims
        row_claim = con.execute("SELECT transformed_data FROM processed_claims LIMIT 1").fetchone()
        if row_claim:
            parsed = json.loads(row_claim[0])
            print(f"  Successfully parsed transformed_data JSON: {type(parsed)}")
        else:
            print("  No transformed_data JSON found to parse.")
            

if __name__ == "__main__":
    run_audit()
