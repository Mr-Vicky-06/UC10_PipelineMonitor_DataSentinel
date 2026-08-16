from typing import List, Tuple, Dict, Any
import pandas as pd
from datetime import datetime
import time
import uuid
from src.pipeline.telemetry import PipelineTelemetryLogger, TelemetryEvent, PipelineStage, TelemetryStatus

from .models import BusinessRuleResult, BusinessRuleViolation
from .rules import BusinessRule

class BusinessRuleEngine:
    def __init__(self, rules: List[BusinessRule]):
        self.rules = rules
        self.telemetry = PipelineTelemetryLogger.get_instance()

    def execute(self, transformed_batch: Tuple[pd.DataFrame, Dict], run_id: str = "business_rules_run") -> BusinessRuleResult:
        """
        Executes business rules against the transformed dataset.
        Expects the exact contract from Transformation: Tuple[pd.DataFrame, Dict]
        """
        df, input_metrics = transformed_batch
        
        batch_id = input_metrics.get("batch_id", "unknown")
        source_file = input_metrics.get("source_file", "unknown")
        hospital_id = "unknown"
        if source_file and "HOSP-" in source_file:
            parts = source_file.replace('\\', '/').split('/')
            for p in parts:
                if p.startswith('HOSP-'):
                    hospital_id = p
                    break
                    
        correlation_id = str(uuid.uuid4())
        start_t = time.time()
        
        start_event = TelemetryEvent(
            correlation_id=correlation_id, run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            stage=PipelineStage.BUSINESS_RULES, status=TelemetryStatus.STARTED, source_file=source_file
        )
        self.telemetry.log_event(start_event)
        
        try:
            all_violations: List[BusinessRuleViolation] = []
            
            # Execute each rule independently
            for rule in self.rules:
                violations = rule.evaluate(df)
                all_violations.extend(violations)
        except Exception as e:
            err_event = TelemetryEvent(
                correlation_id=correlation_id, run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
                stage=PipelineStage.BUSINESS_RULES, status=TelemetryStatus.FAILED, source_file=source_file,
                duration_ms=int((time.time() - start_t) * 1000), error_type=type(e).__name__, error_message=str(e)
            )
            self.telemetry.log_event(err_event)
            raise
            
        # Collect metrics
        metrics = {
            "input_metrics": input_metrics,
            "rules_executed": len(self.rules),
            "total_violations": len(all_violations),
            "claims_processed": len(df),
            "violation_breakdown": {}
        }
        
        for rule in self.rules:
            rule_fails = sum(1 for v in all_violations if v.rule_id == rule.rule_id and v.status == "FAIL")
            rule_not_eval = sum(1 for v in all_violations if v.rule_id == rule.rule_id and v.status == "NOT_EVALUATED")
            metrics["violation_breakdown"][rule.rule_id] = {
                "fails": rule_fails,
                "not_evaluated": rule_not_eval
            }
            
        status = "SUCCESS"
        if len(all_violations) > 0:
            status = "COMPLETED_WITH_VIOLATIONS"
            
        end_event = TelemetryEvent(
            correlation_id=correlation_id, run_id=run_id, hospital_id=hospital_id, batch_id=batch_id,
            stage=PipelineStage.BUSINESS_RULES, status=TelemetryStatus.COMPLETED, source_file=source_file,
            duration_ms=int((time.time() - start_t) * 1000), records_in=len(df), records_out=len(df),
            errors=0
        )
        self.telemetry.log_event(end_event)
            
        return BusinessRuleResult(
            dataframe=df,
            violations=all_violations,
            execution_timestamp=datetime.utcnow().isoformat() + "Z",
            metrics=metrics,
            status=status
        )
