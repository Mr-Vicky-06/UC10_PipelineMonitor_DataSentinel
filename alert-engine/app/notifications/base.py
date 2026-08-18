from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseNotificationProvider(ABC):
    @abstractmethod
    async def send(self, alert_data: Dict[str, Any]) -> bool:
        """
        Sends a notification. 
        Returns True if successful, False otherwise.
        """
        pass
