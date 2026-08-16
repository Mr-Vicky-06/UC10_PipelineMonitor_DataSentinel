"""
Comprehensive test suite for the Data Cleaning Module.
Covers all 23 specific refinement verification points.
"""

import hashlib
import os
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.cleaning import (
    CleaningConfig,
    CleaningStatus,
    DataCleaner,
    clean_dataset,
    load_cleaning_config_by_name,
)


class TestDataCleanerComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.config_dir = cls.project_root / "configs" / "cleaning"
        cls.claims_config = load_cleaning_config_by_name("claims", cls.config_dir)
        cls.auth_config = load_cleaning_config_by_name("authorization", cls.config_dir)
        cls.claims_cleaner = DataCleaner(cls.claims_config)
        cls.auth_cleaner = DataCleaner(cls.auth_config)

    # -------------------------------------------------------------
    # 1. Identifier casing/value preservation (not blindly modified)
    # -------------------------------------------------------------
    def test_01_identifier_preservation(self):
        df = pd.DataFrame(
            {
                "BENE_ID": [" bene_alpha_1 "],
                "CLM_ID": [" clm_test_99 "],
                "CLM_LINE_NUM": [" 1 "],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": [" 030115 "],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        res = self.claims_cleaner.clean(df)
        # Identifiers must have whitespace trimmed but retain exact value and string type
        self.assertEqual(res.cleaned_df["BENE_ID"].iloc[0], "bene_alpha_1")
        self.assertEqual(res.cleaned_df["CLM_ID"].iloc[0], "clm_test_99")
        self.assertEqual(res.cleaned_df["PRVDR_NUM"].iloc[0], "030115")
        self.assertIsInstance(res.cleaned_df["PRVDR_NUM"].iloc[0], str)

    # -------------------------------------------------------------
    # 2. Categorical uppercase normalization
    # -------------------------------------------------------------
    def test_02_categorical_uppercase_normalization(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["A1"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": [" approved "],
            }
        )
        res = self.auth_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["AUTH_STATUS_CD"].iloc[0], "APPROVED")
        self.assertEqual(res.report.metrics.categorical_cells_normalized, 1)

    # -------------------------------------------------------------
    # 3. Unknown categorical value preservation
    # -------------------------------------------------------------
    def test_03_unknown_categorical_preservation(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["A1"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": [" unknown_status "],
            }
        )
        res = self.auth_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["AUTH_STATUS_CD"].iloc[0], "UNKNOWN_STATUS")

    # -------------------------------------------------------------
    # 4. Free-text is not blindly uppercased
    # -------------------------------------------------------------
    def test_04_free_text_not_blindly_uppercased(self):
        custom_config = CleaningConfig(
            dataset_name="custom_notes",
            free_text_fields=["CLINICAL_NOTE"],
            identifier_fields=["ID"],
        )
        cleaner = DataCleaner(custom_config)
        df = pd.DataFrame(
            {
                "ID": ["1"],
                "CLINICAL_NOTE": [" Patient reported mild chest pain and shortness of breath. "],
            }
        )
        res = cleaner.clean(df)
        self.assertEqual(
            res.cleaned_df["CLINICAL_NOTE"].iloc[0],
            "Patient reported mild chest pain and shortness of breath.",
        )

    # -------------------------------------------------------------
    # 5. Leading zeros remain intact
    # -------------------------------------------------------------
    def test_05_leading_zeros_remain_intact(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["000123"],
                "CLM_ID": ["000456"],
                "CLM_LINE_NUM": ["01"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["030115"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        res = self.claims_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["PRVDR_NUM"].iloc[0], "030115")
        self.assertEqual(res.cleaned_df["BENE_ID"].iloc[0], "000123")
        self.assertEqual(res.cleaned_df["CLM_LINE_NUM"].iloc[0], "01")

    # -------------------------------------------------------------
    # 6. Mandatory null is NOT fabricated
    # -------------------------------------------------------------
    def test_06_mandatory_null_not_fabricated(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["NULL"],  # Mandatory field
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        res = self.claims_cleaner.clean(df)
        # Standardized to canonical missing "", NEVER fabricated into "UNKNOWN", "0", or synthetic ID
        self.assertEqual(res.cleaned_df["BENE_ID"].iloc[0], "")
        self.assertNotEqual(res.cleaned_df["BENE_ID"].iloc[0], "UNKNOWN")
        self.assertNotEqual(res.cleaned_df["BENE_ID"].iloc[0], "0")

    # -------------------------------------------------------------
    # 7. Mandatory null is reported as unresolved
    # -------------------------------------------------------------
    def test_07_mandatory_null_reported_as_unresolved(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["None"],  # Mandatory field
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        res = self.claims_cleaner.clean(df)
        self.assertEqual(res.report.metrics.unresolved_mandatory_null_count, 1)
        self.assertEqual(res.report.metrics.unresolved_records, 1)
        self.assertEqual(res.report.status, CleaningStatus.WARNING)
        self.assertTrue(any("unresolved mandatory null" in w for w in res.report.warnings))

    # -------------------------------------------------------------
    # 8. Valid date normalization
    # -------------------------------------------------------------
    def test_08_valid_date_normalization(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B2"],
                "CLM_ID": ["C1", "C2"],
                "CLM_LINE_NUM": ["1", "1"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "20220917"],
                "CLM_THRU_DT": ["28-Feb-2023", "2023-02-28"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["100.00", "200.00"],
            }
        )
        res = self.claims_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["CLM_FROM_DT"].iloc[0], "2022-09-17")
        self.assertEqual(res.cleaned_df["CLM_FROM_DT"].iloc[1], "2022-09-17")
        self.assertEqual(res.cleaned_df["CLM_THRU_DT"].iloc[0], "2023-02-28")
        self.assertEqual(res.cleaned_df["CLM_THRU_DT"].iloc[1], "2023-02-28")

    # -------------------------------------------------------------
    # 9. Invalid date is not fabricated
    # -------------------------------------------------------------
    def test_09_invalid_date_not_fabricated(self):
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
        res = self.claims_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["CLM_FROM_DT"].iloc[0], "99-INVALID-2022")
        self.assertEqual(res.report.metrics.unresolved_invalid_date_count, 1)
        self.assertTrue(any("invalid date" in w for w in res.report.warnings))

    # -------------------------------------------------------------
    # 10. Repeated CLM_ID with different line numbers remains
    # -------------------------------------------------------------
    def test_10_repeated_claim_id_different_line_remains(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B1"],
                "CLM_ID": ["C1", "C1"],  # SAME CLM_ID
                "CLM_LINE_NUM": ["1", "2"],  # DIFFERENT LINE NUM
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022", "17-Sep-2022"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["100.00", "250.00"],
            }
        )
        res = self.claims_cleaner.clean(df)
        self.assertEqual(len(res.cleaned_df), 2)
        self.assertEqual(res.report.metrics.exact_duplicate_rows_removed, 0)
        self.assertEqual(res.report.metrics.conflicting_key_groups_found, 0)

    # -------------------------------------------------------------
    # 11. Exact claim-line duplicate is removed
    # -------------------------------------------------------------
    def test_11_exact_claim_line_duplicate_removed(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B1"],
                "CLM_ID": ["C1", "C1"],
                "CLM_LINE_NUM": ["1", "1"],
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022", "17-Sep-2022"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["100.00", "100.00"],
            }
        )
        res = self.claims_cleaner.clean(df)
        self.assertEqual(len(res.cleaned_df), 1)
        self.assertEqual(res.report.metrics.exact_duplicate_rows_removed, 1)

    # -------------------------------------------------------------
    # 12. Conflicting claim-line key is preserved and flagged
    # -------------------------------------------------------------
    def test_12_conflicting_claim_line_key_preserved_and_flagged(self):
        df = pd.DataFrame(
            {
                "BENE_ID": ["B1", "B1"],
                "CLM_ID": ["C1", "C1"],  # SAME CLM_ID
                "CLM_LINE_NUM": ["1", "1"],  # SAME LINE NUM -> CONFLICT
                "NCH_CLM_TYPE_CD": ["60", "60"],
                "CLM_FROM_DT": ["17-Sep-2022", "17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022", "17-Sep-2022"],
                "PRVDR_NUM": ["491581", "491581"],
                "CLM_PMT_AMT": ["100.00", "999.00"],  # DIFFERENT VALUE
            }
        )
        res = self.claims_cleaner.clean(df)
        self.assertEqual(len(res.cleaned_df), 2)  # BOTH PRESERVED
        self.assertEqual(res.report.metrics.conflicting_key_groups_found, 1)
        self.assertEqual(res.report.status, CleaningStatus.WARNING)
        self.assertTrue(any("conflicting composite primary key" in w for w in res.report.warnings))

    # -------------------------------------------------------------
    # 13. Exact AUTH_ID duplicate is removed
    # -------------------------------------------------------------
    def test_13_exact_auth_id_duplicate_removed(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["A1", "A1"],
                "BENE_ID": ["B1", "B1"],
                "PRF_PHYSN_NPI": ["107522", "107522"],
                "HCPCS_CD": ["99495", "99495"],
                "AUTH_EFF_DT": ["20190724", "20190724"],
                "AUTH_EXP_DT": ["20190828", "20190828"],
                "AUTH_AMT": ["100.00", "100.00"],
                "AUTH_STATUS_CD": ["APPROVED", "APPROVED"],
            }
        )
        res = self.auth_cleaner.clean(df)
        self.assertEqual(len(res.cleaned_df), 1)
        self.assertEqual(res.report.metrics.exact_duplicate_rows_removed, 1)

    # -------------------------------------------------------------
    # 14. Conflicting AUTH_ID is preserved and flagged
    # -------------------------------------------------------------
    def test_14_conflicting_auth_id_preserved_and_flagged(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["A1", "A1"],  # SAME AUTH_ID
                "BENE_ID": ["B1", "B1"],
                "PRF_PHYSN_NPI": ["107522", "107522"],
                "HCPCS_CD": ["99495", "99495"],
                "AUTH_EFF_DT": ["20190724", "20190724"],
                "AUTH_EXP_DT": ["20190828", "20190828"],
                "AUTH_AMT": ["100.00", "500.00"],  # DIFFERENT AMT
                "AUTH_STATUS_CD": ["APPROVED", "DENIED"],  # DIFFERENT STATUS
            }
        )
        res = self.auth_cleaner.clean(df)
        self.assertEqual(len(res.cleaned_df), 2)  # BOTH PRESERVED
        self.assertEqual(res.report.metrics.conflicting_key_groups_found, 1)

    # -------------------------------------------------------------
    # 15. UNKNOWN_STATUS remains UNKNOWN_STATUS
    # -------------------------------------------------------------
    def test_15_unknown_status_preserved(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["A1"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": ["UNKNOWN_STATUS"],
            }
        )
        res = self.auth_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["AUTH_STATUS_CD"].iloc[0], "UNKNOWN_STATUS")

    # -------------------------------------------------------------
    # 16. Expired authorization remains expired
    # -------------------------------------------------------------
    def test_16_expired_authorization_remains_expired(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["A1"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20180101"],
                "AUTH_EXP_DT": ["20180201"],  # Expired in past
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": ["EXPIRED"],
            }
        )
        res = self.auth_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["AUTH_STATUS_CD"].iloc[0], "EXPIRED")
        self.assertEqual(res.cleaned_df["AUTH_EXP_DT"].iloc[0], "2018-02-01")

    # -------------------------------------------------------------
    # 17. Provider mismatch remains provider mismatch
    # -------------------------------------------------------------
    def test_17_provider_mismatch_remains_mismatched(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["A1"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["9999999999"],  # Non-matching provider
                "HCPCS_CD": ["99495"],
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": ["APPROVED"],
            }
        )
        res = self.auth_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["PRF_PHYSN_NPI"].iloc[0], "9999999999")

    # -------------------------------------------------------------
    # 18. Procedure mismatch remains procedure mismatch
    # -------------------------------------------------------------
    def test_18_procedure_mismatch_remains_mismatched(self):
        df = pd.DataFrame(
            {
                "AUTH_ID": ["A1"],
                "BENE_ID": ["B1"],
                "PRF_PHYSN_NPI": ["107522"],
                "HCPCS_CD": ["00000"],  # Non-matching procedure
                "AUTH_EFF_DT": ["20190724"],
                "AUTH_EXP_DT": ["20190828"],
                "AUTH_AMT": ["100.00"],
                "AUTH_STATUS_CD": ["APPROVED"],
            }
        )
        res = self.auth_cleaner.clean(df)
        self.assertEqual(res.cleaned_df["HCPCS_CD"].iloc[0], "00000")

    # -------------------------------------------------------------
    # 19. Cleaning metrics distinguish rows vs cells
    # -------------------------------------------------------------
    def test_19_metrics_distinguish_rows_vs_cells(self):
        df = pd.DataFrame(
            {
                "BENE_ID": [" B1 ", " B2 "],
                "CLM_ID": [" C1 ", " C2 "],
                "CLM_LINE_NUM": [" 1 ", " 1 "],
                "NCH_CLM_TYPE_CD": [" 60 ", " 60 "],
                "CLM_FROM_DT": [" 17-Sep-2022 ", " 17-Sep-2022 "],
                "CLM_THRU_DT": [" 17-Sep-2022 ", " 17-Sep-2022 "],
                "PRVDR_NUM": [" 491581 ", " 491581 "],
                "CLM_PMT_AMT": [" 1,234.50 ", " 2,345.60 "],
            }
        )
        res = self.claims_cleaner.clean(df)
        report_dict = res.report.to_dict()
        metrics = report_dict["metrics"]

        # Check explicit row-level metrics
        self.assertEqual(metrics["input_rows"], 2)
        self.assertEqual(metrics["output_rows"], 2)
        self.assertEqual(metrics["rows_changed"], 2)
        self.assertEqual(metrics["exact_duplicate_rows_removed"], 0)

        # Check explicit cell-level metrics
        self.assertEqual(metrics["whitespace_cells_normalized"], 16)
        self.assertEqual(metrics["date_cells_normalized"], 4)
        self.assertEqual(metrics["numeric_cells_normalized"], 2)

    # -------------------------------------------------------------
    # 20. Cleaning remains deterministic
    # -------------------------------------------------------------
    def test_20_cleaning_remains_deterministic(self):
        df = pd.DataFrame(
            {
                "BENE_ID": [" B1 "],
                "CLM_ID": [" C1 "],
                "CLM_LINE_NUM": [" 1 "],
                "NCH_CLM_TYPE_CD": [" 60 "],
                "CLM_FROM_DT": [" 17-Sep-2022 "],
                "CLM_THRU_DT": [" 17-Sep-2022 "],
                "PRVDR_NUM": [" 491581 "],
                "CLM_PMT_AMT": [" 1,234.50 "],
            }
        )
        res1 = self.claims_cleaner.clean(df)
        res2 = self.claims_cleaner.clean(df)
        pd.testing.assert_frame_equal(res1.cleaned_df, res2.cleaned_df)

    # -------------------------------------------------------------
    # 21. Schema Validation -> Cleaning integration still works
    # -------------------------------------------------------------
    def test_21_schema_validation_integration(self):
        valid_df = pd.DataFrame(
            {
                "BENE_ID": ["B1"],
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        res_valid = clean_dataset("claims", valid_df, run_schema_validation=True)
        self.assertTrue(res_valid.passed)
        self.assertEqual(res_valid.report.status, CleaningStatus.SUCCESS)

        invalid_df = pd.DataFrame(
            {
                # Missing BENE_ID -> Schema Validation FAIL
                "CLM_ID": ["C1"],
                "CLM_LINE_NUM": ["1"],
                "NCH_CLM_TYPE_CD": ["60"],
                "CLM_FROM_DT": ["17-Sep-2022"],
                "CLM_THRU_DT": ["17-Sep-2022"],
                "PRVDR_NUM": ["491581"],
                "CLM_PMT_AMT": ["100.00"],
            }
        )
        res_invalid = clean_dataset("claims", invalid_df, run_schema_validation=True)
        self.assertFalse(res_invalid.passed)
        self.assertEqual(res_invalid.report.status, CleaningStatus.FAILED)

    # -------------------------------------------------------------
    # 22. Source data remains unchanged
    # -------------------------------------------------------------
    def test_22_source_data_remains_unchanged(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", newline="") as f:
            f.write("AUTH_ID,BENE_ID,PRF_PHYSN_NPI,HCPCS_CD,AUTH_EFF_DT,AUTH_EXP_DT,AUTH_AMT,AUTH_STATUS_CD\n")
            f.write("A1,B1,107522,99495,20190724,20190828,100.0, approved \n")
            temp_path = f.name

        with open(temp_path, "rb") as f:
            hash_before = hashlib.sha256(f.read()).hexdigest()

        with tempfile.TemporaryDirectory() as out_dir:
            out_file = Path(out_dir) / "cleaned.csv"
            clean_dataset("authorization", temp_path, output_path=out_file, run_schema_validation=False)

        with open(temp_path, "rb") as f:
            hash_after = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(hash_before, hash_after)
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # -------------------------------------------------------------
    # 23. Master data remains unchanged
    # -------------------------------------------------------------
    def test_23_master_data_remains_unchanged(self):
        master_auth = self.project_root / "master_data" / "master_data" / "authorization" / "authorization_linked.csv"
        if master_auth.exists():
            with open(master_auth, "rb") as f:
                h_before = hashlib.sha256(f.read()).hexdigest()

            with tempfile.TemporaryDirectory() as out_dir:
                out_f = Path(out_dir) / "cleaned_auth.csv"
                clean_dataset("authorization", master_auth, output_path=out_f, run_schema_validation=False)

            with open(master_auth, "rb") as f:
                h_after = hashlib.sha256(f.read()).hexdigest()

            self.assertEqual(h_before, h_after)


if __name__ == "__main__":
    unittest.main()
