import os
import shutil
import hashlib
from pathlib import Path
from typing import Tuple
from .errors import ConflictError, SourceNotFoundError, PathViolationError
from .models import LandingStatus

class BatchCopier:
    """Handles secure, verifiable copying of batch files from source to landing."""
    
    def __init__(self, source_root: str, landing_root: str):
        self.source_root = Path(source_root).resolve()
        self.landing_root = Path(landing_root).resolve()

    def _hash_file(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        if not file_path.exists():
            raise SourceNotFoundError(f"File not found: {file_path}")
            
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def _verify_path(self, path: Path, allowed_root: Path):
        """Ensure the path is under the allowed root (prevent path traversal)."""
        try:
            resolved_path = path.resolve()
            if allowed_root not in resolved_path.parents and resolved_path != allowed_root:
                raise PathViolationError(f"Path {path} is outside allowed root {allowed_root}")
        except Exception as e:
            if isinstance(e, PathViolationError):
                raise
            raise PathViolationError(f"Invalid path: {path}") from e

    def safe_copy(self, source_path: Path, landing_path: Path) -> Tuple[LandingStatus, str, str]:
        """
        Safely copy a file from source to landing, verifying hashes.
        Returns (status, source_hash, landing_hash).
        """
        self._verify_path(source_path, self.source_root)
        self._verify_path(landing_path, self.landing_root)

        if not source_path.exists():
            raise SourceNotFoundError(f"Source file missing: {source_path}")

        source_hash = self._hash_file(source_path)

        if landing_path.exists():
            landing_hash = self._hash_file(landing_path)
            if source_hash == landing_hash:
                return LandingStatus.ALREADY_LANDED, source_hash, landing_hash
            else:
                raise ConflictError(f"Conflict at {landing_path}. Hash mismatch.")

        # Perform the actual copy
        landing_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, landing_path)
        
        # Verify post-copy hash
        landing_hash = self._hash_file(landing_path)
        if source_hash != landing_hash:
            raise ConflictError(f"Copy failed integrity check for {landing_path}")

        return LandingStatus.LANDED, source_hash, landing_hash
