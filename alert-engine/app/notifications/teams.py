from .base import BaseNotificationProvider
from app.config import settings
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TeamsNotificationProvider(BaseNotificationProvider):
    async def send(self, alert_data: Dict[str, Any]) -> bool:
        url = settings.TEAMS_WEBHOOK_URL
        if not url:
            logger.warning("TEAMS_WEBHOOK_URL not set. Skipping Teams notification.")
            return False
            
        # Format the message for Teams
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"🔴 {alert_data.get('severity')} ALERT",
                                "weight": "Bolder",
                                "size": "Large"
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Alert ID:", "value": alert_data.get('alert_id')},
                                    {"title": "Pipeline:", "value": alert_data.get('pipeline')},
                                    {"title": "Hospital:", "value": alert_data.get('hospital')},
                                    {"title": "Type:", "value": alert_data.get('event_type')},
                                    {"title": "Status:", "value": alert_data.get('status')}
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": alert_data.get('summary'),
                                "wrap": True
                            }
                        ]
                    }
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {str(e)}")
            return False
