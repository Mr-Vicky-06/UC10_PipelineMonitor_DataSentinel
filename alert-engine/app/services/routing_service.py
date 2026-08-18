from sqlalchemy.orm import Session
from app.models.alert import Alert, Severity
from app.models.notification_history import NotificationHistory
from app.notifications.teams import TeamsNotificationProvider
from app.notifications.email import EmailNotificationProvider
from app.notifications.webhook import WebhookNotificationProvider
from app.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

class RoutingService:
    def __init__(self, db: Session):
        self.db = db
        self.teams = TeamsNotificationProvider()
        self.email = EmailNotificationProvider()
        self.webhook = WebhookNotificationProvider()

    async def route_alert(self, alert: Alert):
        """
        Determine which channels to trigger and send notifications.
        """
        alert_data = {
            "alert_id": alert.alert_id,
            "source": alert.source,
            "pipeline": alert.pipeline,
            "hospital": alert.hospital,
            "event_type": alert.event_type,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "summary": alert.summary
        }

        tasks = []
        channels = []

        # Teams routing
        if (alert.severity == Severity.CRITICAL and settings.CRITICAL_TEAMS_ENABLED) or \
           (alert.severity == Severity.HIGH and settings.HIGH_TEAMS_ENABLED):
            tasks.append(self.teams.send(alert_data))
            channels.append("TEAMS")

        # Email routing
        if (alert.severity == Severity.CRITICAL and settings.CRITICAL_EMAIL_ENABLED) or \
           (alert.severity == Severity.HIGH and settings.HIGH_EMAIL_ENABLED):
            tasks.append(self.email.send(alert_data))
            channels.append("EMAIL")
            
        # Webhook routing (all severities, if enabled)
        if settings.ALERT_WEBHOOK_URL:
            tasks.append(self.webhook.send(alert_data))
            channels.append("WEBHOOK")

        if not tasks:
            return

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Record history
        for idx, result in enumerate(results):
            channel = channels[idx]
            history = NotificationHistory(alert_id=alert.id, channel=channel)
            
            if isinstance(result, Exception):
                history.status = "FAILED"
                history.error_message = str(result)
                logger.error(f"Notification to {channel} failed: {result}")
            elif result is False:
                history.status = "FAILED"
                history.error_message = "Provider returned False (likely disabled or configuration missing)"
            else:
                history.status = "SUCCESS"

            self.db.add(history)
        
        self.db.commit()
