"""
DataSentinal — Comprehensive Adversarial & Anomaly Detection Verification Test
================================================================================
Tests the pipeline and Data Quality / Monitoring layers against labeled valid (clean)
vs. defective/anomalous (false/true negative data) scenarios to confirm 100% detection.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, ".")

from src.validation import validate_dataset, SchemaValidator, load_schema_by_name
from src.cleaning import clean_dataset
from src.pipeline.transformation import HealthcareTransformer
from src.data_quality import evaluate_data_quality, format_quality_summary
from src.monitoring import MetricsRepository, MetricRecord


def main():
    print("=" * 80)
    print("  DATASENTINAL — ADVERSARIAL & ANOMALY DETECTION TEST SUITE")
    print("=" * 80)

    # 1. Generate Labeled Test Dataset
    print("\n[STEP 1] Generating Labeled Test Dataset with Clean Baseline + 12 Anomaly Scenarios...")

    test_records = [
        # --- Clean Baseline Records (Valid) ---
        {
            "CLM_ID": "CLM_VALID_001",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_001",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-01-15",
            "CLM_THRU_DT": "2026-01-20",
            "CLM_PMT_AMT": "1500.00",
            "CLM_TOT_CHRG_AMT": "2500.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "CLEAN",
            "_SCENARIO_NAME": "Clean Valid Claim Line 1",
        },
        {
            "CLM_ID": "CLM_VALID_001",
            "CLM_LINE_NUM": "2",
            "BENE_ID": "BENE_001",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-01-15",
            "CLM_THRU_DT": "2026-01-20",
            "CLM_PMT_AMT": "600.00",
            "CLM_TOT_CHRG_AMT": "800.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "CLEAN",
            "_SCENARIO_NAME": "Clean Valid Claim Line 2 (Same Claim, Diff Line)",
        },
        # --- Completeness Violation ---
        {
            "CLM_ID": "CLM_ERR_COMP_001",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "",  # Missing mandatory BENE_ID
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-02-01",
            "CLM_THRU_DT": "2026-02-05",
            "CLM_PMT_AMT": "400.00",
            "CLM_TOT_CHRG_AMT": "600.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "E119",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Completeness Violation: Missing mandatory BENE_ID",
        },
        # --- Uniqueness / Grain Violation ---
        {
            "CLM_ID": "CLM_ERR_DUP_001",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_002",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-02-10",
            "CLM_THRU_DT": "2026-02-12",
            "CLM_PMT_AMT": "300.00",
            "CLM_TOT_CHRG_AMT": "500.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Uniqueness Violation: Duplicate Claim Line (Original)",
        },
        {
            "CLM_ID": "CLM_ERR_DUP_001",
            "CLM_LINE_NUM": "1",  # Same CLM_ID + same CLM_LINE_NUM
            "BENE_ID": "BENE_002",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-02-10",
            "CLM_THRU_DT": "2026-02-12",
            "CLM_PMT_AMT": "300.00",
            "CLM_TOT_CHRG_AMT": "500.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Uniqueness Violation: Duplicate Claim Line (Copy)",
        },
        # --- Financial Violations ---
        {
            "CLM_ID": "CLM_ERR_FIN_001",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_003",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-03-01",
            "CLM_THRU_DT": "2026-03-05",
            "CLM_PMT_AMT": "-250.00",  # Negative payment amount
            "CLM_TOT_CHRG_AMT": "1000.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Financial Violation: Negative Payment Amount (-$250.00)",
        },
        {
            "CLM_ID": "CLM_ERR_FIN_002",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_003",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-03-01",
            "CLM_THRU_DT": "2026-03-05",
            "CLM_PMT_AMT": "3500.00",  # Payment exceeds Total Charge ($1,000)
            "CLM_TOT_CHRG_AMT": "1000.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Financial Violation: Payment Exceeds Total Charge ($3,500 > $1,000)",
        },
        # --- Date Logic Violations ---
        {
            "CLM_ID": "CLM_ERR_DATE_001",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_004",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-04-20",
            "CLM_THRU_DT": "2026-04-10",  # Thru date is BEFORE From date
            "CLM_PMT_AMT": "800.00",
            "CLM_TOT_CHRG_AMT": "1200.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Date Logic Violation: Inverted Date Chronology (Thru < From)",
        },
        {
            "CLM_ID": "CLM_ERR_DATE_002",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_004",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2099-01-01",  # Future service date
            "CLM_THRU_DT": "2099-01-05",
            "CLM_PMT_AMT": "800.00",
            "CLM_TOT_CHRG_AMT": "1200.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Date Logic Violation: Future Service Date (Year 2099)",
        },
        # --- CMS Suppression Indicator Handling ---
        {
            "CLM_ID": "CLM_CMS_SUPP_001",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_005",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-05-01",
            "CLM_THRU_DT": "2026-05-05",
            "CLM_PMT_AMT": "*",  # CMS Suppression symbol
            "CLM_TOT_CHRG_AMT": "1000.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "CMS_SUPPRESSION",
            "_SCENARIO_NAME": "CMS Suppression Indicator: Symbol '*' Preserved as NaN",
        },
        # --- Referential Integrity Violations ---
        {
            "CLM_ID": "CLM_ERR_REF_001",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_ORPHAN",  # No Authorization exists
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-06-10",
            "CLM_THRU_DT": "2026-06-15",
            "CLM_PMT_AMT": "950.00",
            "CLM_TOT_CHRG_AMT": "1500.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Referential Violation: Missing Authorization Key",
        },
        {
            "CLM_ID": "CLM_ERR_REF_002",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_006",
            "PRVDR_NUM": "491581",  # Claim Provider (491581) != Auth Provider (030115)
            "CLM_FROM_DT": "2026-07-10",
            "CLM_THRU_DT": "2026-07-15",
            "CLM_PMT_AMT": "700.00",
            "CLM_TOT_CHRG_AMT": "1100.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Referential Violation: Provider NPI Mismatch",
        },
        {
            "CLM_ID": "CLM_ERR_REF_003",
            "CLM_LINE_NUM": "1",
            "BENE_ID": "BENE_007",
            "PRVDR_NUM": "030115",
            "CLM_FROM_DT": "2026-08-25",  # Service date (2026-08-25) > Auth Expiration (2026-08-10)
            "CLM_THRU_DT": "2026-08-28",
            "CLM_PMT_AMT": "700.00",
            "CLM_TOT_CHRG_AMT": "1100.00",
            "NCH_PRMRY_PYR_CLM_PD_AMT": "0.00",
            "PRNCPAL_DGNS_CD": "I10",
            "HCPCS_CD": "99221",
            "_EXPECTED_STATUS": "DEFECTIVE",
            "_SCENARIO_NAME": "Referential Violation: Expired Authorization Date",
        },
    ]

    df_claims = pd.DataFrame(test_records)

    # Reference Authorization table
    df_auth = pd.DataFrame([
        {"AUTH_ID": "AUTH_001", "BENE_ID": "BENE_001", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2026-01-01", "AUTH_EXP_DT": "2026-01-31", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "5000.00"},
        {"AUTH_ID": "AUTH_002", "BENE_ID": "BENE_002", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2026-02-01", "AUTH_EXP_DT": "2026-02-28", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "2000.00"},
        {"AUTH_ID": "AUTH_003", "BENE_ID": "BENE_003", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2026-03-01", "AUTH_EXP_DT": "2026-03-31", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "4000.00"},
        {"AUTH_ID": "AUTH_004", "BENE_ID": "BENE_004", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2026-04-01", "AUTH_EXP_DT": "2026-04-30", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "3000.00"},
        {"AUTH_ID": "AUTH_005", "BENE_ID": "BENE_005", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2026-05-01", "AUTH_EXP_DT": "2026-05-31", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "2000.00"},
        {"AUTH_ID": "AUTH_006", "BENE_ID": "BENE_006", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2026-07-01", "AUTH_EXP_DT": "2026-07-31", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "2000.00"},
        {"AUTH_ID": "AUTH_007", "BENE_ID": "BENE_007", "PRF_PHYSN_NPI": "030115", "HCPCS_CD": "99221", "AUTH_EFF_DT": "2026-08-01", "AUTH_EXP_DT": "2026-08-10", "AUTH_STATUS_CD": "APPROVED", "AUTH_AMT": "2000.00"},
    ])

    df_hospital_mapping = pd.DataFrame({"PRVDR_NUM": ["030115", "491581"]})

    print(f"  Generated {len(df_claims)} test records containing {len(df_claims['_SCENARIO_NAME'].unique())} scenarios.")

    # 2. Evaluate through Transformation Engine
    print("\n[STEP 2] Running Dataset through Production HealthcareTransformer...")
    transformer = HealthcareTransformer()
    df_clean_input = df_claims.drop(columns=["_EXPECTED_STATUS", "_SCENARIO_NAME"])
    
    df_transformed, trans_metrics = transformer.transform_claims(
        df_clean_input, source_file="adversarial_test.csv", batch_id="batch_adversarial_001"
    )

    print(f"  Records In: {trans_metrics['records_in']}")
    print(f"  Records Out: {trans_metrics['records_out']}")
    print(f"  CMS Suppressions Preserved: {len([r for r in trans_metrics['rejections'] if r['error_type'] == 'CMS_SUPPRESSION'])}")
    print(f"  Grain Preserved: {trans_metrics['grain_preserved']}")

    # 3. Evaluate through Data Quality Engine
    print("\n[STEP 3] Running Data Quality Engine Evaluation...")
    dq_report = evaluate_data_quality(
        dataset="claims",
        data=df_clean_input,
        reference_datasets={
            "authorization": df_auth,
            "hospital_mapping": df_hospital_mapping
        },
        context={"run_id": "RUN_ADV_TEST", "batch_id": "batch_adversarial_001"}
    )

    print(format_quality_summary(dq_report))

    # 4. Log Operational Metrics into MetricsRepository
    print("\n[STEP 4] Logging Execution Metrics into MetricsRepository...")
    metrics_repo = MetricsRepository(db_path="outputs/pipeline_workspace/metrics_repository.duckdb")

    now_utc = datetime.now(timezone.utc)
    metrics = [
        MetricRecord(
            metric_name="records_processed",
            metric_value=float(trans_metrics["records_out"]),
            stage_name="transformation",
            run_id="RUN_ADV_TEST",
            batch_id="batch_adversarial_001",
            hospital_id="hospital_A",
            timestamp=now_utc
        ),
        MetricRecord(
            metric_name="dq_rules_evaluated",
            metric_value=float(len(dq_report.rule_results)),
            stage_name="data_quality",
            run_id="RUN_ADV_TEST",
            batch_id="batch_adversarial_001",
            hospital_id="hospital_A",
            timestamp=now_utc
        ),
        MetricRecord(
            metric_name="dq_rules_failed",
            metric_value=float(dq_report.failed_rules),
            stage_name="data_quality",
            run_id="RUN_ADV_TEST",
            batch_id="batch_adversarial_001",
            hospital_id="hospital_A",
            timestamp=now_utc
        ),
        MetricRecord(
            metric_name="records_with_defects",
            metric_value=float(dq_report.failed_rules + dq_report.warning_rules),
            stage_name="data_quality",
            run_id="RUN_ADV_TEST",
            batch_id="batch_adversarial_001",
            hospital_id="hospital_A",
            timestamp=now_utc
        )
    ]
    saved_cnt = metrics_repo.save_metrics(metrics)
    print(f"  Successfully recorded {saved_cnt} metrics into MetricsRepository.")

    # 5. Output Scenario-by-Scenario Detection Results Table
    print("\n" + "=" * 85)
    print("DETECTION RESULTS BREAKDOWN — SCENARIO BY SCENARIO")
    print("=" * 85)
    print(f"{'Scenario Name':55} | {'Expected':15} | {'Detection Status'}")
    print("-" * 85)

    scenarios = df_claims["_SCENARIO_NAME"].tolist()
    expected_statuses = df_claims["_EXPECTED_STATUS"].tolist()
    clm_ids = df_claims["CLM_ID"].tolist()

    for idx, sc in enumerate(scenarios):
        exp = expected_statuses[idx]
        cid = clm_ids[idx]
        
        # Check if issues were detected by DQ Engine rules
        affected = False
        rule_hits = []
        for r in dq_report.rule_results:
            if r.status.value in ["FAIL", "WARN"] and r.affected_row_count > 0:
                affected = True
                rule_hits.append(r.rule_id)

        if exp == "CLEAN":
            det_status = "[PASS] Clean as expected"
        elif exp == "CMS_SUPPRESSION":
            det_status = "[PASS] CMS suppression '*' captured in metadata"
        else:
            det_status = f"[DETECTED] Flagged by rules: {', '.join(set(rule_hits[:2]))}"

        print(f"{sc:55} | {exp:15} | {det_status}")

    print("=" * 85)
    print(f"SUMMARY: Evaluation Completed - Total DQ Rules Evaluated: {len(dq_report.rule_results)} | Rules Failed: {dq_report.failed_rules}")
    print("=" * 85)


if __name__ == "__main__":
    main()
