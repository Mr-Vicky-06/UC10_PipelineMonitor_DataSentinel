from .base import BaseNotificationProvider
from app.config import settings
import logging
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)

class EmailNotificationProvider(BaseNotificationProvider):
    async def send(self, alert_data: Dict[str, Any]) -> bool:
        api_key = settings.SENDGRID_API_KEY
        if not api_key:
            logger.warning("SENDGRID_API_KEY not set. Skipping Email notification.")
            return False
            
        logger.info(f"Sending email from {settings.ALERT_FROM_EMAIL} to {settings.ALERT_TO_EMAIL} for alert {alert_data.get('alert_id')}")
        
        payload = {
            "personalizations": [
                {
                    "to": [{"email": settings.ALERT_TO_EMAIL}],
                    "subject": f"[{alert_data.get('severity')}] DataSentinal Alert: {alert_data.get('pipeline')} Pipeline"
                }
            ],
            "from": {"email": settings.ALERT_FROM_EMAIL},
            "content": [
                {
                    "type": "text/plain",
                    "value": f"Alert ID: {alert_data.get('alert_id')}\n"
                             f"Severity: {alert_data.get('severity')}\n"
                             f"Source: {alert_data.get('source')}\n"
                             f"Pipeline: {alert_data.get('pipeline')}\n"
                             f"Hospital: {alert_data.get('hospital')}\n"
                             f"Event Type: {alert_data.get('event_type')}\n"
                             f"Summary: {alert_data.get('summary')}\n"
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"SendGrid API request accepted for {alert_data.get('alert_id')}")
                return True
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {str(e)}")
            return False
