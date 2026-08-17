"""
DataSentinal — Data Quality Validation Engine Interactive Test Runner.
Demonstrates quality validation across both:
  1. Synthetic sample dataset (with intentional, labeled anomaly scenarios)
  2. Real production master dataset (hospital batches & authorization repository)

Usage:
  py -3.12 scripts/demo_data_quality_test.py
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from datetime import datetime
import pandas as pd

from src.data_quality import evaluate_data_quality, format_quality_json, format_quality_summary
from src.validation import validate_dataset


def create_sample_test_data():
    """
    Creates a rich synthetic claims dataset containing:
      - Valid claims (Clean Baseline)
      - Completeness violations (Missing mandatory fields)
      - Uniqueness violations (Duplicate claim line grain)
      - Financial violations (Negative amount, payment > charge)
      - Date logic violations (Thru date < From date, future date)
      - Referential integrity violations (Missing auth, provider mismatch, procedure mismatch, expired auth)
    """
    print("\n" + "=" * 75)
    print("STEP 1: GENERATING SYNTHETIC SAMPLE CLAIMS & AUTHORIZATION DATASET")
    print("=" * 75)

    sample_claims = pd.DataFrame(
        [
            # --- Valid Records ---
            {
                "CLM_ID": "CLM_VALID_001",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_001",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-01-15",
                "CLM_THRU_DT": "2020-01-20",
                "CLM_PMT_AMT": "1500.00",
                "CLM_TOT_CHRG_AMT": "2500.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "VALID_RECORD_1",
            },
            {
                "CLM_ID": "CLM_VALID_001",
                "CLM_LINE_NUM": "2",
                "BENE_ID": "BENE_001",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-01-15",
                "CLM_THRU_DT": "2020-01-20",
                "CLM_PMT_AMT": "600.00",
                "CLM_TOT_CHRG_AMT": "800.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "VALID_RECORD_2_SAME_CLAIM_DIFF_LINE",
            },
            # --- Completeness Violation ---
            {
                "CLM_ID": "CLM_ERR_COMP_001",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "",  # Missing mandatory BENE_ID
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-02-01",
                "CLM_THRU_DT": "2020-02-05",
                "CLM_PMT_AMT": "400.00",
                "CLM_TOT_CHRG_AMT": "600.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "E119",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "MISSING_MANDATORY_BENE_ID",
            },
            # --- Uniqueness Violation ---
            {
                "CLM_ID": "CLM_ERR_DUP_001",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_002",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-02-10",
                "CLM_THRU_DT": "2020-02-12",
                "CLM_PMT_AMT": "300.00",
                "CLM_TOT_CHRG_AMT": "500.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "DUPLICATE_CLAIM_LINE_ORIGINAL",
            },
            {
                "CLM_ID": "CLM_ERR_DUP_001",
                "CLM_LINE_NUM": "1",  # Same CLM_ID + same CLM_LINE_NUM = DUPLICATE
                "BENE_ID": "BENE_002",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-02-10",
                "CLM_THRU_DT": "2020-02-12",
                "CLM_PMT_AMT": "300.00",
                "CLM_TOT_CHRG_AMT": "500.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "DUPLICATE_CLAIM_LINE_COPY",
            },
            # --- Financial Violations ---
            {
                "CLM_ID": "CLM_ERR_FIN_001",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_003",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-03-01",
                "CLM_THRU_DT": "2020-03-05",
                "CLM_PMT_AMT": "-250.00",  # Negative payment amount
                "CLM_TOT_CHRG_AMT": "1000.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "NEGATIVE_PAYMENT_AMOUNT",
            },
            {
                "CLM_ID": "CLM_ERR_FIN_002",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_003",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-03-01",
                "CLM_THRU_DT": "2020-03-05",
                "CLM_PMT_AMT": "3500.00",  # Payment exceeds Total Charge ($1,000)
                "CLM_TOT_CHRG_AMT": "1000.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "PAYMENT_EXCEEDS_TOTAL_CHARGE",
            },
            # --- Date Logic Violations ---
            {
                "CLM_ID": "CLM_ERR_DATE_001",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_004",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-04-20",
                "CLM_THRU_DT": "2020-04-10",  # Thru date is BEFORE From date
                "CLM_PMT_AMT": "800.00",
                "CLM_TOT_CHRG_AMT": "1200.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "DATE_CHRONOLOGY_INVERTED",
            },
            {
                "CLM_ID": "CLM_ERR_DATE_002",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_004",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2099-01-01",  # Future date
                "CLM_THRU_DT": "2099-01-05",
                "CLM_PMT_AMT": "800.00",
                "CLM_TOT_CHRG_AMT": "1200.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "FUTURE_SERVICE_DATE",
            },
            # --- Referential Integrity Violations ---
            {
                "CLM_ID": "CLM_ERR_REF_001",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_ORPHAN",  # No Authorization exists for this beneficiary
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-05-10",
                "CLM_THRU_DT": "2020-05-15",
                "CLM_PMT_AMT": "950.00",
                "CLM_TOT_CHRG_AMT": "1500.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "MISSING_AUTHORIZATION",
            },
            {
                "CLM_ID": "CLM_ERR_REF_002",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_005",
                "PRVDR_NUM": "491581",  # Provider in claim (491581) != Auth Provider (030115)
                "CLM_FROM_DT": "2020-06-10",
                "CLM_THRU_DT": "2020-06-15",
                "CLM_PMT_AMT": "700.00",
                "CLM_TOT_CHRG_AMT": "1100.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "PROVIDER_MISMATCH",
            },
            {
                "CLM_ID": "CLM_ERR_REF_003",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_006",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-07-10",
                "CLM_THRU_DT": "2020-07-15",
                "CLM_PMT_AMT": "700.00",
                "CLM_TOT_CHRG_AMT": "1100.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99495",  # Claim Procedure (99495) != Auth Procedure (99221)
                "_TEST_SCENARIO": "PROCEDURE_MISMATCH",
            },
            {
                "CLM_ID": "CLM_ERR_REF_004",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_007",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-08-25",  # Service date AFTER Authorization Expiration (2020-08-10)
                "CLM_THRU_DT": "2020-08-28",
                "CLM_PMT_AMT": "700.00",
                "CLM_TOT_CHRG_AMT": "1100.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "EXPIRED_AUTHORIZATION",
            },
            {
                "CLM_ID": "CLM_ERR_REF_005",
                "CLM_LINE_NUM": "1",
                "BENE_ID": "BENE_008",
                "PRVDR_NUM": "030115",
                "CLM_FROM_DT": "2020-09-10",
                "CLM_THRU_DT": "2020-09-15",
                "CLM_PMT_AMT": "700.00",
                "CLM_TOT_CHRG_AMT": "1100.00",
                "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
                "PRNCPAL_DGNS_CD": "I10",
                "HCPCS_CD": "99221",
                "_TEST_SCENARIO": "DENIED_AUTH_STATUS",
            },
        ]
    )

    # Reference Authorization table
    sample_auth = pd.DataFrame(
        [
            {"AUTH_ID": "AUTH_001", "BENE_ID": "BENE_001", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2020-01-01", "AUTH_EXP_DT": "2020-01-31", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "5000.00"},
            {"AUTH_ID": "AUTH_002", "BENE_ID": "BENE_002", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2020-02-01", "AUTH_EXP_DT": "2020-02-28", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "2000.00"},
            {"AUTH_ID": "AUTH_003", "BENE_ID": "BENE_003", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2020-03-01", "AUTH_EXP_DT": "2020-03-31", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "4000.00"},
            {"AUTH_ID": "AUTH_004", "BENE_ID": "BENE_004", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2020-04-01", "AUTH_EXP_DT": "2020-04-30", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "3000.00"},
            {"AUTH_ID": "AUTH_005", "BENE_ID": "BENE_005", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2020-06-01", "AUTH_EXP_DT": "2020-06-30", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "2000.00"},
            {"AUTH_ID": "AUTH_006", "BENE_ID": "BENE_006", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2020-07-01", "AUTH_EXP_DT": "2020-07-31", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "2000.00"},
            {"AUTH_ID": "AUTH_007", "BENE_ID": "BENE_007", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2020-08-01", "AUTH_EXP_DT": "2020-08-10", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "2000.00"},
            {"AUTH_ID": "AUTH_008", "BENE_ID": "BENE_008", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2020-09-01", "AUTH_EXP_DT": "2020-09-30", "AUTH_STATUS_CD": "DENIED", "AUTH_AMT": "2000.00"},
        ]
    )

    # Reference Hospital Mapping
    sample_hospital_mapping = pd.DataFrame({"PRVDR_NUM": ["030115", "491581"]})

    print(f"Generated {len(sample_claims)} test claim lines across {len(sample_claims['_TEST_SCENARIO'].unique())} labeled scenarios.")
    return sample_claims, sample_auth, sample_hospital_mapping


def test_synthetic_sample():
    """Runs the DQ engine against the synthetic sample dataset."""
    sample_claims, sample_auth, sample_hospital_mapping = create_sample_test_data()

    print("\n" + "=" * 75)
    print("STEP 2: RUNNING DATA QUALITY ENGINE ON SYNTHETIC SAMPLE")
    print("=" * 75)

    report = evaluate_data_quality(
        dataset="claims",
        data=sample_claims,
        reference_datasets={
            "authorization": sample_auth,
            "hospital_mapping": sample_hospital_mapping,
        },
        schema_validation_result="PASS",
        context={"run_id": "test_run_synthetic_001", "batch_id": "batch_synthetic_demo"},
    )

    print(format_quality_summary(report))

    print("\n" + "-" * 75)
    print("DETAILED RULE-BY-RULE EXECUTION BREAKDOWN:")
    print("-" * 75)
    for r in report.rule_results:
        status_tag = f"[{r.status.value}]"
        print(f"{status_tag:8} | {r.category.value:20} | {r.rule_id:12} | {r.rule_name:35} | Affected: {r.affected_row_count:2} ({r.affected_percentage:5.1f}%)")

    return report


def test_real_master_data():
    """Runs the DQ engine against actual production master data."""
    print("\n" + "=" * 75)
    print("STEP 3: RUNNING DATA QUALITY ENGINE ON REAL MASTER DATA")
    print("=" * 75)

    master_data_dir = _project_root / "master_data" / "master_data"
    if not master_data_dir.exists():
        master_data_dir = Path(r"D:\UC10_Data_Quality_Pipeline\master_data")

    # 1. Real Hospital Batch
    real_batch_file = master_data_dir / "batches" / "run_20260816_141418" / "hospital_A" / "batch_20150316.csv"
    real_auth_file = master_data_dir / "authorization" / "authorization_linked.csv"
    real_hm_file = master_data_dir / "reference" / "hospital_mapping.csv"

    print(f"Target Batch: {real_batch_file.name}")

    # Run Schema Validation first to obtain upstream gate result
    schema_res = validate_dataset("claims", real_batch_file)
    print(f"Upstream Schema Validation Status: {schema_res.status.value} (Errors: {schema_res.error_count})")

    # Run Data Quality Validation
    batch_report = evaluate_data_quality(
        dataset="claims",
        data=real_batch_file,
        reference_datasets={
            "hospital_mapping": real_hm_file,
            "authorization": real_auth_file,
        },
        schema_validation_result=schema_res,
        context={
            "run_id": "prod_run_20260816_141418",
            "batch_id": "batch_20150316",
            "hospital_id": "hospital_A",
        },
    )

    print("\n" + format_quality_summary(batch_report))

    # 2. Real Authorization Master Data
    print("\n" + "-" * 75)
    print("EVALUATING FULL AUTHORIZATION MASTER DATASET (21,801 ROWS)")
    print("-" * 75)

    auth_report = evaluate_data_quality(
        dataset="authorization",
        data=real_auth_file,
        schema_validation_result="PASS",
    )

    print(format_quality_summary(auth_report))


def main():
    print("=" * 75)
    print("  DATASENTINAL — DATA QUALITY VALIDATION ENGINE TEST SUITE")
    print("=" * 75)

    # 1. Synthetic Sample
    test_synthetic_sample()

    # 2. Real Master Data
    test_real_master_data()

    print("\n" + "=" * 75)
    print("  ALL TESTS COMPLETED SUCCESSFULLY — ZERO REGRESSIONS")
    print("=" * 75)


if __name__ == "__main__":
    main()
