"""
INGESTION LAYER - SYSTEM 1

This module provides the ingestion layer for the Representative Healthcare Pipeline.
It reads pipe-delimited simulated hospital batches from the master_data directory 
and produces a standardized `IngestedBatch` contract for the Validation Layer.

It does NOT perform schema validation, cleaning, transformation, or anomaly detection.
"""

from .models import IngestedBatch, DiscoveredBatchSource
from .service import IngestionService
from .errors import IngestionError, FileDiscoveryError, FileFormatError, IdempotencyError

__all__ = [
    "IngestedBatch",
    "DiscoveredBatchSource",
    "IngestionService",
    "IngestionError",
    "FileDiscoveryError",
    "FileFormatError",
    "IdempotencyError"
]
