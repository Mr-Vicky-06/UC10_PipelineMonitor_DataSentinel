"""
Tests for Rule Group C: Financial and Amount Validation Quality Rules.
"""

import unittest
import pandas as pd

from src.data_quality.models import (
    DataQualitySeverity,
    DataQualityStatus,
    FinancialRuleConfig,
)
from src.data_quality.rules.financial import FinancialAmountRule


class TestFinancialRules(unittest.TestCase):
    def setUp(self):
        self.non_negative_config = FinancialRuleConfig(
            id="DQ-FIN-001",
            name="non_negative_payment_amount",
            field="CLM_PMT_AMT",
            allow_negative=False,
            min_value=0.0,
            severity=DataQualitySeverity.ERROR,
        )
        self.range_config = FinancialRuleConfig(
            id="DQ-FIN-002",
            name="bounded_amount_range",
            field="AUTH_AMT",
            allow_negative=False,
            min_value=10.0,
            max_value=50000.0,
            severity=DataQualitySeverity.ERROR,
        )
        self.relational_config = FinancialRuleConfig(
            id="DQ-FIN-004",
            name="payment_within_total_charge",
            payment_field="CLM_PMT_AMT",
            charge_field="CLM_TOT_CHRG_AMT",
            severity=DataQualitySeverity.WARNING,
        )

    def test_09_valid_positive_amount(self):
        """Test 9: Valid positive amounts pass validation."""
        rule = FinancialAmountRule(self.non_negative_config, "claims")
        df = pd.DataFrame({"CLM_PMT_AMT": ["1500.00", "0.00", "250.50", "9999.99"]})
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.PASS)
        self.assertEqual(result.affected_row_count, 0)
        self.assertEqual(result.actual["negative_count"], 0)

    def test_10_invalid_negative_amount(self):
        """Test 10: Negative amounts where prohibited trigger FAIL."""
        rule = FinancialAmountRule(self.non_negative_config, "claims")
        df = pd.DataFrame({"CLM_PMT_AMT": ["1500.00", "-50.00", "250.50", "-1.00"]})
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 2)
        self.assertEqual(result.actual["negative_count"], 2)

    def test_11_invalid_numeric_amount(self):
        """Test 11: Non-numeric strings (malformed numbers) trigger FAIL."""
        rule = FinancialAmountRule(self.non_negative_config, "claims")
        df = pd.DataFrame({"CLM_PMT_AMT": ["1500.00", "INVALID_AMT", "250.50", "abc"]})
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 2)
        self.assertEqual(result.actual["malformed_count"], 2)

    def test_12_configurable_boundary_condition(self):
        """Test 12: Values exceeding min/max thresholds trigger FAIL."""
        rule = FinancialAmountRule(self.range_config, "authorization")
        df = pd.DataFrame({"AUTH_AMT": ["5.00", "500.00", "75000.00"]})  # 5.00 < 10.0, 75000 > 50000
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 2)

    def test_12b_payment_within_total_charge_relational(self):
        """Test 12b: Payment exceeding total charge is flagged with WARNING."""
        rule = FinancialAmountRule(self.relational_config, "claims")
        df = pd.DataFrame(
            {
                "CLM_PMT_AMT": ["100.00", "500.00", "200.00"],
                "CLM_TOT_CHRG_AMT": ["150.00", "300.00", "200.00"],  # row 2: pmt 500 > chrg 300
            }
        )
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.WARNING)
        self.assertEqual(result.affected_row_count, 1)


if __name__ == "__main__":
    unittest.main()
