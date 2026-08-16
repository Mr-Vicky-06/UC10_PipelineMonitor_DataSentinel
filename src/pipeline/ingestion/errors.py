class IngestionError(Exception):
    """Base exception for all ingestion-related errors."""
    pass

class FileDiscoveryError(IngestionError):
    """Raised when the expected batch files or directories cannot be found or accessed."""
    pass

class FileFormatError(IngestionError):
    """Raised when a discovered file does not meet the structural requirements (e.g., malformed format)."""
    pass

class IdempotencyError(IngestionError):
    """Raised when a batch has already been ingested and duplicate processing is attempted."""
    pass
