"""
Tests for Rule Groups D & E: Clinical Code (ICD and HCPCS/CPT) Quality Rules.
"""

import unittest
import pandas as pd

from src.data_quality.models import (
    ClinicalCodeRuleConfig,
    DataQualitySeverity,
    DataQualityStatus,
)
from src.data_quality.rules.clinical import ClinicalCodeRule


class TestClinicalCodeRules(unittest.TestCase):
    def setUp(self):
        self.icd_config = ClinicalCodeRuleConfig(
            id="DQ-CLIN-001",
            name="principal_icd_diagnosis_validity",
            field="PRNCPAL_DGNS_CD",
            code_system="ICD-10-CM",
            reference_dataset="icd_reference",
            reference_field="code",
            severity=DataQualitySeverity.WARNING,
        )
        self.hcpcs_config = ClinicalCodeRuleConfig(
            id="DQ-CLIN-003",
            name="procedure_hcpcs_cpt_validity",
            field="HCPCS_CD",
            code_system="HCPCS/CPT",
            reference_dataset="hcpcs_reference",
            reference_field="code",
            severity=DataQualitySeverity.WARNING,
        )

        # Mock reference tables for testing
        self.mock_icd_ref = pd.DataFrame({"code": ["I10", "E119", "J449", "M545", "K219"]})
        self.mock_hcpcs_ref = pd.DataFrame({"code": ["99221", "99495", "96156", "C8929", "G0442"]})

    def test_17_valid_icd_against_reference(self):
        """Test 17: Valid ICD codes matching reference dataset pass."""
        rule = ClinicalCodeRule(self.icd_config, "claims")
        df = pd.DataFrame({"PRNCPAL_DGNS_CD": ["I10", "E119", "J449"]})
        result = rule.evaluate(df, reference_datasets={"icd_reference": self.mock_icd_ref})

        self.assertEqual(result.status, DataQualityStatus.PASS)
        self.assertEqual(result.affected_row_count, 0)

    def test_18_invalid_icd_against_reference(self):
        """Test 18: Unrecognized ICD code not in reference triggers FAIL."""
        rule = ClinicalCodeRule(self.icd_config, "claims")
        df = pd.DataFrame({"PRNCPAL_DGNS_CD": ["I10", "INVALID_ICD_999", "J449"]})
        result = rule.evaluate(df, reference_datasets={"icd_reference": self.mock_icd_ref})

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 1)

    def test_19_missing_icd_reference_dependency(self):
        """Test 19: When reference dataset is unavailable, rule explicitly reports missing dependency."""
        rule = ClinicalCodeRule(self.icd_config, "claims")
        df = pd.DataFrame({"PRNCPAL_DGNS_CD": ["I10", "E119"]})
        # No icd_reference passed
        result = rule.evaluate(df, reference_datasets={})

        self.assertEqual(result.status, DataQualityStatus.WARNING)
        self.assertTrue(result.metadata.get("missing_reference"))
        self.assertIn("unavailable", result.message.lower())

    def test_20_valid_hcpcs_code(self):
        """Test 20: Valid HCPCS codes matching reference dataset pass."""
        rule = ClinicalCodeRule(self.hcpcs_config, "claims")
        df = pd.DataFrame({"HCPCS_CD": ["99221", "99495", "96156"]})
        result = rule.evaluate(df, reference_datasets={"hcpcs_reference": self.mock_hcpcs_ref})

        self.assertEqual(result.status, DataQualityStatus.PASS)
        self.assertEqual(result.affected_row_count, 0)

    def test_21_invalid_hcpcs_code(self):
        """Test 21: Unrecognized HCPCS code triggers FAIL."""
        rule = ClinicalCodeRule(self.hcpcs_config, "claims")
        df = pd.DataFrame({"HCPCS_CD": ["99221", "ZZ999", "96156"]})
        result = rule.evaluate(df, reference_datasets={"hcpcs_reference": self.mock_hcpcs_ref})

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.affected_row_count, 1)

    def test_22_missing_hcpcs_reference_dependency(self):
        """Test 22: Missing HCPCS reference dependency is explicitly reported."""
        rule = ClinicalCodeRule(self.hcpcs_config, "claims")
        df = pd.DataFrame({"HCPCS_CD": ["99221", "99495"]})
        result = rule.evaluate(df, reference_datasets=None)

        self.assertEqual(result.status, DataQualityStatus.WARNING)
        self.assertTrue(result.metadata.get("missing_reference"))


if __name__ == "__main__":
    unittest.main()
