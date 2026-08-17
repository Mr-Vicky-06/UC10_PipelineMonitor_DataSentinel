"""
Tests for Rule Group B: Uniqueness and Duplicate Quality Rules.
"""

import unittest
import pandas as pd

from src.data_quality.models import (
    DataQualitySeverity,
    DataQualityStatus,
    UniquenessRuleConfig,
)
from src.data_quality.rules.uniqueness import UniquenessRule


class TestUniquenessRules(unittest.TestCase):
    def setUp(self):
        self.claim_line_config = UniquenessRuleConfig(
            id="DQ-DUP-001",
            name="claim_line_composite_uniqueness",
            fields=["CLM_ID", "CLM_LINE_NUM"],
            threshold_duplicate_pct=0.0,
            severity=DataQualitySeverity.ERROR,
        )
        self.auth_id_config = UniquenessRuleConfig(
            id="DQ-AUTH-DUP-001",
            name="auth_id_uniqueness",
            fields=["AUTH_ID"],
            threshold_duplicate_pct=0.0,
            severity=DataQualitySeverity.ERROR,
        )

    def test_06_valid_repeated_claim_id_different_lines(self):
        """Test 6: Repeated CLM_ID with different line numbers is VALID (respects claim-line grain)."""
        rule = UniquenessRule(self.claim_line_config, "claims")
        df = pd.DataFrame(
            {
                "CLM_ID": ["C001", "C001", "C001", "C002", "C002"],
                "CLM_LINE_NUM": ["1", "2", "3", "1", "2"],
            }
        )
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.PASS)
        self.assertEqual(result.affected_row_count, 0)
        self.assertEqual(result.actual["duplicate_row_count"], 0)
        self.assertEqual(result.actual["duplicate_keys_count"], 0)

    def test_07_duplicate_claim_id_and_line_number(self):
        """Test 7: Duplicate (CLM_ID, CLM_LINE_NUM) pairs trigger FAIL."""
        rule = UniquenessRule(self.claim_line_config, "claims")
        df = pd.DataFrame(
            {
                "CLM_ID": ["C001", "C001", "C002"],
                "CLM_LINE_NUM": ["1", "1", "1"],  # C001, line 1 is duplicated!
            }
        )
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        # 2 rows participate in the duplicate (keep=False)
        self.assertEqual(result.affected_row_count, 2)
        self.assertEqual(result.actual["duplicate_row_count"], 2)
        self.assertEqual(result.actual["duplicate_keys_count"], 1)
        self.assertEqual(result.actual["excess_duplicate_count"], 1)

    def test_08_multiple_duplicate_claim_lines(self):
        """Test 8: Multiple distinct duplicate keys are accurately counted."""
        rule = UniquenessRule(self.claim_line_config, "claims")
        df = pd.DataFrame(
            {
                "CLM_ID": ["C001", "C001", "C002", "C002", "C003"],
                "CLM_LINE_NUM": ["1", "1", "2", "2", "1"],
            }
        )
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        # 4 rows participate in duplicates (C001-1 and C002-2)
        self.assertEqual(result.affected_row_count, 4)
        self.assertEqual(result.actual["duplicate_keys_count"], 2)
        self.assertEqual(result.actual["excess_duplicate_count"], 2)


if __name__ == "__main__":
    unittest.main()
