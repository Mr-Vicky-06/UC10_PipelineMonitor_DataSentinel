"""
Tests for Rule Group G: Referential Integrity and Cross-Dataset Validation Quality Rules.
"""

import unittest
import pandas as pd

from src.data_quality.models import (
    DataQualitySeverity,
    DataQualityStatus,
    ReferentialIntegrityRuleConfig,
)
from src.data_quality.rules.referential import ReferentialIntegrityRule


class TestReferentialRules(unittest.TestCase):
    def setUp(self):
        self.hospital_ref_config = ReferentialIntegrityRuleConfig(
            id="DQ-REF-001",
            name="hospital_provider_reference",
            foreign_key="PRVDR_NUM",
            reference_dataset="hospital_mapping",
            reference_key="PRVDR_NUM",
            severity=DataQualitySeverity.ERROR,
        )

        self.auth_ref_config = ReferentialIntegrityRuleConfig(
            id="DQ-REF-002",
            name="claims_authorization_integrity",
            match_key="BENE_ID",
            reference_dataset="authorization",
            reference_match_key="BENE_ID",
            provider_field="PRVDR_NUM",
            reference_provider_field="PRF_PHYSN_NPI",
            procedure_field="HCPCS_CD",
            reference_procedure_field="HCPCS_CD",
            service_date_field="CLM_FROM_DT",
            reference_eff_date_field="AUTH_EFF_DT",
            reference_exp_date_field="AUTH_EXP_DT",
            reference_status_field="AUTH_STATUS_CD",
            valid_auth_status="APPROVED",
            severity=DataQualitySeverity.ERROR,
        )

        self.mock_hospital_mapping = pd.DataFrame(
            {"PRVDR_NUM": ["030115", "491581", "377673", "331131", "107522"]}
        )

    def test_23_matching_valid_authorization(self):
        """Test 23: Claim matching an active authorization within service dates passes."""
        rule = ReferentialIntegrityRule(self.auth_ref_config, "claims")
        claims_df = pd.DataFrame(
            {
                "CLM_ID": ["C001"],
                "BENE_ID": ["B001"],
                "PRVDR_NUM": ["030115"],
                "HCPCS_CD": ["99221"],
                "CLM_FROM_DT": ["2020-05-15"],
            }
        )
        auth_df = pd.DataFrame(
            {
                "AUTH_ID": ["A001"],
                "BENE_ID": ["B001"],
                "PRF_PHYSN_NPI": ["030115"],
                "HCPCS_CD": ["99221"],
                "AUTH_EFF_DT": ["2020-05-01"],
                "AUTH_EXP_DT": ["2020-05-30"],
                "AUTH_STATUS_CD": ["APPROVED"],
            }
        )
        result = rule.evaluate(claims_df, reference_datasets={"authorization": auth_df})

        self.assertEqual(result.status, DataQualityStatus.PASS)
        self.assertEqual(result.affected_row_count, 0)

    def test_24_missing_authorization(self):
        """Test 24: Claim without matching authorization record triggers FAIL."""
        rule = ReferentialIntegrityRule(self.auth_ref_config, "claims")
        claims_df = pd.DataFrame(
            {
                "CLM_ID": ["C001"],
                "BENE_ID": ["B999_ORPHAN"],
                "PRVDR_NUM": ["030115"],
                "HCPCS_CD": ["99221"],
                "CLM_FROM_DT": ["2020-05-15"],
            }
        )
        auth_df = pd.DataFrame(
            {
                "AUTH_ID": ["A001"],
                "BENE_ID": ["B001"],
                "PRF_PHYSN_NPI": ["030115"],
                "HCPCS_CD": ["99221"],
                "AUTH_EFF_DT": ["2020-05-01"],
                "AUTH_EXP_DT": ["2020-05-30"],
                "AUTH_STATUS_CD": ["APPROVED"],
            }
        )
        result = rule.evaluate(claims_df, reference_datasets={"authorization": auth_df})

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.metadata["missing_authorization_count"], 1)

    def test_25_provider_mismatch(self):
        """Test 25: Provider on claim not matching authorization physician triggers FAIL."""
        rule = ReferentialIntegrityRule(self.auth_ref_config, "claims")
        claims_df = pd.DataFrame(
            {
                "CLM_ID": ["C001"],
                "BENE_ID": ["B001"],
                "PRVDR_NUM": ["491581"],  # Mismatched provider
                "HCPCS_CD": ["99221"],
                "CLM_FROM_DT": ["2020-05-15"],
            }
        )
        auth_df = pd.DataFrame(
            {
                "AUTH_ID": ["A001"],
                "BENE_ID": ["B001"],
                "PRF_PHYSN_NPI": ["030115"],
                "HCPCS_CD": ["99221"],
                "AUTH_EFF_DT": ["2020-05-01"],
                "AUTH_EXP_DT": ["2020-05-30"],
                "AUTH_STATUS_CD": ["APPROVED"],
            }
        )
        result = rule.evaluate(claims_df, reference_datasets={"authorization": auth_df})

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.metadata["provider_mismatch_count"], 1)

    def test_26_procedure_mismatch(self):
        """Test 26: HCPCS procedure on claim not matching authorization triggers FAIL."""
        rule = ReferentialIntegrityRule(self.auth_ref_config, "claims")
        claims_df = pd.DataFrame(
            {
                "CLM_ID": ["C001"],
                "BENE_ID": ["B001"],
                "PRVDR_NUM": ["030115"],
                "HCPCS_CD": ["99495"],  # Mismatched procedure
                "CLM_FROM_DT": ["2020-05-15"],
            }
        )
        auth_df = pd.DataFrame(
            {
                "AUTH_ID": ["A001"],
                "BENE_ID": ["B001"],
                "PRF_PHYSN_NPI": ["030115"],
                "HCPCS_CD": ["99221"],
                "AUTH_EFF_DT": ["2020-05-01"],
                "AUTH_EXP_DT": ["2020-05-30"],
                "AUTH_STATUS_CD": ["APPROVED"],
            }
        )
        result = rule.evaluate(claims_df, reference_datasets={"authorization": auth_df})

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.metadata["procedure_mismatch_count"], 1)

    def test_27_invalid_authorization_status(self):
        """Test 27: Authorization with status other than APPROVED triggers FAIL."""
        rule = ReferentialIntegrityRule(self.auth_ref_config, "claims")
        claims_df = pd.DataFrame(
            {
                "CLM_ID": ["C001"],
                "BENE_ID": ["B001"],
                "PRVDR_NUM": ["030115"],
                "HCPCS_CD": ["99221"],
                "CLM_FROM_DT": ["2020-05-15"],
            }
        )
        auth_df = pd.DataFrame(
            {
                "AUTH_ID": ["A001"],
                "BENE_ID": ["B001"],
                "PRF_PHYSN_NPI": ["030115"],
                "HCPCS_CD": ["99221"],
                "AUTH_EFF_DT": ["2020-05-01"],
                "AUTH_EXP_DT": ["2020-05-30"],
                "AUTH_STATUS_CD": ["DENIED"],  # Denied authorization
            }
        )
        result = rule.evaluate(claims_df, reference_datasets={"authorization": auth_df})

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.metadata["invalid_status_count"], 1)

    def test_28_expired_and_not_yet_effective_authorization(self):
        """Test 28: Service dates outside authorization effective window trigger FAIL."""
        rule = ReferentialIntegrityRule(self.auth_ref_config, "claims")
        # Claim 1 is expired (2020-06-15 > 2020-05-30)
        # Claim 2 is not yet effective (2020-04-15 < 2020-05-01)
        claims_df = pd.DataFrame(
            {
                "CLM_ID": ["C001", "C002"],
                "BENE_ID": ["B001", "B002"],
                "PRVDR_NUM": ["030115", "030115"],
                "HCPCS_CD": ["99221", "99221"],
                "CLM_FROM_DT": ["2020-06-15", "2020-04-15"],
            }
        )
        auth_df = pd.DataFrame(
            {
                "AUTH_ID": ["A001", "A002"],
                "BENE_ID": ["B001", "B002"],
                "PRF_PHYSN_NPI": ["030115", "030115"],
                "HCPCS_CD": ["99221", "99221"],
                "AUTH_EFF_DT": ["2020-05-01", "2020-05-01"],
                "AUTH_EXP_DT": ["2020-05-30", "2020-05-30"],
                "AUTH_STATUS_CD": ["APPROVED", "APPROVED"],
            }
        )
        result = rule.evaluate(claims_df, reference_datasets={"authorization": auth_df})

        self.assertEqual(result.status, DataQualityStatus.FAIL)
        self.assertEqual(result.metadata["expired_authorization_count"], 1)
        self.assertEqual(result.metadata["not_yet_effective_count"], 1)

    def test_28b_hospital_mapping_lookup(self):
        """Test 28b: Hospital provider mapping referential integrity."""
        rule = ReferentialIntegrityRule(self.hospital_ref_config, "claims")
        valid_claims = pd.DataFrame({"PRVDR_NUM": ["030115", "491581", "377673"]})
        res_pass = rule.evaluate(valid_claims, reference_datasets={"hospital_mapping": self.mock_hospital_mapping})
        self.assertEqual(res_pass.status, DataQualityStatus.PASS)

        invalid_claims = pd.DataFrame({"PRVDR_NUM": ["030115", "UNKNOWN_HOSP_999"]})
        res_fail = rule.evaluate(invalid_claims, reference_datasets={"hospital_mapping": self.mock_hospital_mapping})
        self.assertEqual(res_fail.status, DataQualityStatus.FAIL)
        self.assertEqual(res_fail.affected_row_count, 1)


if __name__ == "__main__":
    unittest.main()
