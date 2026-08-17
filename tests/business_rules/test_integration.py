import pandas as pd
import pytest

from src.pipeline.transformation import HealthcareTransformer
from src.business_rules.engine import BusinessRuleEngine
from src.business_rules.rules import (
    ClaimChronologyRule,
    AdmissionDischargeRule,
    NegativeAmountRule,
    PaymentChargeBalanceRule
)

def test_transformation_to_business_rules_integration():
    # 1. Create dummy input data that represents what Cleaning would output
    df_raw = pd.DataFrame({
        'CLM_ID': ['C1', 'C2', 'C3'],
        'CLM_LINE_NUM': ['1', '2', '1'],
        'BENE_ID': ['B1', 'B1', 'B2'],
        'PRVDR_NUM': ['P1', 'P1', 'P2'],
        # Dates (C1 is valid, C2 is invalid chronology, C3 has missing dates)
        'CLM_FROM_DT': ['2026-01-01', '2026-01-05', ''],
        'CLM_THRU_DT': ['2026-01-05', '2026-01-01', ''],
        'ADMTN_DT': ['2026-01-01', '2026-01-01', '2026-01-01'],
        'NCH_BENE_DSCHRG_DT': ['2026-01-05', '2026-01-05', '2025-12-31'],
        # Amounts
        'CLM_PMT_AMT': ['100.50', '600.00', '-50.00'],
        'CLM_TOT_CHRG_AMT': ['200.00', '100.00', '10.00']
    })
    
    # 2. Run Transformation
    transformer = HealthcareTransformer()
    # Mock the configuration so it knows about our columns
    # Actually HealthcareTransformer will load from configs/transformation_config.yaml
    # We will just call transform_claims. It might coerce some, let's see.
    transformed_batch = transformer.transform_claims(df_raw, source_file="test.csv")
    
    assert isinstance(transformed_batch, tuple)
    assert isinstance(transformed_batch[0], pd.DataFrame)
    
    # 3. Run Business Rule Engine
    rules = [
        ClaimChronologyRule(),
        AdmissionDischargeRule(),
        NegativeAmountRule(),
        PaymentChargeBalanceRule()
    ]
    engine = BusinessRuleEngine(rules)
    
    result = engine.execute(transformed_batch)
    
    # 4. Verify outputs
    assert result.status == "COMPLETED_WITH_VIOLATIONS"
    assert len(result.dataframe) == 3  # Original claim-line count is preserved
    
    # C1 should have 0 FAIL
    c1_fails = [v for v in result.violations if v.clm_id == 'C1' and v.status == 'FAIL']
    assert len(c1_fails) == 0
    
    # C2 should FAIL chronology and payment balance
    c2_fails = [v for v in result.violations if v.clm_id == 'C2' and v.status == 'FAIL']
    assert len(c2_fails) == 2
    assert any(v.rule_id == 'BR-DATE-001' for v in c2_fails)
    assert any(v.rule_id == 'BR-AMT-002' for v in c2_fails)
    
    # C3 should FAIL AdmissionDischarge (2026 > 2025) and NegativeAmount (-50)
    # C3 should be NOT_EVALUATED for Chronology (missing dates)
    c3_fails = [v for v in result.violations if v.clm_id == 'C3' and v.status == 'FAIL']
    assert len(c3_fails) == 2
    assert any(v.rule_id == 'BR-DATE-002' for v in c3_fails)
    assert any(v.rule_id == 'BR-AMT-001' for v in c3_fails)
    
    c3_not_eval = [v for v in result.violations if v.clm_id == 'C3' and v.status == 'NOT_EVALUATED']
    assert any(v.rule_id == 'BR-DATE-001' for v in c3_not_eval)
