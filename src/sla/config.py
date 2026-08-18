from typing import Optional
from pydantic import BaseModel, Field

class SLAConfig(BaseModel):
    """Configuration for an SLA contract for a specific pipeline stage."""
    sla_id: str
    pipeline_name: str
    stage: str
    target_duration_seconds: float
    warning_margin_seconds: float
    enabled: bool = True

class SLAConfigManager:
    """
    Manages SLA configurations.
    For the prototype, this loads from local dictionaries.
    Production systems would load this from an external config registry.
    """
    def __init__(self):
        # Default prototype SLAs
        self.slas = {
            "ingestion_sla_1": SLAConfig(
                sla_id="ingestion_sla_1",
                pipeline_name="uc10_pipeline",
                stage="INGESTION",
                target_duration_seconds=300.0,
                warning_margin_seconds=60.0
            ),
            "transformation_sla_1": SLAConfig(
                sla_id="transformation_sla_1",
                pipeline_name="uc10_pipeline",
                stage="TRANSFORMATION",
                target_duration_seconds=600.0,
                warning_margin_seconds=120.0
            ),
            "landing_sla_1": SLAConfig(
                sla_id="landing_sla_1",
                pipeline_name="uc10_pipeline",
                stage="LANDING",
                target_duration_seconds=300.0,
                warning_margin_seconds=60.0
            )
        }
        
    def get_sla(self, pipeline_name: str, stage: str) -> Optional[SLAConfig]:
        """Returns the enabled SLA config for a given pipeline and stage if one exists."""
        for sla in self.slas.values():
            if sla.pipeline_name == pipeline_name and sla.stage == stage and sla.enabled:
                return sla
        return None
