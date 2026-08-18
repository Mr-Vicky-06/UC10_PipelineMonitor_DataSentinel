from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
import uuid
from app.database.connection import Base

class NotificationHistory(Base):
    __tablename__ = "notification_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    
    channel = Column(String, nullable=False) # 'TEAMS', 'EMAIL', 'WEBHOOK'
    recipient = Column(String, nullable=True) # or team name
    status = Column(String, nullable=False) # 'SUCCESS', 'FAILED'
    error_message = Column(String, nullable=True)
    
    sent_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    alert = relationship("Alert", back_populates="notifications")
