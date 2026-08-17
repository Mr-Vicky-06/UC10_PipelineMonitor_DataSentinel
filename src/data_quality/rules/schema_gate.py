"""
Rule Group H: Schema Validation Gate Integration Rule.
Consumes upstream structural Schema Validation results without re-running schema validation logic.
"""

import time
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from ..models import (
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    RuleResult,
    SchemaGateConfig,
)
from .base import BaseDataQualityRule


class SchemaGateRule(BaseDataQualityRule):
    """Integrates upstream Schema Validation status into the Data Quality report."""

    def __init__(self, config: SchemaGateConfig, dataset_name: str):
        super().__init__(
            rule_id="DQ-SCHEMA-001",
            rule_name="upstream_schema_validation_gate",
            category=DataQualityCategory.SCHEMA_CONFORMANCE,
            dataset=dataset_name,
            severity=config.severity_on_fail,
            description=config.description or "Captures upstream structural Schema Validation status.",
            enabled=config.enabled,
        )
        self.severity_on_fail = config.severity_on_fail
        self.severity_on_warning = config.severity_on_warning

    def evaluate(
        self,
        df: pd.DataFrame,
        context: Optional[Dict[str, Any]] = None,
        reference_datasets: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        start_time = time.perf_counter()
        total_rows = len(df)

        # Check if schema validation result is provided in context or reference_datasets
        schema_res = None
        if context and "schema_validation_result" in context:
            schema_res = context["schema_validation_result"]
        elif reference_datasets and "schema_validation_result" in reference_datasets:
            schema_res = reference_datasets["schema_validation_result"]

        if schema_res is None:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected="Schema validation executed upstream",
                actual="No upstream schema validation result provided (assumed PASS)",
                affected_row_count=0,
                total_rows=total_rows,
                message="Upstream schema validation result not provided; schema gate assumed PASS.",
                execution_time_seconds=time.perf_counter() - start_time,
                metadata={"upstream_provided": False},
            )

        # Parse schema result (could be ValidationResult object, dict, or string)
        if hasattr(schema_res, "status"):
            raw_status = str(schema_res.status.value if hasattr(schema_res.status, "value") else schema_res.status).upper()
            error_count = getattr(schema_res, "error_count", 0)
            warning_count = getattr(schema_res, "warning_count", 0)
            issues_len = len(getattr(schema_res, "issues", []))
        elif isinstance(schema_res, dict):
            raw_status = str(schema_res.get("status", "PASS")).upper()
            error_count = int(schema_res.get("error_count", 0))
            warning_count = int(schema_res.get("warning_count", 0))
            issues_len = len(schema_res.get("issues", []))
        elif isinstance(schema_res, str):
            raw_status = schema_res.upper()
            error_count = 1 if raw_status == "FAIL" else 0
            warning_count = 1 if raw_status == "WARNING" else 0
            issues_len = error_count + warning_count
        else:
            raw_status = "PASS"
            error_count = 0
            warning_count = 0
            issues_len = 0

        if raw_status == "FAIL":
            status = DataQualityStatus.FAIL
            severity = self.severity_on_fail
            message = f"Upstream schema validation FAILED with {error_count} error(s) and {warning_count} warning(s)."
            affected_count = error_count
        elif raw_status == "WARNING":
            status = DataQualityStatus.WARNING
            severity = self.severity_on_warning
            message = f"Upstream schema validation passed with {warning_count} WARNING(s)."
            affected_count = warning_count
        else:
            status = DataQualityStatus.PASS
            severity = DataQualitySeverity.INFO
            message = "Upstream structural schema validation PASSED."
            affected_count = 0

        self.severity = severity

        return self._build_result(
            status=status,
            expected="Upstream Schema Validation PASS",
            actual=f"Schema status: {raw_status} ({error_count} errors, {warning_count} warnings)",
            affected_row_count=affected_count,
            total_rows=total_rows,
            message=message,
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={
                "upstream_schema_status": raw_status,
                "error_count": error_count,
                "warning_count": warning_count,
                "issues_count": issues_len,
            },
        )
