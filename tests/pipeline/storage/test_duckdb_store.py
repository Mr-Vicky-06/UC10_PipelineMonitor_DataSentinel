import pytest
import pandas as pd
import duckdb
import os
import json
from pathlib import Path
from src.pipeline.storage.duckdb_store import ProcessedClaimsStore
from src.business_rules.models import BusinessRuleResult, BusinessRuleViolation

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_store.duckdb"
    return str(db_path)

def test_empty_dataframe(temp_db):
    store = ProcessedClaimsStore(db_path=temp_db)
    df = pd.DataFrame()
    res = BusinessRuleResult(df, [], "2023-01-01T00:00:00", {}, "SUCCESS")
    store.save(df, res, "run_1", "hosp_1", "batch_1")
    
    with duckdb.connect(temp_db) as con:
        claims_count = con.execute("SELECT count(*) FROM processed_claims").fetchone()[0]
        assert claims_count == 0

def test_single_claim_line(temp_db):
    store = ProcessedClaimsStore(db_path=temp_db)
    df = pd.DataFrame([{
        "CLM_ID": "C1",
        "CLM_LINE_NUM": "1",
        "BENE_ID": "B1",
        "PRVDR_NUM": "P1",
        "HCPCS_CD": "H1",
        "CLM_FROM_DT": "2023-01-01",
        "EXTRA_FIELD": "Extra"
    }])
    
    violation = BusinessRuleViolation("BR1", "Rule1", "C1", "1", "ERROR", "FAIL", "Failed", {"field": "val"})
    res = BusinessRuleResult(df, [violation], "2023-01-01T00:00:00", {}, "SUCCESS")
    
    store.save(df, res, "run_1", "hosp_1", "batch_1")
    
    with duckdb.connect(temp_db) as con:
        claims = con.execute("SELECT * FROM processed_claims").fetchdf()
        assert len(claims) == 1
        assert claims.iloc[0]['CLM_ID'] == "C1"
        transformed_json = json.loads(claims.iloc[0]['transformed_data'])
        assert transformed_json['EXTRA_FIELD'] == "Extra"
        
        rules = con.execute("SELECT * FROM rule_results").fetchdf()
        assert len(rules) == 1
        assert rules.iloc[0]['rule_id'] == "BR1"
        assert rules.iloc[0]['run_id'] == "run_1"

def test_multiple_claim_lines_duplicate_clm_id(temp_db):
    store = ProcessedClaimsStore(db_path=temp_db)
    df = pd.DataFrame([
        {"CLM_ID": "C1", "CLM_LINE_NUM": "1"},
        {"CLM_ID": "C1", "CLM_LINE_NUM": "2"},
        {"CLM_ID": "C2", "CLM_LINE_NUM": "1"}
    ])
    res = BusinessRuleResult(df, [], "2023-01-01T00:00:00", {}, "SUCCESS")
    store.save(df, res, "run_1", "hosp_1", "batch_1")
    
    with duckdb.connect(temp_db) as con:
        claims = con.execute("SELECT CLM_ID, CLM_LINE_NUM FROM processed_claims").fetchdf()
        assert len(claims) == 3

def test_multiple_violations_one_claim(temp_db):
    store = ProcessedClaimsStore(db_path=temp_db)
    df = pd.DataFrame([{"CLM_ID": "C1", "CLM_LINE_NUM": "1"}])
    v1 = BusinessRuleViolation("BR1", "Rule1", "C1", "1", "ERROR", "FAIL", "M1", {})
    v2 = BusinessRuleViolation("BR2", "Rule2", "C1", "1", "INFO", "PASS", "M2", {})
    res = BusinessRuleResult(df, [v1, v2], "2023-01-01", {}, "SUCCESS")
    store.save(df, res, "run_1", "hosp_1", "batch_1")
    
    with duckdb.connect(temp_db) as con:
        rules = con.execute("SELECT rule_id FROM rule_results").fetchdf()
        assert set(rules['rule_id']) == {"BR1", "BR2"}

def test_idempotency_same_run(temp_db):
    store = ProcessedClaimsStore(db_path=temp_db)
    df = pd.DataFrame([{"CLM_ID": "C1", "CLM_LINE_NUM": "1", "VAL": "v1"}])
    res = BusinessRuleResult(df, [], "2023-01-01", {}, "SUCCESS")
    
    # Run 1 initial
    store.save(df, res, "run_1", "hosp_1", "batch_1")
    
    # Run 1 repeat (modified data)
    df2 = pd.DataFrame([{"CLM_ID": "C1", "CLM_LINE_NUM": "1", "VAL": "v2"}])
    res2 = BusinessRuleResult(df2, [], "2023-01-02", {}, "SUCCESS")
    store.save(df2, res2, "run_1", "hosp_1", "batch_1")
    
    with duckdb.connect(temp_db) as con:
        claims = con.execute("SELECT transformed_data FROM processed_claims").fetchdf()
        assert len(claims) == 1
        assert json.loads(claims.iloc[0]['transformed_data'])['VAL'] == "v2"

def test_isolation_different_runs(temp_db):
    store = ProcessedClaimsStore(db_path=temp_db)
    df = pd.DataFrame([{"CLM_ID": "C1", "CLM_LINE_NUM": "1"}])
    res = BusinessRuleResult(df, [], "2023-01-01", {}, "SUCCESS")
    
    # Run 1
    store.save(df, res, "run_1", "hosp_1", "batch_1")
    
    # Run 2 (should not overwrite run_1)
    store.save(df, res, "run_2", "hosp_1", "batch_1")
    
    with duckdb.connect(temp_db) as con:
        claims = con.execute("SELECT run_id FROM processed_claims").fetchdf()
        assert len(claims) == 2
        assert set(claims['run_id']) == {"run_1", "run_2"}

def test_json_authorization_metadata(temp_db):
    store = ProcessedClaimsStore(db_path=temp_db)
    df = pd.DataFrame([{"CLM_ID": "C1", "CLM_LINE_NUM": "1"}])
    v = BusinessRuleViolation("BR1", "Rule1", "C1", "1", "INFO", "AMBIGUOUS_AUTH", "Msg", 
                              {"candidate_auth_ids": ["A1", "A2"]})
    res = BusinessRuleResult(df, [v], "2023-01-01", {}, "SUCCESS")
    store.save(df, res, "run_1", "hosp_1", "batch_1")
    
    with duckdb.connect(temp_db) as con:
        rules = con.execute("SELECT field_values FROM rule_results").fetchdf()
        fields = json.loads(rules.iloc[0]['field_values'])
        assert "A1" in fields["candidate_auth_ids"]

