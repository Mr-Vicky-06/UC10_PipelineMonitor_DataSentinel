import os
import json
import logging
import datetime
from pathlib import Path
from typing import List, Dict, Any
import uuid
from .discovery import BatchDiscoverer
from .reader import BatchReader
from .models import DiscoveredBatchSource, IngestedBatch
from .errors import IdempotencyError, IngestionError
from src.pipeline.telemetry import PipelineTelemetryLogger, TelemetryEvent, PipelineStage, TelemetryStatus

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
        self.telemetry = PipelineTelemetryLogger.get_instance()

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

    def _telemetry_hook(self, batch: IngestedBatch, duration_sec: float, status: TelemetryStatus, correlation_id: str, error_msg: str = ""):
        """
        Emits structured telemetry to the operational DuckDB store.
        """
        event = TelemetryEvent(
            correlation_id=correlation_id,
            run_id=self.run_id,
            hospital_id=batch.hospital_id if batch else "",
            batch_id=batch.batch_id if batch else "",
            stage=PipelineStage.INGESTION,
            status=status,
            source_file=batch.source_file if batch else "",
            service_date=str(batch.service_date) if batch and batch.service_date else None,
            duration_ms=int(duration_sec * 1000),
            records_in=batch.records_in if batch else 0,
            records_out=batch.records_in if batch and status == TelemetryStatus.COMPLETED else 0,
            error_message=error_msg
        )
        self.telemetry.log_event(event)

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
            correlation_id = str(uuid.uuid4())
            
            # Log STARTED event
            start_event = TelemetryEvent(
                correlation_id=correlation_id,
                run_id=self.run_id,
                hospital_id=source.hospital_id,
                batch_id=source.batch_id,
                stage=PipelineStage.INGESTION,
                status=TelemetryStatus.STARTED,
                source_file=source.source_file,
                service_date=str(source.service_date)
            )
            self.telemetry.log_event(start_event)
            
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
                self._telemetry_hook(batch, duration, TelemetryStatus.COMPLETED, correlation_id)
                
                ingested_batches.append(batch)
                
            except IngestionError as e:
                logger.error(f"Ingestion failed for {batch_identity}: {e}")
                duration = (datetime.datetime.now() - start_time).total_seconds()
                # Log FAILED event with empty batch placeholder since it failed
                err_event = TelemetryEvent(
                    correlation_id=correlation_id,
                    run_id=self.run_id,
                    hospital_id=source.hospital_id,
                    batch_id=source.batch_id,
                    stage=PipelineStage.INGESTION,
                    status=TelemetryStatus.FAILED,
                    source_file=source.source_file,
                    service_date=str(source.service_date),
                    duration_ms=int(duration * 1000),
                    error_type="IngestionError",
                    error_message=str(e)
                )
                self.telemetry.log_event(err_event)
                
        return ingested_batches
