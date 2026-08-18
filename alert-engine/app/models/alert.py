from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
import datetime
from app.database.connection import Base
import uuid

class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String, unique=True, index=True, nullable=False)
    source = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    pipeline = Column(String, index=True, nullable=False)
    hospital = Column(String, index=True, nullable=False)
    severity = Column(Enum(Severity), index=True, nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.OPEN, index=True, nullable=False)
    summary = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    occurrence_count = Column(Integer, default=1, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    fingerprint = Column(String, unique=True, index=True, nullable=False)

    details = relationship("AlertDetail", back_populates="alert", cascade="all, delete-orphan")
    notifications = relationship("NotificationHistory", back_populates="alert", cascade="all, delete-orphan")
