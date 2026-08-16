import os
import re
import datetime
from pathlib import Path
from typing import List
from .models import DiscoveredBatchSource
from .errors import FileDiscoveryError, FileFormatError

class BatchDiscoverer:
    """
    Discovers batch files within the master_data directory recursively.
    Extracts metadata from the directory structure and filenames.
    """
    def __init__(self, input_root: str, run_id: str, file_extension: str = ".csv", delimiter: str = "|"):
        self.input_root = Path(input_root)
        self.run_id = run_id
        self.run_dir = self.input_root / self.run_id
        self.file_extension = file_extension
        self.delimiter = delimiter
        self.filename_pattern = re.compile(r"^batch_(\d{8})\.csv$")

    def discover(self) -> List[DiscoveredBatchSource]:
        """
        Recursively scans the active run directory for batch files.
        Returns a deterministically ordered list of DiscoveredBatchSource.
        """
        if not self.run_dir.exists() or not self.run_dir.is_dir():
            raise FileDiscoveryError(f"Run directory not found: {self.run_dir}")

        discovered_sources = []
        
        # rglob ensures recursive discovery
        for file_path in sorted(self.run_dir.rglob(f"*{self.file_extension}")):
            if not file_path.is_file():
                continue

            # Identify hospital/source from parent directory
            hospital_id = file_path.parent.name
            batch_filename = file_path.name
            
            # Extract service date from filename
            match = self.filename_pattern.match(batch_filename)
            if not match:
                # We skip files that don't match the required batch format to avoid malformed inputs
                continue
                
            date_str = match.group(1)
            try:
                service_date = datetime.datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError as e:
                raise FileFormatError(f"Invalid date in filename {batch_filename}: {e}")

            file_size = file_path.stat().st_size
            if file_size == 0:
                # Optionally handle empty files. For now, we still discover them, 
                # but the reader may handle it differently or downstream validation will fail it.
                pass

            source = DiscoveredBatchSource(
                source_file=str(file_path.absolute()),
                hospital_id=hospital_id,
                batch_id=batch_filename,
                service_date=service_date,
                file_size=file_size,
                file_format=self.file_extension.lstrip('.'),
                delimiter=self.delimiter
            )
            discovered_sources.append(source)

        return discovered_sources
