from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://alertuser:alertpass@localhost:5432/alertdb"
    
    # Notifications
    SENDGRID_API_KEY: Optional[str] = None
    ALERT_FROM_EMAIL: str = "shanjaykannan6@gmail.com"
    ALERT_TO_EMAIL: str = "shanjaykannan6@gmail.com"
    TEAMS_WEBHOOK_URL: Optional[str] = None
    ALERT_WEBHOOK_URL: Optional[str] = None
    
    # Routing Config
    CRITICAL_EMAIL_ENABLED: bool = True
    HIGH_EMAIL_ENABLED: bool = True
    CRITICAL_TEAMS_ENABLED: bool = True
    HIGH_TEAMS_ENABLED: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
