import os
import time
import uuid
import datetime
import traceback
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from src.pipeline.landing.service import LandingService
from src.pipeline.ingestion.service import IngestionService
from src.pipeline.ingestion.errors import IdempotencyError
from src.cleaning.pipeline import clean_dataset
from src.pipeline.transformation import HealthcareTransformer
from src.business_rules.engine import BusinessRuleEngine
from src.business_rules.phase_c_rules import ICDValidityRule, HCPCSValidityRule, BeneficiaryIntegrityRule, ProviderIntegrityRule, AuthorizationMatchRule
from src.business_rules.rules import ClaimChronologyRule, AdmissionDischargeRule, NegativeAmountRule, PaymentChargeBalanceRule
from src.pipeline.storage.duckdb_store import ProcessedClaimsStore
from src.pipeline.telemetry.logger import PipelineTelemetryLogger, setup_pipeline_logging


@dataclass
class PipelineRunResult:
    run_id: str
    is_successful: bool
    records_received: int = 0
    records_persisted: int = 0
    business_rule_violations: int = 0
    operational_errors: int = 0
    duration_ms: int = 0
    error_message: Optional[str] = None
    batch_results: List[Dict] = field(default_factory=list)

class PipelineOrchestrator:
    def __init__(self, config_path: str = "src/pipeline/config.yaml"):
        self.config_path = config_path
        
        # Hardcoding the default paths for now matching the existing local structure
        # In a real environment these would be read from config.yaml
        self.landing_output = "outputs/pipeline_workspace/landing"
        self.ingestion_output = "outputs/pipeline_workspace/ingestion"
        self.duckdb_path = "outputs/pipeline_workspace/processed_claims.duckdb"

    def run(self, source_directory: str, run_id: str) -> PipelineRunResult:
        setup_pipeline_logging()
        start_time = time.time()
        result = PipelineRunResult(run_id=run_id, is_successful=False)
        
        try:
            # 1. LANDING
            landing = LandingService(source_root=source_directory, output_root=self.landing_output, run_id=run_id)
            landed_batches = landing.run()
            
            # 2. INGESTION
            ingestion = IngestionService(input_root=self.landing_output, output_root=self.ingestion_output, run_id=run_id)
            try:
                ingested_batches = ingestion.run()
            except IdempotencyError as e:
                result.is_successful = True
                result.error_message = f"Idempotency skip: {str(e)}"
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result
                
            if not ingested_batches:
                result.is_successful = True
                result.error_message = "No batches ingested"
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

            # Process each batch
            for batch in ingested_batches:
                batch_res = {"batch_id": batch.batch_id, "hospital_id": batch.hospital_id, "records_received": 0, "records_persisted": 0}
                df_ingest = batch.dataframe
                if df_ingest.is_empty():
                    continue
                    
                records_received = len(df_ingest)
                result.records_received += records_received
                batch_res["records_received"] = records_received
                
                # Convert to pandas for downstream consistency
                df_ingest_pd = df_ingest.to_pandas()
                
                # We enforce the claim grain: CLM_ID + CLM_LINE_NUM
                # In real scenario, we shouldn't necessarily drop, but validation handles it.

                # 3. VALIDATION & CLEANING
                cleaning_res = clean_dataset(
                    dataset="claims",
                    input_path_or_df=df_ingest_pd,
                    run_schema_validation=True,
                    run_id=run_id
                )
                
                if not cleaning_res.passed:
                    raise RuntimeError(f"Validation/Cleaning failed for batch {batch.batch_id}")
                    
                df_clean = cleaning_res.cleaned_df
                
                # 4. TRANSFORMATION
                transformer = HealthcareTransformer(config_path=self.config_path)
                df_transform, transform_meta = transformer.transform_claims(
                    df_clean, 
                    batch_id=batch.batch_id, 
                    source_file=batch.source_file, 
                    run_id=run_id
                )
                
                # 5. BUSINESS RULES
                engine = BusinessRuleEngine([
                    ClaimChronologyRule(), AdmissionDischargeRule(), NegativeAmountRule(), PaymentChargeBalanceRule(),
                    ICDValidityRule(), HCPCSValidityRule(), BeneficiaryIntegrityRule(), ProviderIntegrityRule(), AuthorizationMatchRule()
                ])
                br_result = engine.execute((df_transform, transform_meta), run_id=run_id)
                
                result.business_rule_violations += len(br_result.violations)
                
                # 6. STORAGE
                store = ProcessedClaimsStore(db_path=self.duckdb_path)
                store.save(
                    df_transformed=df_transform,
                    rule_result=br_result,
                    run_id=run_id,
                    hospital_id=batch.hospital_id,
                    batch_id=batch.batch_id,
                    source_file=batch.source_file
                )
                
                records_persisted = len(df_transform)
                result.records_persisted += records_persisted
                batch_res["records_persisted"] = records_persisted
                result.batch_results.append(batch_res)

            result.is_successful = True
            
        except Exception as e:
            result.is_successful = False
            result.error_message = f"{type(e).__name__}: {str(e)}"
            result.operational_errors += 1
            # traceback.print_exc()
            
        finally:
            result.duration_ms = int((time.time() - start_time) * 1000)
            
        return result
