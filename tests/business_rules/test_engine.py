import pandas as pd
import pytest

from src.business_rules.rules import ClaimChronologyRule, PaymentChargeBalanceRule
from src.business_rules.engine import BusinessRuleEngine

def test_engine_execution():
    rules = [ClaimChronologyRule(), PaymentChargeBalanceRule()]
    engine = BusinessRuleEngine(rules)
    
    df = pd.DataFrame({
        'CLM_ID': ['C1', 'C2'],
        'CLM_LINE_NUM': ['1', '1'],
        'CLM_FROM_DT': ['2026-01-05', '2026-01-01'],
        'CLM_THRU_DT': ['2026-01-01', '2026-01-05'],
        'CLM_PMT_AMT': [500.0, 100.0],
        'CLM_TOT_CHRG_AMT': [100.0, 200.0]
    })
    
    # Simulate transformation tuple
    transformed_batch = (df, {"source": "test", "rows": 2})
    
    result = engine.execute(transformed_batch)
    
    assert result.status == "COMPLETED_WITH_VIOLATIONS"
    assert result.dataframe is df
    
    # C1 fails both Date and Amount
    assert len(result.violations) == 2
    for v in result.violations:
        assert v.clm_id == 'C1'
        assert v.status == "FAIL"

    # Check metrics
    assert result.metrics['claims_processed'] == 2
    assert result.metrics['rules_executed'] == 2
    assert 'BR-DATE-001' in result.metrics['violation_breakdown']
    assert 'BR-AMT-002' in result.metrics['violation_breakdown']
