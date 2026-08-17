class LandingError(Exception):
    """Base exception for all landing-related errors."""
    pass

class ConflictError(LandingError):
    """Raised when a destination file exists but has a different hash than the source."""
    pass

class PathViolationError(LandingError):
    """Raised when an operation attempts to read or write outside configured boundaries."""
    pass

class SourceNotFoundError(LandingError):
    """Raised when a source file is missing or inaccessible."""
    pass
