import os
import yaml
from pathlib import Path
from src.pipeline.ingestion import IngestionService

def run_integration():
    # Load config
    config_path = Path("configs/pipeline_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    input_root = config["input_root"]
    active_run_id = config["active_run_id"]
    output_root = config["output_root"]
    delimiter = config["ingestion"]["delimiter"]

    # We will test on a restricted path (just hospital_A) to prevent full 1137 batch load for this quick validation
    # Actually, the discovery.py uses run_id. Let's just create a temporary run_id directory with symlinks or copy 1 batch.
    # To keep it simple, we will just run the full service. Polars reads 1137 small batches in ~2 seconds.
    print(f"Running integration test against: {input_root}/{active_run_id}")
    
    service = IngestionService(
        input_root=input_root,
        run_id=active_run_id,
        output_root=output_root,
        delimiter=delimiter
    )

    batches = service.run()
    
    print(f"Total batches ingested: {len(batches)}")
    
    total_records = sum(b.records_in for b in batches)
    print(f"Total records ingested: {total_records}")

    if len(batches) > 0:
        b0 = batches[0]
        print(f"Sample Batch: {b0.batch_id} | Hospital: {b0.hospital_id} | Records: {b0.records_in}")
        print(f"Sample Columns: {b0.source_columns}")
        print(f"Sample Types: {b0.dataframe.schema}")
        print(f"Ingestion Timestamp: {b0.ingestion_timestamp}")
        print(f"Service Date: {b0.service_date}")

if __name__ == "__main__":
    run_integration()
