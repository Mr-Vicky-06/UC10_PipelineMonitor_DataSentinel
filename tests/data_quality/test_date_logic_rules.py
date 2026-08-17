"""
Tests for Rule Group F: Date Quality and Logical Consistency Rules.
"""

import unittest
import pandas as pd

from src.data_quality.models import (
    DataQualitySeverity,
    DataQualityStatus,
    DateLogicRuleConfig,
)
from src.data_quality.rules.date_logic import DateLogicRule


class TestDateLogicRules(unittest.TestCase):
    def setUp(self):
        self.service_seq_config = DateLogicRuleConfig(
            id="DQ-DATE-001",
            name="service_date_ordering",
            from_date_field="CLM_FROM_DT",
            thru_date_field="CLM_THRU_DT",
            operator="<=",
            severity=DataQualitySeverity.ERROR,
        )
        self.admsn_dschrg_config = DateLogicRuleConfig(
            id="DQ-DATE-002",
            name="admission_discharge_ordering",
            admission_date_field="CLM_ADMSN_DT",
            discharge_date_field="NCH_BENE_DSCHRG_DT",
            operator="<=",
            severity=DataQualitySeverity.ERROR,
        )
        self.future_date_config = DateLogicRuleConfig(
            id="DQ-DATE-004",
            name="no_future_service_dates",
            date_field="CLM_FROM_DT",
            allow_future=False,
            reference_date="2026-01-01",
            severity=DataQualitySeverity.ERROR,
        )

    def test_13_valid_date_relationships(self):
        """Test 13: Chronologically valid dates pass validation across formats."""
        rule = DateLogicRule(self.service_seq_config, "claims")
        df = pd.DataFrame(
            {
                "CLM_FROM_DT": ["15-Jan-2020", "2021-03-01", "20220510"],
                "CLM_THRU_DT": ["20-Jan-2020", "2021-03-05", "20220510"],  # same-day thru is valid
            }
        )
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.PASS)
        self.assertEqual(result.affected_row_count, 0)

    def test_14_claim_thru_before_claim_from(self):
        """Test 14: Claim Through Date occurring before Claim From Date triggers FAIL."""
        rule = DateLogicRule(self.service_seq_config, "claims")
        df = pd.DataFrame(
            {
                "CLM_FROM_DT": ["25-Jan-2020", "2021-03-10"],
                "CLM_THRU_DT": ["20-Jan-2020", "2021-03-15"],  # row 1 has thru before from
            }
        )
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 1)

    def test_15_discharge_before_admission(self):
        """Test 15: Discharge date occurring before admission date triggers FAIL."""
        rule = DateLogicRule(self.admsn_dschrg_config, "claims")
        df = pd.DataFrame(
            {
                "CLM_ADMSN_DT": ["10-Mar-2021", "15-Apr-2021"],
                "NCH_BENE_DSCHRG_DT": ["05-Mar-2021", "20-Apr-2021"],  # row 1: discharge before admission
            }
        )
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 1)

    def test_16_future_date_scenario(self):
        """Test 16: Dates beyond reference cutoff trigger FAIL."""
        rule = DateLogicRule(self.future_date_config, "claims")
        df = pd.DataFrame(
            {
                "CLM_FROM_DT": ["15-Jan-2020", "01-Jun-2028"],  # row 2 is in 2028 (future)
            }
        )
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 1)


if __name__ == "__main__":
    unittest.main()
