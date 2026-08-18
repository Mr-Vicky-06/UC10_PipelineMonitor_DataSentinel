import time
from typing import Optional, Dict, Any
from src.sla.config import SLAConfig
from src.sla.evidence import SLAObservation

class SLACalculator:
    """Calculates ETA and SLA status based on current pipeline metrics."""
    
    @staticmethod
    def calculate(
        config: SLAConfig,
        run_id: str,
        start_time: float,
        current_time: float,
        expected_records: Optional[int],
        processed_records: Optional[int],
        stage_status: str = "RUNNING",
        batch_id: Optional[str] = None,
        hospital_id: Optional[str] = None
    ) -> SLAObservation:
        
        elapsed = max(0.0, current_time - start_time)
        sla_deadline = start_time + config.target_duration_seconds
        warning_threshold_time = sla_deadline - config.warning_margin_seconds
        
        # Base observation
        obs = SLAObservation(
            sla_id=config.sla_id,
            run_id=run_id,
            stage=config.stage,
            status="UNKNOWN",
            expected_records=expected_records,
            processed_records=processed_records,
            elapsed_seconds=elapsed,
            sla_deadline=sla_deadline,
            batch_id=batch_id,
            hospital_id=hospital_id,
            timestamp=current_time
        )
        
        # Determine UNKNOWN states
        if expected_records is None or expected_records < 0:
            obs.status = "UNKNOWN"
            return obs
            
        if processed_records is None or processed_records < 0:
            obs.status = "UNKNOWN"
            return obs
            
        remaining_records = expected_records - processed_records
        obs.remaining_records = remaining_records
        
        # Handle completed or failed stages
        if stage_status == "COMPLETED" or remaining_records <= 0:
            obs.remaining_records = 0
            obs.estimated_remaining_seconds = 0.0
            obs.estimated_completion_time = current_time
            obs.sla_margin_seconds = sla_deadline - current_time
            if current_time > sla_deadline:
                obs.status = "BREACHED"
            else:
                obs.status = "ON_TRACK"
            return obs
            
        if stage_status == "FAILED":
            # If the stage failed, it will never complete, but it missed its SLA.
            obs.status = "UNKNOWN"
            return obs

        # Zero throughput handling
        if processed_records == 0 or elapsed == 0:
            obs.throughput = 0.0
            obs.status = "UNKNOWN" # Cannot project without throughput
            return obs
            
        # Calculate ETA
        throughput = processed_records / elapsed
        obs.throughput = throughput
        
        estimated_remaining_seconds = remaining_records / throughput
        obs.estimated_remaining_seconds = estimated_remaining_seconds
        
        estimated_completion = current_time + estimated_remaining_seconds
        obs.estimated_completion_time = estimated_completion
        
        sla_margin = sla_deadline - estimated_completion
        obs.sla_margin_seconds = sla_margin
        
        # Status classification
        if estimated_completion <= warning_threshold_time:
            obs.status = "ON_TRACK"
        elif estimated_completion <= sla_deadline:
            obs.status = "AT_RISK"
        else:
            obs.status = "BREACHED"
            
        return obs
