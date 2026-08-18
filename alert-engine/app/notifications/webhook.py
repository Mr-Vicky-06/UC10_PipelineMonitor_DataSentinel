from .base import BaseNotificationProvider
from app.config import settings
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WebhookNotificationProvider(BaseNotificationProvider):
    async def send(self, alert_data: Dict[str, Any]) -> bool:
        url = settings.ALERT_WEBHOOK_URL
        if not url:
            logger.debug("ALERT_WEBHOOK_URL not set. Skipping Webhook notification.")
            return False
            
        payload = {
            "alert_id": alert_data.get('alert_id'),
            "source": alert_data.get('source'),
            "severity": alert_data.get('severity'),
            "pipeline": alert_data.get('pipeline'),
            "summary": alert_data.get('summary')
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=5.0)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send Webhook notification: {str(e)}")
            return False
