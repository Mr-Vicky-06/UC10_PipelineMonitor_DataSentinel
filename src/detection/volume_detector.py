from typing import List, Dict, Any

from src.monitoring.models import AnomalyEvent
from src.detection.models import BaseDetector, InsufficientDataError

class VolumeDetector(BaseDetector):
    """
    Phase 4B Healthcare Behaviour / Volume Detector.
    Monitors the physical volume of entities (claims, beneficiaries, providers).
    Current candidate algorithm: Rolling Median + MAD.
    """
    
    def detect(self, **kwargs) -> List[AnomalyEvent]:
        """
        Executes volume anomaly detection.
        Currently BLOCKED due to insufficient historical telemetry observations.
        """
        raise InsufficientDataError(
            "Volume detection blocked: Insufficient historical operational data to establish a volume baseline. "
            "Model training and detection cannot proceed without fabricating data."
        )
