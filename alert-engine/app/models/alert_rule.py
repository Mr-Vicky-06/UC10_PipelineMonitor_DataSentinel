from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.orm import declarative_base
from app.database.connection import Base
import uuid

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    metric = Column(String, index=True, nullable=False)
    operator = Column(String, nullable=False) # e.g., '>', '<', '>=', '<=', '==', '!='
    threshold = Column(Float, nullable=False)
    severity = Column(String, nullable=False) # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    enabled = Column(Boolean, default=True, nullable=False)
