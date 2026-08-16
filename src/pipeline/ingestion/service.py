import os
import json
import logging
import datetime
from pathlib import Path
from typing import List, Dict, Any
from .discovery import BatchDiscoverer
from .reader import BatchReader
from .models import DiscoveredBatchSource, IngestedBatch
from .errors import IdempotencyError, IngestionError

# Basic logging setup for ingestion
logging.basicConfig(level=logging.INFO, format="%(asctime)s - INGESTION - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class IngestionService:
    """
    Orchestrates the ingestion layer workflow:
    1. Discovers files.
    2. Checks idempotency.
    3. Reads files into IngestedBatch objects.
    4. Records idempotency state.
    5. Emits telemetry hooks.
    """
    def __init__(self, input_root: str, run_id: str, output_root: str, delimiter: str = "|"):
        self.input_root = input_root
        self.run_id = run_id
        self.output_root = Path(output_root)
        self.delimiter = delimiter
        self.state_file = self.output_root / "ingestion_state.json"
        
        # Ensure output workspace exists
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._state_cache: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads idempotency state from JSON."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def _save_state(self):
        """Saves idempotency state to JSON."""
        with open(self.state_file, "w") as f:
            json.dump(self._state_cache, f, indent=2)

    def _get_batch_identity(self, source: DiscoveredBatchSource) -> str:
        """Deterministic identity for idempotency."""
        return f"{source.hospital_id}::{source.batch_id}"

    def _telemetry_hook(self, batch: IngestedBatch, duration_sec: float):
        """
        Integration point for future telemetry developer.
        Captures essential metadata per the contract.
        """
        # Downstream developers can replace this with OpenTelemetry/Prometheus logic
        metadata = {
            "batch_id": batch.batch_id,
            "hospital_id": batch.hospital_id,
            "source_file": batch.source_file,
            "service_date": str(batch.service_date),
            "ingestion_timestamp": str(batch.ingestion_timestamp),
            "records_in": batch.records_in,
            "duration_sec": duration_sec,
            "status": batch.ingestion_status
        }
        logger.info(f"Telemetry Event Emit: {metadata}")

    def run(self) -> List[IngestedBatch]:
        """
        Executes the ingestion pipeline.
        Returns a list of IngestedBatch objects for downstream validation.
        """
        discoverer = BatchDiscoverer(self.input_root, self.run_id, delimiter=self.delimiter)
        discovered_sources = discoverer.discover()
        
        logger.info(f"Discovered {len(discovered_sources)} potential batch files.")
        
        ingested_batches = []
        
        for source in discovered_sources:
            batch_identity = self._get_batch_identity(source)
            
            if batch_identity in self._state_cache:
                logger.warning(f"Idempotency skip: {batch_identity} has already been ingested.")
                continue
                
            logger.info(f"Ingesting {batch_identity}...")
            start_time = datetime.datetime.now()
            
            try:
                # Use the reader to load the dataframe
                batch = BatchReader.read(source)
                
                # Mark as processed
                self._state_cache[batch_identity] = {
                    "ingestion_timestamp": str(batch.ingestion_timestamp),
                    "source_file": batch.source_file,
                    "records_in": batch.records_in
                }
                self._save_state()
                
                # Emit telemetry
                duration = (datetime.datetime.now() - start_time).total_seconds()
                self._telemetry_hook(batch, duration)
                
                ingested_batches.append(batch)
                
            except IngestionError as e:
                logger.error(f"Ingestion failed for {batch_identity}: {e}")
                # We log the error but allow the pipeline to continue with other files.
                # A production system might route this to a Dead Letter Queue.
                
        return ingested_batches
