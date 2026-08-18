from sqlalchemy.orm import Session
from app.models.alert import Alert, AlertStatus
from app.models.alert_detail import AlertDetail
from app.schemas.alert_event import AlertEvent
from app.services.severity_service import SeverityService
from app.services.deduplication_service import DeduplicationService
from app.services.routing_service import RoutingService
from app.api.websocket import manager
import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.severity_svc = SeverityService(db)
        self.dedup_svc = DeduplicationService(db)
        self.routing_svc = RoutingService(db)

    async def process_event(self, event: AlertEvent):
        # 1. Determine Severity
        severity = self.severity_svc.determine_severity(event)
        
        # 2. Deduplicate
        fingerprint = self.dedup_svc.generate_fingerprint(event)
        existing_alert = self.dedup_svc.get_existing_open_alert(fingerprint)
        
        if existing_alert:
            # Update existing alert
            existing_alert.occurrence_count += 1
            existing_alert.last_seen_at = datetime.datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_alert)
            
            logger.info(f"Deduplicated alert {existing_alert.alert_id} (count: {existing_alert.occurrence_count})")
            
            # Broadcast update via websocket
            await self._broadcast_alert(existing_alert)
            return existing_alert
            
        # 3. Create new Alert ID
        date_str = datetime.datetime.utcnow().strftime("%Y%m%d")
        # For a real system we might use a sequence, here we use a UUID suffix for uniqueness
        short_id = str(uuid.uuid4())[:6].upper()
        alert_id = f"ALT-{date_str}-{short_id}"
        
        # 4. Store Alert
        new_alert = Alert(
            alert_id=alert_id,
            source=event.source,
            event_type=event.event_type,
            pipeline=event.pipeline,
            hospital=event.hospital,
            severity=severity,
            status=AlertStatus.OPEN,
            summary=event.summary,
            fingerprint=fingerprint
        )
        self.db.add(new_alert)
        self.db.commit() # commit to get the generated UUID id
        self.db.refresh(new_alert)
        
        # Store Details
        details = AlertDetail(
            alert_id=new_alert.id,
            rule_id=event.details.rule_id,
            rule_name=event.details.rule_name,
            metric=event.metric,
            value=float(event.value) if isinstance(event.value, (int, float)) or (isinstance(event.value, str) and event.value.replace('.','',1).isdigit()) else 0.0,
            unit=event.unit,
            affected_rows=event.details.affected_rows,
            total_rows=event.details.total_rows,
            affected_percentage=event.details.affected_percentage,
            details_json=event.details.model_dump()
        )
        self.db.add(details)
        self.db.commit()
        
        logger.info(f"Created new alert {alert_id} with severity {severity.name}")
        
        # 5. Route Notifications asynchronously
        await self.routing_svc.route_alert(new_alert)
        
        # 6. Broadcast via WebSocket
        await self._broadcast_alert(new_alert)
        
        return new_alert

    async def _broadcast_alert(self, alert: Alert):
        alert_data = {
            "alert_id": alert.alert_id,
            "source": alert.source,
            "event_type": alert.event_type,
            "pipeline": alert.pipeline,
            "hospital": alert.hospital,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "summary": alert.summary,
            "created_at": alert.created_at.isoformat(),
            "occurrence_count": alert.occurrence_count
        }
        await manager.broadcast_alert(alert_data)
