import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from .models import LandedBatch

class LandingManifest:
    """Handles the creation and serialization of the landing manifest."""
    
    @staticmethod
    def generate(run_id: str, source_root: str, landing_root: str, batches: List[LandedBatch], output_path: Path):
        """Generates and writes the manifest JSON."""
        total_source_files = len(batches)
        total_landed = len([b for b in batches if b.status in ("LANDED", "ALREADY_LANDED")])
        total_bytes = sum(b.size_bytes for b in batches)
        hospitals = list(set(b.hospital_id for b in batches))
        
        manifest_data = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "source_root": str(Path(source_root).resolve()),
            "landing_root": str(Path(landing_root).resolve()),
            "total_source_files": total_source_files,
            "total_landed_files": total_landed,
            "total_bytes": total_bytes,
            "hospitals": sorted(hospitals),
            "files": [
                {
                    "hospital_id": b.hospital_id,
                    "filename": b.filename,
                    "service_date": b.service_date.isoformat(),
                    "source_path": b.source_path,
                    "landing_path": b.landing_path,
                    "size_bytes": b.size_bytes,
                    "source_sha256": b.source_sha256,
                    "landing_sha256": b.landing_sha256,
                    "status": b.status,
                    "landed_at": b.landed_at.isoformat()
                } for b in batches
            ]
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(manifest_data, f, indent=2)
