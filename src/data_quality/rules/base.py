"""
Base abstract class for all Data Quality Rules.
"""

from abc import ABC, abstractmethod
import time
from typing import Any, Dict, List, Optional
import pandas as pd

from ..models import (
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    RuleResult,
)


class BaseDataQualityRule(ABC):
    """Abstract base class for all data quality rule evaluators."""

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        category: DataQualityCategory,
        dataset: str,
        severity: DataQualitySeverity = DataQualitySeverity.ERROR,
        description: str = "",
        enabled: bool = True,
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.category = category
        self.dataset = dataset
        self.severity = severity
        self.description = description
        self.enabled = enabled

    @abstractmethod
    def evaluate(
        self,
        df: pd.DataFrame,
        context: Optional[Dict[str, Any]] = None,
        reference_datasets: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        """
        Evaluate this rule against the given DataFrame (Read-Only).
        Must NOT modify the input DataFrame.
        """
        pass

    def _build_result(
        self,
        status: DataQualityStatus,
        expected: Any,
        actual: Any,
        affected_row_count: int,
        total_rows: int,
        message: str,
        fields: Optional[List[str]] = None,
        execution_time_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        """Helper to construct a standardized RuleResult."""
        affected_pct = (affected_row_count / total_rows * 100.0) if total_rows > 0 else 0.0
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            dataset=self.dataset,
            fields=fields or [],
            status=status,
            severity=self.severity,
            expected=expected,
            actual=actual,
            affected_row_count=affected_row_count,
            affected_percentage=affected_pct,
            message=message,
            execution_time_seconds=execution_time_seconds,
            metadata=metadata or {},
        )
