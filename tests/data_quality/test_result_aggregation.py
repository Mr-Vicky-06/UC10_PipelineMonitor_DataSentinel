"""
Tests for Data Quality Result Aggregation and Upstream Schema Validation Gate Integration.
"""

import unittest
import pandas as pd

from src.data_quality.engine import DataQualityEngine
from src.data_quality.loader import load_rules_from_dict
from src.data_quality.models import (
    DataQualityReport,
    DataQualitySeverity,
    DataQualityStatus,
)
from src.validation.models import (
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)


class TestResultAggregation(unittest.TestCase):
    def setUp(self):
        self.sample_config_dict = {
            "dataset_name": "claims",
            "version": "1.0.0",
            "completeness_rules": [
                {
                    "id": "DQ-COMP-001",
                    "name": "bene_id_completeness",
                    "field": "BENE_ID",
                    "threshold_null_pct": 0.0,
                    "threshold_blank_pct": 0.0,
                    "severity": "ERROR",
                }
            ],
            "uniqueness_rules": [
                {
                    "id": "DQ-DUP-001",
                    "name": "claim_line_composite_uniqueness",
                    "fields": ["CLM_ID", "CLM_LINE_NUM"],
                    "threshold_duplicate_pct": 0.0,
                    "severity": "ERROR",
                }
            ],
            "financial_rules": [
                {
                    "id": "DQ-FIN-001",
                    "name": "non_negative_payment_amount",
                    "field": "CLM_PMT_AMT",
                    "allow_negative": False,
                    "severity": "ERROR",
                }
            ],
            "clinical_code_rules": [
                {
                    "id": "DQ-CLIN-001",
                    "name": "principal_icd_diagnosis_code_validity",
                    "field": "PRNCPAL_DGNS_CD",
                    "code_system": "ICD-10-CM",
                    "reference_dataset": "icd_reference",
                    "severity": "WARNING",
                }
            ],
            "schema_gate": {
                "enabled": True,
                "severity_on_fail": "CRITICAL",
                "severity_on_warning": "WARNING",
            },
        }

    def test_29_overall_pass(self):
        """Test 29: When all rules pass, overall status is PASS."""
        engine = DataQualityEngine(self.sample_config_dict)
        clean_df = pd.DataFrame(
            {
                "BENE_ID": ["B001", "B002"],
                "CLM_ID": ["C001", "C002"],
                "CLM_LINE_NUM": ["1", "1"],
                "CLM_PMT_AMT": ["100.00", "250.00"],
                "PRNCPAL_DGNS_CD": ["I10", "E119"],
            }
        )
        mock_icd = pd.DataFrame({"code": ["I10", "E119"]})

        report = engine.evaluate_dataframe(
            df=clean_df,
            reference_datasets={"icd_reference": mock_icd},
            schema_validation_result="PASS",
        )

        self.assertEqual(report.overall_status, DataQualityStatus.PASS)
        self.assertTrue(report.passed)
        self.assertEqual(report.failed_rules, 0)
        self.assertEqual(report.warning_rules, 0)
        self.assertGreater(report.passed_rules, 0)

    def test_30_overall_warning(self):
        """Test 30: When warnings occur without hard failures, overall status is WARNING."""
        engine = DataQualityEngine(self.sample_config_dict)
        df = pd.DataFrame(
            {
                "BENE_ID": ["B001", "B002"],
                "CLM_ID": ["C001", "C002"],
                "CLM_LINE_NUM": ["1", "1"],
                "CLM_PMT_AMT": ["100.00", "250.00"],
                "PRNCPAL_DGNS_CD": ["I10", "E119"],
            }
        )
        # icd_reference missing triggers WARNING on DQ-CLIN-001
        report = engine.evaluate_dataframe(
            df=df,
            reference_datasets={},
            schema_validation_result="PASS",
        )

        self.assertEqual(report.overall_status, DataQualityStatus.WARNING)
        self.assertTrue(report.has_warnings)
        self.assertEqual(report.failed_rules, 0)
        self.assertGreater(report.warning_rules, 0)

    def test_31_overall_fail(self):
        """Test 31: When a rule with ERROR severity fails, overall status is FAIL."""
        engine = DataQualityEngine(self.sample_config_dict)
        # Negative amount on CLM_PMT_AMT
        df = pd.DataFrame(
            {
                "BENE_ID": ["B001", "B002"],
                "CLM_ID": ["C001", "C002"],
                "CLM_LINE_NUM": ["1", "1"],
                "CLM_PMT_AMT": ["100.00", "-50.00"],
                "PRNCPAL_DGNS_CD": ["I10", "E119"],
            }
        )
        mock_icd = pd.DataFrame({"code": ["I10", "E119"]})

        report = engine.evaluate_dataframe(
            df=df,
            reference_datasets={"icd_reference": mock_icd},
            schema_validation_result="PASS",
        )

        self.assertEqual(report.overall_status, DataQualityStatus.FAIL)
        self.assertTrue(report.has_failures)
        self.assertGreater(report.failed_rules, 0)

    def test_32_multiple_simultaneous_rule_failures(self):
        """Test 32: Multiple simultaneous rule failures across dimensions are all captured."""
        engine = DataQualityEngine(self.sample_config_dict)
        # Failures:
        # 1. Null in BENE_ID
        # 2. Duplicate (CLM_ID, CLM_LINE_NUM)
        # 3. Negative CLM_PMT_AMT
        bad_df = pd.DataFrame(
            {
                "BENE_ID": ["B001", None],
                "CLM_ID": ["C001", "C001"],
                "CLM_LINE_NUM": ["1", "1"],
                "CLM_PMT_AMT": ["-10.00", "-50.00"],
                "PRNCPAL_DGNS_CD": ["I10", "E119"],
            }
        )
        mock_icd = pd.DataFrame({"code": ["I10", "E119"]})

        report = engine.evaluate_dataframe(
            df=bad_df,
            reference_datasets={"icd_reference": mock_icd},
            schema_validation_result="PASS",
        )

        self.assertEqual(report.overall_status, DataQualityStatus.FAIL)
        self.assertEqual(report.failed_rules, 3)
        failures = report.get_failures()
        failed_ids = [f.rule_id for f in failures]
        self.assertIn("DQ-COMP-001", failed_ids)
        self.assertIn("DQ-DUP-001", failed_ids)
        self.assertIn("DQ-FIN-001", failed_ids)

    def test_32b_upstream_validation_result_object_integration(self):
        """Test 32b: Integrating upstream ValidationResult object into DataQualityReport."""
        engine = DataQualityEngine(self.sample_config_dict)
        clean_df = pd.DataFrame(
            {
                "BENE_ID": ["B001"],
                "CLM_ID": ["C001"],
                "CLM_LINE_NUM": ["1"],
                "CLM_PMT_AMT": ["100.00"],
                "PRNCPAL_DGNS_CD": ["I10"],
            }
        )
        mock_icd = pd.DataFrame({"code": ["I10"]})

        # Simulate upstream ValidationResult failing
        failed_schema_res = ValidationResult(
            dataset="claims",
            file_path="sample.csv",
            status=ValidationStatus.FAIL,
            total_rows=1,
            total_columns=5,
            issues=[
                ValidationIssue(
                    category=ValidationCategory.COLUMNS,
                    check_name="required_columns_present",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.ERROR,
                    message="Missing column X",
                )
            ],
        )

        report = engine.evaluate_dataframe(
            df=clean_df,
            reference_datasets={"icd_reference": mock_icd},
            schema_validation_result=failed_schema_res,
        )

        # Since schema validation failed upstream, the schema gate rule fails
        self.assertEqual(report.overall_status, DataQualityStatus.FAIL)
        schema_rule = [r for r in report.rule_results if r.rule_id == "DQ-SCHEMA-001"][0]
        self.assertEqual(schema_rule.status, DataQualityStatus.FAIL)
        self.assertEqual(schema_rule.severity, DataQualitySeverity.CRITICAL)


if __name__ == "__main__":
    unittest.main()
