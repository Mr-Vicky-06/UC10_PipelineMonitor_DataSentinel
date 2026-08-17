"""
Tests for Rule Group A: Completeness Quality Rules.
"""

import unittest
import pandas as pd

from src.data_quality.models import (
    CompletenessRuleConfig,
    DataQualitySeverity,
    DataQualityStatus,
)
from src.data_quality.rules.completeness import CompletenessRule


class TestCompletenessRules(unittest.TestCase):
    def setUp(self):
        self.config_zero_tolerance = CompletenessRuleConfig(
            id="DQ-COMP-001",
            name="bene_id_completeness",
            field="BENE_ID",
            threshold_null_pct=0.0,
            threshold_blank_pct=0.0,
            severity=DataQualitySeverity.ERROR,
        )
        self.config_with_tolerance = CompletenessRuleConfig(
            id="DQ-COMP-002",
            name="optional_field_completeness",
            field="ICD_DGNS_CD1",
            threshold_null_pct=10.0,
            threshold_blank_pct=5.0,
            severity=DataQualitySeverity.WARNING,
        )

    def test_01_no_nulls(self):
        """Test 1: Dataset with 100% populated fields passes completeness check."""
        rule = CompletenessRule(self.config_zero_tolerance, "claims")
        df = pd.DataFrame({"BENE_ID": ["B001", "B002", "B003", "B004"]})
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.PASS)
        self.assertEqual(result.affected_row_count, 0)
        self.assertEqual(result.affected_percentage, 0.0)
        self.assertEqual(result.actual["null_count"], 0)
        self.assertEqual(result.actual["blank_count"], 0)

    def test_02_nulls_below_threshold(self):
        """Test 2: Null percentage below configured threshold passes."""
        rule = CompletenessRule(self.config_with_tolerance, "claims")
        # 1 null out of 20 = 5% (threshold is 10%)
        df = pd.DataFrame({"ICD_DGNS_CD1": ["I10"] * 19 + [None]})
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.PASS)
        self.assertEqual(result.affected_row_count, 1)
        self.assertEqual(result.actual["null_count"], 1)
        self.assertAlmostEqual(result.actual["null_pct"], 5.0)

    def test_03_nulls_above_threshold(self):
        """Test 3: Null percentage exceeding threshold triggers FAIL."""
        rule = CompletenessRule(self.config_zero_tolerance, "claims")
        # 2 nulls out of 4 = 50% (threshold is 0.0%)
        df = pd.DataFrame({"BENE_ID": ["B001", None, "B003", None]})
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 2)
        self.assertEqual(result.affected_percentage, 50.0)
        self.assertEqual(result.actual["null_count"], 2)

    def test_04_blank_strings(self):
        """Test 4: Blank string representations ('', '   ', 'NULL', 'None') are detected."""
        rule = CompletenessRule(self.config_zero_tolerance, "claims")
        df = pd.DataFrame({"BENE_ID": ["B001", "", "   ", "NULL", "None", "B002"]})
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        # 4 blank string variants
        self.assertEqual(result.actual["blank_count"], 4)
        self.assertEqual(result.affected_row_count, 4)

    def test_05_required_field_missing(self):
        """Test 5: Required field completely missing from DataFrame results in FAIL."""
        rule = CompletenessRule(self.config_zero_tolerance, "claims")
        df = pd.DataFrame({"OTHER_FIELD": [1, 2, 3]})
        result = rule.evaluate(df)

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 3)
        self.assertIn("missing", result.message.lower())


if __name__ == "__main__":
    unittest.main()
