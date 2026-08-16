"""
Comprehensive Unit Test Suite for Schema Validation Module.
Covers 20 distinct failure, grain, format, and edge-case scenarios.
"""

from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.validation import (
    SchemaContract,
    SchemaValidator,
    ValidationSeverity,
    ValidationStatus,
    format_validation_json,
    format_validation_summary,
    load_schema_by_name,
    validate_dataset,
)


class TestSchemaValidatorComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.schemas_dir = cls.project_root / "configs" / "schemas"
        cls.claims_schema = load_schema_by_name("claims", cls.schemas_dir)
        cls.auth_schema = load_schema_by_name("authorization", cls.schemas_dir)
        cls.claims_validator = SchemaValidator(cls.claims_schema)
        cls.auth_validator = SchemaValidator(cls.auth_schema)

    # -------------------------------------------------------------
    # Scenario 1: Missing required column
    # -------------------------------------------------------------
    def test_01_missing_required_column(self):
        df = pd.DataFrame(
            {
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["111.01"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        self.assertFalse(result.passed)
        missing_issues = [i for i in result.issues if i.check_name == "required_columns_present"]
        self.assertTrue(len(missing_issues) > 0)
        self.assertIn("BENE_ID", missing_issues[0].message)

    # -------------------------------------------------------------
    # Scenario 2: Duplicate column name in header
    # -------------------------------------------------------------
    def test_02_duplicate_column_name(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", newline="") as f:
            f.write("AUTH_ID,BENE_ID,AUTH_ID,HCPCS_CD,AUTH_EFF_DT,AUTH_EXP_DT,AUTH_AMT,AUTH_STATUS_CD\n")
            f.write("A1,B1,A1,99495,20190724,20190828,100.0,APPROVED\n")
            temp_path = f.name

        try:
            result = self.auth_validator.validate_file(temp_path)
            self.assertEqual(result.status, ValidationStatus.FAIL)
            dup_issues = [i for i in result.issues if i.check_name == "no_duplicate_columns"]
            self.assertTrue(len(dup_issues) > 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------
    # Scenario 3: Unexpected column under strict/non-permissive schema
    # -------------------------------------------------------------
    def test_03_unexpected_column(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["AUTH001"],
                "BENE_ID": ["BENE001"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["4344.20"],
                "AUTH_STATUS_CD": ["APPROVED"],
                "EXTRA_UNKNOWN_COLUMN": ["value"],
            }
        )
        result = self.auth_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        unexp_issues = [i for i in result.issues if i.check_name == "no_unexpected_columns"]
        self.assertTrue(len(unexp_issues) > 0)

    # -------------------------------------------------------------
    # Scenario 4: Empty file (0 bytes)
    # -------------------------------------------------------------
    def test_04_empty_file(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as f:
            f.write("")
            temp_path = f.name

        try:
            result = self.claims_validator.validate_file(temp_path)
            self.assertEqual(result.status, ValidationStatus.FAIL)
            file_issues = [i for i in result.issues if i.category.value == "FILE_STRUCTURE"]
            self.assertTrue(len(file_issues) > 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------
    # Scenario 5: Malformed delimiter detection
    # -------------------------------------------------------------
    def test_05_malformed_delimiter_detection(self):
        # File has comma delimited records when default pipe was expected, auto-detects comma
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", newline="") as f:
            f.write("AUTH_ID,BENE_ID,PRF_PHYSN_NPI,HCPCS_CD,AUTH_EFF_DT,AUTH_EXP_DT,AUTH_AMT,AUTH_STATUS_CD\n")
            f.write("AUTH_1,BENE_1,107522,99495,20190724,20190828,500.00,APPROVED\n")
            temp_path = f.name

        try:
            result = self.auth_validator.validate_file(temp_path)
            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(result.total_columns, 8)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------
    # Scenario 6: Invalid integer
    # -------------------------------------------------------------
    def test_06_invalid_integer(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1"],
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["ABC_NOT_INT"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        type_issues = [i for i in result.issues if i.check_name == "integer_type"]
        self.assertEqual(len(type_issues), 1)

    # -------------------------------------------------------------
    # Scenario 7: Invalid float
    # -------------------------------------------------------------
    def test_07_invalid_float(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1"],
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["1,234.50.00_BAD"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        float_issues = [i for i in result.issues if i.check_name == "float_type"]
        self.assertEqual(len(float_issues), 1)

    # -------------------------------------------------------------
    # Scenario 8: Signed integer
    # -------------------------------------------------------------
    def test_08_signed_integer(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B2"],
                "CLM_ID": ["C1", "C2"],
                "CLM_LINE_NUM": ["+1", "-2"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022", "17-Sep-2022"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["100.00", "200.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.PASS)

    # -------------------------------------------------------------
    # Scenario 9: Decimal supplied to integer field
    # -------------------------------------------------------------
    def test_09_decimal_supplied_to_integer_field(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1"],
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1.5"],  # Decimal in integer field
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        type_issues = [i for i in result.issues if i.check_name == "integer_type"]
        self.assertEqual(len(type_issues), 1)

    # -------------------------------------------------------------
    # Scenario 10: Empty mandatory value ("")
    # -------------------------------------------------------------
    def test_10_empty_mandatory_value(self):
        df = pd.DataFrame(
            {
                "BENE_ID": [""],  # Empty string in mandatory non-nullable field
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        null_issues = [i for i in result.issues if i.check_name == "non_nullable_field" and i.column == "BENE_ID"]
        self.assertEqual(len(null_issues), 1)

    # -------------------------------------------------------------
    # Scenario 11: NULL mandatory value
    # -------------------------------------------------------------
    def test_11_null_mandatory_value(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["NULL"],  # Literal string "NULL" in mandatory field
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        null_issues = [i for i in result.issues if i.check_name == "non_nullable_field" and i.column == "BENE_ID"]
        self.assertEqual(len(null_issues), 1)

    # -------------------------------------------------------------
    # Scenario 12: NONE mandatory value
    # -------------------------------------------------------------
    def test_12_none_mandatory_value(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["NONE"],  # Literal string "NONE" in mandatory field
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        null_issues = [i for i in result.issues if i.check_name == "non_nullable_field" and i.column == "BENE_ID"]
        self.assertEqual(len(null_issues), 1)

    # -------------------------------------------------------------
    # Scenario 13: Invalid date
    # -------------------------------------------------------------
    def test_13_invalid_date(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1"],
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["99-INVALID-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        date_issues = [i for i in result.issues if i.check_name == "date_format"]
        self.assertEqual(len(date_issues), 1)

    # -------------------------------------------------------------
    # Scenario 14: Valid alternate date format (YYYY-MM-DD and DD-Mon-YYYY)
    # -------------------------------------------------------------
    def test_14_valid_alternate_date_format(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B2"],
                "CLM_ID": ["C1", "C2"],
                "CLM_LINE_NUM": ["1", "1"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "2022-09-17"],  # Both are accepted formats
                "CLM_THRU_DT": ["17-Sep-2022", "2022-09-17"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["100.00", "200.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.PASS)

    # -------------------------------------------------------------
    # Scenario 15: Duplicate CLM_ID + CLM_LINE_NUM (Duplicate primary key)
    # -------------------------------------------------------------
    def test_15_duplicate_claim_id_and_line_num(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B1"],
                "CLM_ID": ["C1", "C1"],  # SAME CLM_ID
                "CLM_LINE_NUM": ["1", "1"],  # SAME LINE NUM -> DUPLICATE KEY
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022", "17-Sep-2022"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["100.00", "200.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        pk_issues = [i for i in result.issues if i.check_name == "primary_key_uniqueness"]
        self.assertEqual(len(pk_issues), 1)

    # -------------------------------------------------------------
    # Scenario 16: Repeated CLM_ID with different line number (Claim-Line Grain)
    # -------------------------------------------------------------
    def test_16_repeated_claim_id_different_line(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B1"],
                "CLM_ID": ["C1", "C1"],  # SAME CLM_ID
                "CLM_LINE_NUM": ["1", "2"],  # DIFFERENT LINE NUM -> VALID CLAIM-LINE GRAIN
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022", "17-Sep-2022"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["100.00", "200.00"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.PASS)

    # -------------------------------------------------------------
    # Scenario 17: Duplicate AUTH_ID
    # -------------------------------------------------------------
    def test_17_duplicate_auth_id(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["AUTH001", "AUTH001"],  # DUPLICATE AUTH_ID
                "BENE_ID": ["B1", "B2"],
                "PRF_PHYSN_NPI": ["107522", "107522"],
                "HCPCS_CD": ["99495", "99495"],
                "AUTH_EFF_DT": ["20190724", "20190724"],
                "AUTH_EXP_DT": ["20190828", "20190828"],
                "AUTH_AMT": ["100.00", "200.00"],
                "AUTH_STATUS_CD": ["APPROVED", "APPROVED"],
            }
        )
        result = self.auth_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        pk_issues = [i for i in result.issues if i.check_name == "primary_key_uniqueness"]
        self.assertEqual(len(pk_issues), 1)

    # -------------------------------------------------------------
    # Scenario 18: Invalid authorization status (e.g. UNKNOWN_STATUS)
    # -------------------------------------------------------------
    def test_18_invalid_authorization_status(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["AUTH001"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": ["UNKNOWN_STATUS"],  # Ground truth anomaly status
            }
        )
        result = self.auth_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        status_issues = [i for i in result.issues if i.check_name == "allowed_values"]
        self.assertEqual(len(status_issues), 1)

    # -------------------------------------------------------------
    # Scenario 19: Valid authorization record
    # -------------------------------------------------------------
    def test_19_valid_authorization_record(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["AUTH001"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": ["APPROVED"],
            }
        )
        result = self.auth_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.PASS)
        self.assertTrue(result.passed)

    # -------------------------------------------------------------
    # Scenario 20: Completely valid claim batch
    # -------------------------------------------------------------
    def test_20_completely_valid_claim_batch(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B2"],
                "CLM_ID": ["C1", "C2"],
                "CLM_LINE_NUM": ["1", "1"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "10-Nov-2017"],
                "CLM_THRU_DT": ["17-Sep-2022", "10-Nov-2017"],
                "PRVDR_NUM": ["491581", "030115"],
                "CLM_PMT_AMT": ["111.01", "18206.34"],
                "ingestion_timestamp": ["2026-08-16T12:00:00", "2026-08-16T12:00:00"],
                "hospital_id": ["hospital_A", "hospital_A"],
                "batch_id": ["batch_20150316", "batch_20150316"],
            }
        )
        result = self.claims_validator.validate_dataframe(df)
        self.assertEqual(result.status, ValidationStatus.PASS)
        self.assertTrue(result.passed)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.warning_count, 0)


if __name__ == "__main__":
    unittest.main()
