import os
import json
import hashlib
import uuid
import datetime
import time
from pathlib import Path
import pandas as pd
import duckdb

from src.pipeline.landing.service import LandingService
from src.pipeline.ingestion.service import IngestionService
from src.cleaning.pipeline import validate_dataset, clean_dataset
from src.pipeline.transformation import HealthcareTransformer
from src.business_rules.engine import BusinessRuleEngine
from src.business_rules.phase_c_rules import ICDValidityRule, HCPCSValidityRule, BeneficiaryIntegrityRule, ProviderIntegrityRule, AuthorizationMatchRule
from src.business_rules.rules import ClaimChronologyRule, AdmissionDischargeRule, NegativeAmountRule, PaymentChargeBalanceRule
from src.pipeline.storage.duckdb_store import ProcessedClaimsStore
from src.pipeline.telemetry import PipelineTelemetryLogger, TelemetryEvent, PipelineStage, TelemetryStatus

def get_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_50k_pipeline():
    print("======================================================================")
    print("DATASENTINEL 50,000 RECORD PIPELINE EXECUTION & TELEMETRY FUSION")
    print("======================================================================")
    
    start_time = time.time()
    
    # 0. Setup directories
    workspace_dir = Path("outputs/pipeline_workspace/run_50k")
    if workspace_dir.exists():
        import shutil
        shutil.rmtree(workspace_dir)
        
    source_dir = workspace_dir / "source"
    run_id = "RUN_50K_LIVE_MASSIVE"
    hosp_dir = source_dir / run_id / "HOSP-MASSIVE"
    hosp_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Read 50,000 records from immutable raw data
    src_file = "data/raw/claims/inpatient.csv"
    print(f"\n[1/6] Reading 50,000 rows from raw data: {src_file}...")
    df_50k = pd.read_csv(src_file, sep="|", dtype=str, nrows=50000)
    print(f"-> Successfully loaded {len(df_50k):,} records.")
    
    # Save landing batch file
    batch_file = hosp_dir / "batch_20260101.csv"
    df_50k.to_csv(batch_file, sep="|", index=False)
    
    run_id = "RUN_50K_LIVE_MASSIVE"
    
    # 2. Landing
    print("\n[2/6] Executing Landing Stage...")
    landing_svc = LandingService(
        source_root=str(source_dir),
        output_root=str(workspace_dir / "landed"),
        run_id=run_id
    )
    landed_batches = landing_svc.run()
    print(f"-> Landed {len(landed_batches)} batch(es).")
    
    # 3. Ingestion
    print("\n[3/6] Executing Ingestion Stage...")
    ingestion_svc = IngestionService(
        input_root=str(workspace_dir / "landed"),
        run_id=run_id,
        output_root=str(workspace_dir / "ingested")
    )
    ingested_batches = ingestion_svc.run()
    print(f"-> Ingested {len(ingested_batches)} batch(es).")
    
    # 4. Data Quality Validation & Cleaning
    print("\n[4/6] Executing Data Quality Rules & Data Cleaning Engine...")
    df_ingest_pd = ingested_batches[0].dataframe.to_pandas()
    cleaning_res = clean_dataset('claims', df_ingest_pd, run_schema_validation=False)
    cleaned_df = cleaning_res.cleaned_df
    metrics = getattr(cleaning_res, 'metrics', None) or getattr(cleaning_res.report, 'metrics', None)
    dq_violations_count = getattr(metrics, 'unresolved_records', 0) if metrics else 0
    print(f"-> Cleaning complete. {len(cleaned_df):,} records validated. DQ Violations: {dq_violations_count}")
    
    # 5. Healthcare Transformation
    print("\n[5/6] Executing Healthcare Claims Transformation...")
    transformer = HealthcareTransformer()
    transformed_df, transform_metrics = transformer.transform_claims(cleaned_df, batch_id='50K_CARRIER_BATCH_001')
    print(f"-> Standardized {len(transformed_df):,} records to canonical schema.")
    
    # 6. Business Rules Engine & DuckDB Storage + Telemetry Logging
    print("\n[6/6] Executing Business Rules Engine & Telemetry Fusion Store...")
    engine = BusinessRuleEngine([
        ClaimChronologyRule(),
        AdmissionDischargeRule(),
        NegativeAmountRule(),
        PaymentChargeBalanceRule(),
        ICDValidityRule(),
        HCPCSValidityRule(),
        BeneficiaryIntegrityRule(),
        ProviderIntegrityRule(),
        AuthorizationMatchRule()
    ])
    rule_results = engine.execute((transformed_df, transform_metrics), run_id=run_id)
    
    # Store to DuckDB
    store = ProcessedClaimsStore(db_path="outputs/pipeline_workspace/processed_claims.duckdb")
    store.save(transformed_df, rule_results, run_id=run_id, hospital_id="HOSP-MASSIVE", batch_id="50K_CARRIER_BATCH_001")
    
    # Log Telemetry
    telemetry_db = "outputs/pipeline_workspace/pipeline_telemetry.duckdb"
    telemetry = PipelineTelemetryLogger(db_path=telemetry_db)
    
    duration = time.time() - start_time
    
    event = TelemetryEvent(
        correlation_id=str(uuid.uuid4()),
        run_id=run_id,
        hospital_id="HOSP-MASSIVE",
        batch_id="50K_CARRIER_BATCH_001",
        stage=PipelineStage.STORAGE,
        status=TelemetryStatus.COMPLETED,
        source_file="inpatient.csv",
        records_in=len(df_50k),
        records_out=len(transformed_df),
        records_failed=dq_violations_count,
        violations_count=dq_violations_count,
        duration_ms=int(duration * 1000)
    )
    telemetry.log_event(event)
    
    print("\n======================================================================")
    print(f"SUCCESS: Processed {len(transformed_df):,} records in {duration:.2f} seconds!")
    print(f"Throughput: {len(df_50k) / max(duration, 0.1):,.2f} rows/sec")
    print("======================================================================")

if __name__ == "__main__":
    run_50k_pipeline()
