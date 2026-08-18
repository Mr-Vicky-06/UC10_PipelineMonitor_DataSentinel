from sqlalchemy import Column, String, Float, ForeignKey, Integer
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from app.database.connection import Base
import uuid

class AlertDetail(Base):
    __tablename__ = "alert_details"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    
    rule_id = Column(String, nullable=True)
    rule_name = Column(String, nullable=True)
    metric = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    message = Column(String, nullable=True)
    
    affected_rows = Column(Integer, nullable=True)
    total_rows = Column(Integer, nullable=True)
    affected_percentage = Column(Float, nullable=True)
    
    details_json = Column(JSON, nullable=True)

    alert = relationship("Alert", back_populates="details")
