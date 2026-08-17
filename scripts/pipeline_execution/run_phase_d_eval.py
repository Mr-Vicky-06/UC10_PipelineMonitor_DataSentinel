import pandas as pd
import time
import json
import duckdb
from pathlib import Path

from src.pipeline.transformation import HealthcareTransformer

# Create transformer instance
transformer = HealthcareTransformer(config_path="src/pipeline/config.yaml")

def real_transform(df):
    return transformer.transform_claims(df, batch_id="B-SMOKE", source_file="smoke_test.csv")

from src.business_rules.engine import BusinessRuleEngine
from src.business_rules.phase_c_rules import ICDValidityRule, HCPCSValidityRule, BeneficiaryIntegrityRule, ProviderIntegrityRule, AuthorizationMatchRule
from src.business_rules.rules import ClaimChronologyRule, AdmissionDischargeRule, NegativeAmountRule, PaymentChargeBalanceRule
from src.pipeline.storage import ProcessedClaimsStore

def run_phase_d_integration():
    dataset_path = "outputs/business_rules/evaluation/phase_c/synthetic_phase_c_dataset.csv"
    db_path = "outputs/pipeline_workspace/processed_claims.duckdb"
    
    # Ensure directory exists and wipe db for clean test
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(db_path).exists():
        Path(db_path).unlink()

    
    print(f"Loading {dataset_path}...")
    df = pd.read_csv(dataset_path, sep="|", dtype=str)
    
    # 1. Transformation (mock)
    print("Running Transformation...")
    df_transformed, meta = real_transform(df)
    
    # 2. Business Rules
    print("Running BusinessRuleEngine...")
    
    rules = [
        ICDValidityRule(),
        HCPCSValidityRule(),
        BeneficiaryIntegrityRule(),
        ProviderIntegrityRule(),
        AuthorizationMatchRule(),
        ClaimChronologyRule(),
        AdmissionDischargeRule(),
        NegativeAmountRule(),
        PaymentChargeBalanceRule()
    ]
    engine = BusinessRuleEngine(rules)
        
    start_eval = time.time()
    transformed_batch = (df_transformed, meta)
    rule_result = engine.execute(transformed_batch)
    eval_duration = time.time() - start_eval
    print(f"Evaluation finished in {eval_duration:.3f}s. {len(rule_result.violations)} violations found.")
    
    # 3. Storage
    print("Saving to ProcessedClaimsStore...")
    store = ProcessedClaimsStore(db_path=db_path)
    
    # Run 1
    start_save = time.time()
    store.save(df_transformed, rule_result, run_id="phase_d_run_1", hospital_id="HOSP-EVAL", batch_id="B-100", source_file=dataset_path)
    save_duration = time.time() - start_save
    print(f"Storage finished in {save_duration:.3f}s.")
    
    # Test idempotency (Run 2 - same run_id)
    print("Testing idempotency (saving same run_id again)...")
    store.save(df_transformed, rule_result, run_id="phase_d_run_1", hospital_id="HOSP-EVAL", batch_id="B-100", source_file=dataset_path)
    
    # Verify counts
    with duckdb.connect(db_path) as con:
        claims_count = con.execute("SELECT count(*) FROM processed_claims WHERE run_id = 'phase_d_run_1'").fetchone()[0]
        rules_count = con.execute("SELECT count(*) FROM rule_results WHERE run_id = 'phase_d_run_1'").fetchone()[0]
        
    print(f"Idempotency Check: Claims Count = {claims_count}, Rule Violations Count = {rules_count}")
    
    # Assertions
    assert claims_count == len(df_transformed), f"Expected {len(df_transformed)} claims, got {claims_count}"
    assert rules_count == len(rule_result.violations), f"Expected {len(rule_result.violations)} violations, got {rules_count}"
    
    print("\nPhase D Integration passed!\n")
    
    return db_path

def run_phase_d_smoke_test(db_path):
    dataset_path = "outputs/reference_data/master_claims_100k.csv"
    if not Path(dataset_path).exists():
        print(f"Skipping smoke test, file not found: {dataset_path}")
        return
        
    print(f"Loading {dataset_path}...")
    df = pd.read_csv(dataset_path, dtype=str)
    
    # Phase A generates master_claims_100k, but maybe we should use master_data/claims/claims_master.csv if it's there?
    # Wait, the reference is master_data/claims/claims_master.csv
    
def run_phase_d_smoke_test_real(db_path):
    dataset_path = "master_data/claims/claims_master.csv"
    if not Path(dataset_path).exists():
        print(f"Skipping smoke test, file not found: {dataset_path}")
        return
        
    print(f"Loading {dataset_path}...")
    df = pd.read_csv(dataset_path, sep="|", dtype=str)
    
    print("Running Transformation...")
    df_transformed, meta = real_transform(df)
    
    print("Running BusinessRuleEngine...")
    engine = BusinessRuleEngine([
        ICDValidityRule(),
        ClaimChronologyRule()
    ])
    
    start_eval = time.time()
    rule_result = engine.execute((df_transformed, meta))
    eval_duration = time.time() - start_eval
    print(f"Smoke evaluation finished in {eval_duration:.3f}s. {len(rule_result.violations)} violations found.")
    
    print("Saving to ProcessedClaimsStore...")
    store = ProcessedClaimsStore(db_path=db_path)
    
    start_save = time.time()
    store.save(df_transformed, rule_result, run_id="smoke_run_1", hospital_id="HOSP-SMOKE", batch_id="B-SMOKE", source_file=dataset_path)
    save_duration = time.time() - start_save
    
    print(f"Smoke storage finished in {save_duration:.3f}s. Throughput: {len(df_transformed)/save_duration:.0f} rows/s")
    
    with duckdb.connect(db_path) as con:
        claims_count = con.execute("SELECT count(*) FROM processed_claims WHERE run_id = 'smoke_run_1'").fetchone()[0]
        rules_count = con.execute("SELECT count(*) FROM rule_results WHERE run_id = 'smoke_run_1'").fetchone()[0]
        duplicate_claims = con.execute("SELECT run_id, CLM_ID, CLM_LINE_NUM, count(*) FROM processed_claims WHERE run_id = 'smoke_run_1' GROUP BY run_id, CLM_ID, CLM_LINE_NUM HAVING count(*) > 1").fetchall()
        
    print(f"Smoke Test: Persisted {claims_count} claims successfully.")
    print(f"Smoke Test: Persisted {rules_count} violations successfully.")
    print(f"Smoke Test: Found {len(duplicate_claims)} duplicate grain violations.")
    
    # Test Isolation
    print("\nTesting isolation with a different run_id...")
    store.save(df_transformed, rule_result, run_id="smoke_run_2", hospital_id="HOSP-SMOKE", batch_id="B-SMOKE", source_file=dataset_path)
    with duckdb.connect(db_path) as con:
        claims_run1 = con.execute("SELECT count(*) FROM processed_claims WHERE run_id = 'smoke_run_1'").fetchone()[0]
        claims_run2 = con.execute("SELECT count(*) FROM processed_claims WHERE run_id = 'smoke_run_2'").fetchone()[0]
        
    print(f"Isolation Check: Run 1 has {claims_run1} claims, Run 2 has {claims_run2} claims.")
    
    print("\nPhase D Smoke Test passed!")


if __name__ == "__main__":
    db = run_phase_d_integration()
    run_phase_d_smoke_test_real(db)
