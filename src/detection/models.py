from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.monitoring.models import AnomalyEvent


class InsufficientDataError(Exception):
    """
    Raised when a detection model lacks the necessary historical observations
    to reliably establish a baseline, preventing arbitrary or fabricated detection.
    """
    pass


class BaseDetector(ABC):
    """
    Abstract base class for all detection algorithms (Volume, Distribution, Ops).
    """

    @abstractmethod
    def detect(self, **kwargs) -> List[AnomalyEvent]:
        """
        Execute detection algorithm and return standard AnomalyEvent objects.
        Must raise InsufficientDataError if historical readiness is unmet.
        """
        pass
