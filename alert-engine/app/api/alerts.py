from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import logging

from app.database.connection import get_db
from app.schemas.alert_event import AlertEvent
from app.schemas.alert_response import AlertResponse, AlertDetailedResponse, AlertSummary
from app.services.alert_service import AlertService
from app.models.alert import Alert, AlertStatus, Severity
from app.api.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

@router.post("/events", status_code=status.HTTP_201_CREATED, response_model=AlertResponse)
async def create_alert_event(event: AlertEvent, db: Session = Depends(get_db)):
    logger.info(f"Received alert event: {event.source} - {event.event_type}")
    service = AlertService(db)
    try:
        alert = await service.process_event(event)
        return alert
    except Exception as e:
        logger.error(f"Error processing alert event: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while processing event")

@router.get("/", response_model=List[AlertResponse])
def get_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    pipeline: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    
    if severity:
        query = query.filter(Alert.severity == Severity(severity.upper()))
    if status:
        query = query.filter(Alert.status == AlertStatus(status.upper()))
    if source:
        query = query.filter(Alert.source == source.upper())
    if pipeline:
        query = query.filter(Alert.pipeline == pipeline)
        
    alerts = query.order_by(Alert.updated_at.desc()).limit(limit).all()
    return alerts

@router.get("/summary", response_model=AlertSummary)
def get_alert_summary(db: Session = Depends(get_db)):
    summary = {
        "critical": db.query(Alert).filter(Alert.severity == Severity.CRITICAL).count(),
        "high": db.query(Alert).filter(Alert.severity == Severity.HIGH).count(),
        "medium": db.query(Alert).filter(Alert.severity == Severity.MEDIUM).count(),
        "low": db.query(Alert).filter(Alert.severity == Severity.LOW).count(),
        "open": db.query(Alert).filter(Alert.status == AlertStatus.OPEN).count(),
        "acknowledged": db.query(Alert).filter(Alert.status == AlertStatus.ACKNOWLEDGED).count(),
        "resolved": db.query(Alert).filter(Alert.status == AlertStatus.RESOLVED).count()
    }
    return AlertSummary(**summary)

@router.get("/{alert_id}", response_model=AlertDetailedResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.status = AlertStatus.ACKNOWLEDGED
    db.commit()
    db.refresh(alert)
    
    # Broadcast state change
    alert_service = AlertService(db)
    await alert_service._broadcast_alert(alert)
    return alert

@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.status = AlertStatus.RESOLVED
    db.commit()
    db.refresh(alert)
    
    # Broadcast state change
    alert_service = AlertService(db)
    await alert_service._broadcast_alert(alert)
    return alert
