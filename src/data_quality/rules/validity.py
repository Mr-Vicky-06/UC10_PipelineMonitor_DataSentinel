"""
Categorical and Domain Validity Quality Rules.
Evaluates membership against allowed domain values (e.g. AUTH_STATUS_CD in ['APPROVED', 'DENIED', 'PENDING']).
"""

import time
from typing import Any, Dict, List, Optional
import pandas as pd

from ..models import (
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    RuleResult,
    ValidityRuleConfig,
)
from .base import BaseDataQualityRule


class ValidityRule(BaseDataQualityRule):
    """Evaluates field value membership in allowed domain categories."""

    def __init__(self, config: ValidityRuleConfig, dataset_name: str):
        super().__init__(
            rule_id=config.id,
            rule_name=config.name,
            category=DataQualityCategory.VALIDITY,
            dataset=dataset_name,
            severity=config.severity,
            description=config.description,
            enabled=config.enabled,
        )
        self.field_name = config.field
        self.allowed_values = [str(v).strip().upper() for v in config.allowed_values]

    def evaluate(
        self,
        df: pd.DataFrame,
        context: Optional[Dict[str, Any]] = None,
        reference_datasets: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        start_time = time.perf_counter()
        total_rows = len(df)

        if total_rows == 0:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected=f"Values in {self.allowed_values}",
                actual="0 rows evaluated",
                affected_row_count=0,
                total_rows=0,
                message=f"Dataset is empty; validity rule '{self.rule_name}' passed trivially.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        if self.field_name not in df.columns:
            return self._build_result(
                status=DataQualityStatus.WARNING,
                expected=f"Field '{self.field_name}' present",
                actual="Field missing from columns",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"Field '{self.field_name}' not found in dataset.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        series = df[self.field_name].dropna().astype(str).str.strip().str.upper()
        # Exclude null representations
        non_null_mask = ~series.isin(["", "NULL", "NONE", "NAN"])
        eval_series = series[non_null_mask]

        if len(eval_series) == 0:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected=f"Values in {self.allowed_values}",
                actual="No populated values",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"No populated values in '{self.field_name}' to validate.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        invalid_mask = ~eval_series.isin(self.allowed_values)
        invalid_count = int(invalid_mask.sum())
        invalid_pct = (invalid_count / total_rows) * 100.0

        status = DataQualityStatus.FAIL if invalid_count > 0 else DataQualityStatus.PASS
        if invalid_count > 0:
            message = (
                f"Domain validity violation on '{self.field_name}': {invalid_count} row(s) ({invalid_pct:.2f}%) "
                f"have values outside allowed domain {self.allowed_values}."
            )
        else:
            message = f"All {len(eval_series):,} populated values in '{self.field_name}' conform to allowed domain."

        return self._build_result(
            status=status,
            expected=f"Values in {self.allowed_values}",
            actual={"invalid_count": invalid_count, "invalid_pct": round(invalid_pct, 4)},
            affected_row_count=invalid_count,
            total_rows=total_rows,
            message=message,
            fields=[self.field_name],
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={"allowed_values": self.allowed_values, "invalid_count": invalid_count},
        )
