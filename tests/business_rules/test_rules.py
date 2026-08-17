import pandas as pd
import pytest

from src.business_rules.rules import (
    ClaimChronologyRule,
    AdmissionDischargeRule,
    NegativeAmountRule,
    PaymentChargeBalanceRule
)
from src.business_rules.models import RuleStatus

def test_claim_chronology_rule():
    rule = ClaimChronologyRule()
    
    # 2026-01-01 <= 2026-01-05 (PASS)
    # 2026-01-05 <= 2026-01-01 (FAIL)
    # Boundary: 2026-01-01 <= 2026-01-01 (PASS)
    # Missing: missing CLM_FROM_DT (NOT_EVALUATED)
    
    df = pd.DataFrame({
        'CLM_ID': ['C1', 'C2', 'C3', 'C4'],
        'CLM_LINE_NUM': ['1', '1', '1', '1'],
        'CLM_FROM_DT': ['2026-01-01', '2026-01-05', '2026-01-01', None],
        'CLM_THRU_DT': ['2026-01-05', '2026-01-01', '2026-01-01', '2026-01-05']
    })
    
    violations = rule.evaluate(df)
    
    # C1: PASS -> no violation record
    # C2: FAIL
    # C3: PASS -> no violation record
    # C4: NOT_EVALUATED
    
    assert len(violations) == 2
    
    fail_v = next(v for v in violations if v.clm_id == 'C2')
    assert fail_v.status == RuleStatus.FAIL.value
    
    missing_v = next(v for v in violations if v.clm_id == 'C4')
    assert missing_v.status == RuleStatus.NOT_EVALUATED.value

def test_admission_discharge_rule():
    rule = AdmissionDischargeRule()
    
    df = pd.DataFrame({
        'CLM_ID': ['C1', 'C2', 'C3'],
        'CLM_LINE_NUM': ['1', '1', '1'],
        'CLM_ADMSN_DT': ['2026-01-01', '2026-01-05', None],
        'NCH_BENE_DSCHRG_DT': ['2026-01-05', '2026-01-01', '2026-01-05']
    })
    
    violations = rule.evaluate(df)
    
    assert len(violations) == 2
    
    fail_v = next(v for v in violations if v.clm_id == 'C2')
    assert fail_v.status == RuleStatus.FAIL.value
    
    missing_v = next(v for v in violations if v.clm_id == 'C3')
    assert missing_v.status == RuleStatus.NOT_EVALUATED.value

def test_negative_amount_rule():
    rule = NegativeAmountRule()
    
    df = pd.DataFrame({
        'CLM_ID': ['C1', 'C2', 'C3', 'C4'],
        'CLM_LINE_NUM': ['1', '1', '1', '1'],
        'CLM_PMT_AMT': [100.0, -50.0, 0.0, None],
        'CLM_TOT_CHRG_AMT': [200.0, 100.0, -10.0, None]
    })
    
    violations = rule.evaluate(df)
    
    # C1: PASS for both
    # C2: FAIL for PMT, PASS for CHRG
    # C3: PASS for PMT, FAIL for CHRG
    # C4: NOT_EVALUATED for both (2 records)
    
    assert len(violations) == 4
    
    fails = [v for v in violations if v.status == RuleStatus.FAIL.value]
    assert len(fails) == 2
    
    not_evals = [v for v in violations if v.status == RuleStatus.NOT_EVALUATED.value]
    assert len(not_evals) == 2

def test_payment_charge_balance_rule():
    rule = PaymentChargeBalanceRule()
    
    df = pd.DataFrame({
        'CLM_ID': ['C1', 'C2', 'C3', 'C4'],
        'CLM_LINE_NUM': ['1', '1', '1', '1'],
        'CLM_PMT_AMT': [100.0, 500.0, 500.0, None],
        'CLM_TOT_CHRG_AMT': [200.0, 100.0, 500.0, 100.0]
    })
    
    violations = rule.evaluate(df)
    
    # C1: PASS (100 <= 200)
    # C2: FAIL (500 > 100)
    # C3: PASS (boundary 500 <= 500)
    # C4: NOT_EVALUATED
    
    assert len(violations) == 2
    
    fail_v = next(v for v in violations if v.clm_id == 'C2')
    assert fail_v.status == RuleStatus.FAIL.value
    
    missing_v = next(v for v in violations if v.clm_id == 'C4')
    assert missing_v.status == RuleStatus.NOT_EVALUATED.value

def test_multiple_violations():
    rule1 = ClaimChronologyRule()
    rule2 = PaymentChargeBalanceRule()
    
    df = pd.DataFrame({
        'CLM_ID': ['C1'],
        'CLM_LINE_NUM': ['1'],
        'CLM_FROM_DT': ['2026-01-05'],
        'CLM_THRU_DT': ['2026-01-01'],
        'CLM_PMT_AMT': [500.0],
        'CLM_TOT_CHRG_AMT': [100.0]
    })
    
    v1 = rule1.evaluate(df)
    v2 = rule2.evaluate(df)
    
    assert len(v1) == 1
    assert len(v2) == 1
    assert v1[0].status == RuleStatus.FAIL.value
    assert v2[0].status == RuleStatus.FAIL.value
