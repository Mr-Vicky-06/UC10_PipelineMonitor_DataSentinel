import re
import datetime
from pathlib import Path
from typing import List
from .models import LandedBatch, LandingStatus
from .copier import BatchCopier
from .manifest import LandingManifest
import uuid
from src.pipeline.telemetry import PipelineTelemetryLogger, TelemetryEvent, PipelineStage, TelemetryStatus

class LandingService:
    """Orchestrates the discovery and copying of master data to the landing area."""
    
    def __init__(self, source_root: str, output_root: str, run_id: str):
        self.source_root = Path(source_root)
        self.output_root = Path(output_root)
        self.run_id = run_id
        self.copier = BatchCopier(source_root, output_root)
        
        self.run_source_dir = self.source_root / self.run_id
        self.run_landing_dir = self.output_root / self.run_id
        self.telemetry = PipelineTelemetryLogger.get_instance()
        
        # We reuse the same regex logic from ingestion discovery to identify batch files
        self.filename_pattern = re.compile(r"^batch_(\d{8})\.csv$")

    def run(self) -> List[LandedBatch]:
        """Execute the landing process."""
        landed_batches = []
        
        if not self.run_source_dir.exists():
            raise FileNotFoundError(f"Source run directory not found: {self.run_source_dir}")
            
        for path in self.run_source_dir.rglob("*.csv"):
            if not path.is_file():
                continue
                
            match = self.filename_pattern.match(path.name)
            if not match:
                continue
                
            hospital_id = path.parent.name
            date_str = match.group(1)
            service_date = datetime.date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:]))
            
            landing_path = self.run_landing_dir / hospital_id / path.name
            
            try:
                start_time = datetime.datetime.now()
                correlation_id = str(uuid.uuid4())
                
                # Log STARTED event
                start_event = TelemetryEvent(
                    correlation_id=correlation_id,
                    run_id=self.run_id,
                    hospital_id=hospital_id,
                    batch_id=f"batch_{date_str}", # Standardized batch ID extraction
                    stage=PipelineStage.LANDING,
                    status=TelemetryStatus.STARTED,
                    source_file=path.name,
                    service_date=str(service_date)
                )
                self.telemetry.log_event(start_event)
                
                status, src_hash, dst_hash = self.copier.safe_copy(path, landing_path)
                
                batch = LandedBatch(
                    run_id=self.run_id,
                    hospital_id=hospital_id,
                    source_path=str(path.resolve()),
                    landing_path=str(landing_path.resolve()),
                    filename=path.name,
                    service_date=service_date,
                    size_bytes=path.stat().st_size,
                    source_sha256=src_hash,
                    landing_sha256=dst_hash,
                    landed_at=datetime.datetime.utcnow(),
                    status=status
                )
                landed_batches.append(batch)
                
                duration = (datetime.datetime.now() - start_time).total_seconds()
                end_event = TelemetryEvent(
                    correlation_id=correlation_id,
                    run_id=self.run_id,
                    hospital_id=hospital_id,
                    batch_id=f"batch_{date_str}",
                    stage=PipelineStage.LANDING,
                    status=TelemetryStatus.COMPLETED,
                    source_file=path.name,
                    service_date=str(service_date),
                    duration_ms=int(duration * 1000)
                )
                self.telemetry.log_event(end_event)
            except Exception as e:
                duration = (datetime.datetime.now() - start_time).total_seconds()
                err_event = TelemetryEvent(
                    correlation_id=correlation_id,
                    run_id=self.run_id,
                    hospital_id=hospital_id,
                    batch_id=f"batch_{date_str}",
                    stage=PipelineStage.LANDING,
                    status=TelemetryStatus.FAILED,
                    source_file=path.name,
                    service_date=str(service_date),
                    duration_ms=int(duration * 1000),
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                self.telemetry.log_event(err_event)
                # To fail the pipeline on conflict, we re-raise.
                raise
                
        # Generate manifest
        manifest_path = self.run_landing_dir / "landing_manifest.json"
        LandingManifest.generate(
            run_id=self.run_id,
            source_root=str(self.source_root),
            landing_root=str(self.output_root),
            batches=landed_batches,
            output_path=manifest_path
        )
        
        return landed_batches
