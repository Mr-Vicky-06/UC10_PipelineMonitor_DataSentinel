"""
Real Master Data and Ground-Truth Anomaly Validation Tests for Layer 2 Data Quality Engine.
Evaluates actual master-data files and validates detection against anomaly_ground_truth.csv.
"""

from pathlib import Path
import unittest
import pandas as pd

from src.data_quality import evaluate_data_quality
from src.data_quality.models import DataQualityStatus
from src.data_quality.results import format_quality_summary


class TestRealMasterDataQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.master_data_dir = cls.project_root / "master_data" / "master_data"
        if not cls.master_data_dir.exists():
            cls.master_data_dir = Path(r"D:\UC10_Data_Quality_Pipeline\master_data")

        cls.auth_file = cls.master_data_dir / "authorization" / "authorization_linked.csv"
        cls.hospital_mapping_file = cls.master_data_dir / "reference" / "hospital_mapping.csv"
        cls.ground_truth_file = cls.master_data_dir / "scenarios" / "anomaly_ground_truth.csv"
        cls.claims_master_file = cls.master_data_dir / "claims" / "claims_master.csv"

    def test_36_real_authorization_linked_master_data(self):
        """Test 36: Real authorization dataset is evaluated cleanly."""
        self.assertTrue(self.auth_file.exists(), f"Auth file missing at {self.auth_file}")

        report = evaluate_data_quality(
            dataset="authorization",
            data=self.auth_file,
            schema_validation_result="PASS",
            context={"run_id": "test_auth_run"},
        )

        self.assertEqual(report.total_rows, 21801)
        self.assertEqual(report.total_columns, 8)
        self.assertGreater(report.rules_executed, 0)

        # Completeness on AUTH_ID, BENE_ID, PRF_PHYSN_NPI should pass with 0 nulls
        comp_auth_id = [r for r in report.rule_results if r.rule_id == "DQ-AUTH-COMP-001"][0]
        self.assertEqual(comp_auth_id.status, DataQualityStatus.PASS)

        # Uniqueness on AUTH_ID should pass with 0 duplicates
        unq_auth = [r for r in report.rule_results if r.rule_id == "DQ-AUTH-DUP-001"][0]
        self.assertEqual(unq_auth.status, DataQualityStatus.PASS)

        # Financial on AUTH_AMT should pass with 0 negative amounts
        fin_auth = [r for r in report.rule_results if r.rule_id == "DQ-AUTH-FIN-001"][0]
        self.assertEqual(fin_auth.status, DataQualityStatus.PASS)

        # Validity rule catches the 244 injected UNKNOWN_STATUS records
        val_status = [r for r in report.rule_results if r.rule_id == "DQ-AUTH-VAL-001"][0]
        self.assertEqual(val_status.status, DataQualityStatus.FAIL)
        self.assertEqual(val_status.affected_row_count, 244)

    def test_37_all_five_hospital_batches(self):
        """Test 37: Real batches from all 5 hospitals evaluate with high throughput and valid status."""
        batches_dir = self.master_data_dir / "batches" / "run_20260816_141418"
        if not batches_dir.exists():
            run_dirs = list((self.master_data_dir / "batches").glob("run_*"))
            if run_dirs:
                batches_dir = run_dirs[0]

        self.assertTrue(batches_dir.exists(), f"Batches directory missing at {batches_dir}")
        hospital_mapping_df = pd.read_csv(self.hospital_mapping_file, dtype=str)

        hospitals = ["hospital_A", "hospital_B", "hospital_C", "hospital_D", "hospital_E"]
        for hosp in hospitals:
            hosp_dir = batches_dir / hosp
            self.assertTrue(hosp_dir.exists(), f"Hospital directory missing: {hosp_dir}")
            batch_files = sorted(list(hosp_dir.glob("batch_*.csv")))
            self.assertTrue(len(batch_files) > 0, f"No batch files found for {hosp}")

            # Test first 3 batch files per hospital
            for sample_batch in batch_files[:3]:
                report = evaluate_data_quality(
                    dataset="claims",
                    data=sample_batch,
                    reference_datasets={"hospital_mapping": hospital_mapping_df},
                    schema_validation_result="PASS",
                    context={"hospital_id": hosp, "batch_id": sample_batch.name},
                )
                self.assertGreater(report.total_rows, 0)
                self.assertEqual(report.total_columns, 200)

                # Provider mapping check should pass for all valid hospital batches
                prov_rule = [r for r in report.rule_results if r.rule_id == "DQ-REF-001"][0]
                self.assertEqual(
                    prov_rule.status,
                    DataQualityStatus.PASS,
                    f"Provider mapping failed for {sample_batch.name}: {prov_rule.message}",
                )

    def test_38_claims_sample_and_summary_format(self):
        """Test 38: Claims master sample evaluated and summary output contains no PHI."""
        self.assertTrue(self.claims_master_file.exists())
        sample_df = pd.read_csv(self.claims_master_file, sep="|", nrows=500, dtype=str)
        hospital_mapping_df = pd.read_csv(self.hospital_mapping_file, dtype=str)

        report = evaluate_data_quality(
            dataset="claims",
            data=sample_df,
            reference_datasets={"hospital_mapping": hospital_mapping_df},
            schema_validation_result="PASS",
        )

        summary_text = format_quality_summary(report)
        self.assertIn("Data Quality Report", summary_text)
        self.assertIn("Rules Executed", summary_text)
        # Ensure raw beneficiary IDs are not printed in summary
        for bene in sample_df["BENE_ID"].dropna().unique()[:10]:
            if len(bene) > 4:
                self.assertNotIn(f"'{bene}'", summary_text)

    def test_39_ground_truth_scenario_validation(self):
        """
        Test 39: Full ground-truth anomaly detection comparison against anomaly_ground_truth.csv.
        Compares expected scenario counts from dataset metadata against actual referential integrity rule detection.
        Expected counts on the 24,154 scenario population:
          - VALID: 17,049
          - MISSING: 2,353
          - PROVIDER_MISMATCH: 1,214
          - EXPIRED: 1,205
          - NOT_YET_EFFECTIVE: 1,172
          - PROCEDURE_MISMATCH: 690
          - INVALID_STATUS: 471
        """
        if not self.ground_truth_file.exists() or not self.claims_master_file.exists() or not self.auth_file.exists():
            self.skipTest("Master data ground-truth files not present.")

        gt_df = pd.read_csv(self.ground_truth_file, dtype=str)
        auth_df = pd.read_csv(self.auth_file, dtype=str)
        claims_master = pd.read_csv(self.claims_master_file, sep="|", dtype=str)

        # Filter to the synthetic claims evaluated in ground truth
        scenario_claim_ids = set(gt_df["CLM_ID"].dropna().unique())
        synthetic_claims = claims_master[claims_master["CLM_ID"].isin(scenario_claim_ids)]

        # Evaluate referential integrity rule on synthetic scenario claims vs authorizations
        report = evaluate_data_quality(
            dataset="claims",
            data=synthetic_claims,
            reference_datasets={
                "authorization": auth_df,
                "ground_truth": gt_df,
            },
            context={"run_id": "ground_truth_validation_run"},
        )

        ref_rule = [r for r in report.rule_results if r.rule_id == "DQ-REF-002"][0]
        meta = ref_rule.metadata

        # Verify detection counts match exact ground-truth scenario definitions
        self.assertEqual(meta["missing_authorization_count"], 2353)
        self.assertEqual(meta["provider_mismatch_count"], 1214)
        self.assertEqual(meta["expired_authorization_count"], 1205)
        self.assertEqual(meta["not_yet_effective_count"], 1172)
        self.assertEqual(meta["procedure_mismatch_count"], 690)
        self.assertEqual(meta["invalid_status_count"], 471)

        total_anomalies_detected = (
            meta["missing_authorization_count"]
            + meta["provider_mismatch_count"]
            + meta["expired_authorization_count"]
            + meta["not_yet_effective_count"]
            + meta["procedure_mismatch_count"]
            + meta["invalid_status_count"]
        )
        self.assertEqual(total_anomalies_detected, 7105)
        self.assertEqual(meta["evaluated_claims"], 24154)


if __name__ == "__main__":
    unittest.main()
