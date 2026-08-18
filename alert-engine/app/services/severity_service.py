from sqlalchemy.orm import Session
from typing import Union
from app.models.alert_rule import AlertRule
from app.models.alert import Severity
from app.schemas.alert_event import AlertEvent
import logging

logger = logging.getLogger(__name__)

class SeverityService:
    def __init__(self, db: Session):
        self.db = db

    def determine_severity(self, event: AlertEvent) -> Severity:
        """
        Evaluate the event against the rules stored in PostgreSQL.
        If no rules match, default to LOW.
        """
        # We fetch rules that match the source and metric, ordered by severity ranking
        # Alternatively, we just fetch all enabled rules for this event_type and metric
        rules = self.db.query(AlertRule).filter(
            AlertRule.source == event.source,
            AlertRule.event_type == event.event_type,
            AlertRule.metric == event.metric,
            AlertRule.enabled == True
        ).all()

        if not rules:
            return self._fallback_severity(event)

        # Evaluate rules
        # Hierarchy: CRITICAL > HIGH > MEDIUM > LOW
        severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        highest_severity = Severity.LOW
        current_rank = 1

        for rule in rules:
            if self._evaluate_condition(event.value, rule.operator, rule.threshold):
                rule_severity = Severity(rule.severity)
                rank = severity_rank.get(rule_severity.value, 1)
                if rank > current_rank:
                    highest_severity = rule_severity
                    current_rank = rank

        return highest_severity

    def _evaluate_condition(self, value: Union[float, str], operator: str, threshold: float) -> bool:
        try:
            val = float(value)
            if operator == '>': return val > threshold
            if operator == '<': return val < threshold
            if operator == '>=': return val >= threshold
            if operator == '<=': return val <= threshold
            if operator == '==': return val == threshold
            if operator == '!=': return val != threshold
        except ValueError:
            pass
        return False

    def _fallback_severity(self, event: AlertEvent) -> Severity:
        # Some hardcoded fallbacks if DB rules are missing
        if event.source == 'DQ' and event.metric == 'null_percentage':
            if float(event.value) > 30: return Severity.CRITICAL
            if float(event.value) >= 10: return Severity.HIGH
            if float(event.value) >= 5: return Severity.MEDIUM
        
        if event.source == 'ANOMALY' and event.metric == 'volume_deviation':
            if float(event.value) > 50: return Severity.CRITICAL
            if float(event.value) >= 30: return Severity.HIGH
            if float(event.value) >= 10: return Severity.MEDIUM

        if event.source == 'SLA' and event.metric == 'minutes_remaining':
            if float(event.value) < 10: return Severity.CRITICAL
            if float(event.value) <= 30: return Severity.HIGH
            if float(event.value) <= 60: return Severity.MEDIUM

        if event.source == 'PROCESSING' and str(event.value).upper() == 'FAILED':
            return Severity.CRITICAL

        return Severity.LOW
