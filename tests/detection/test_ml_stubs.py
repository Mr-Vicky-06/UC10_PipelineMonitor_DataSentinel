import pytest
from src.detection.volume_detector import VolumeDetector
from src.detection.distribution_detector import DistributionDetector
from src.detection.operational_detector import OperationalDetector
from src.detection.models import InsufficientDataError

def test_volume_detector_stub():
    detector = VolumeDetector()
    with pytest.raises(InsufficientDataError, match="Insufficient historical operational data"):
        detector.detect()

def test_distribution_detector_stub():
    detector = DistributionDetector()
    with pytest.raises(InsufficientDataError, match="Insufficient historical operational data"):
        detector.detect()

def test_operational_detector_stub():
    detector = OperationalDetector()
    with pytest.raises(InsufficientDataError, match="Insufficient historical operational data"):
        detector.detect()
