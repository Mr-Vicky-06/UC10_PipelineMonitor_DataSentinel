from sqlalchemy.orm import Session
from app.models.alert import Alert, AlertStatus
from app.schemas.alert_event import AlertEvent
import hashlib
import datetime
from typing import Optional

class DeduplicationService:
    def __init__(self, db: Session):
        self.db = db

    def generate_fingerprint(self, event: AlertEvent) -> str:
        """
        Generate a unique fingerprint based on core identifying fields.
        """
        fingerprint_data = f"{event.source}:{event.pipeline}:{event.hospital}:{event.event_type}:{event.metric}:{event.details.rule_id or ''}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()

    def get_existing_open_alert(self, fingerprint: str) -> Optional[Alert]:
        """
        Look for an existing OPEN alert with this fingerprint.
        """
        return self.db.query(Alert).filter(
            Alert.fingerprint == fingerprint,
            Alert.status == AlertStatus.OPEN
        ).first()
