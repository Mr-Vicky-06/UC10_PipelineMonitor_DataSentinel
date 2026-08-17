"""
Rule Group A: Completeness Quality Rules.
Evaluates null count, null percentage, blank string count, and required field completeness.
"""

import time
from typing import Any, Dict, List, Optional
import pandas as pd

from ..models import (
    CompletenessRuleConfig,
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    RuleResult,
)
from .base import BaseDataQualityRule


class CompletenessRule(BaseDataQualityRule):
    """Evaluates completeness (nulls and blanks) of a specified dataset field."""

    def __init__(self, config: CompletenessRuleConfig, dataset_name: str):
        super().__init__(
            rule_id=config.id,
            rule_name=config.name,
            category=DataQualityCategory.COMPLETENESS,
            dataset=dataset_name,
            severity=config.severity,
            description=config.description,
            enabled=config.enabled,
        )
        self.field_name = config.field
        self.threshold_null_pct = config.threshold_null_pct
        self.threshold_blank_pct = config.threshold_blank_pct

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
                expected=f"null_pct <= {self.threshold_null_pct}%",
                actual="0 rows evaluated",
                affected_row_count=0,
                total_rows=0,
                message=f"Dataset is empty; completeness rule '{self.rule_name}' passed trivially.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        if self.field_name not in df.columns:
            return self._build_result(
                status=DataQualityStatus.FAIL,
                expected=f"Field '{self.field_name}' present in dataset",
                actual="Field missing from columns",
                affected_row_count=total_rows,
                total_rows=total_rows,
                message=f"Required field '{self.field_name}' is missing from the dataset.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        series = df[self.field_name]

        # 1. Null check (NaN, None, pd.NA)
        null_mask = series.isna()
        null_count = int(null_mask.sum())
        null_pct = (null_count / total_rows) * 100.0

        # 2. Blank string check (empty string, whitespace-only, or textual nulls)
        # Only evaluate non-null string rows
        non_null_str = series[~null_mask].astype(str).str.strip()
        blank_mask = non_null_str.isin(["", "NULL", "null", "None", "none", "NA", "N/A", "nan", "NaN"])
        blank_count = int(blank_mask.sum())
        blank_pct = (blank_count / total_rows) * 100.0

        total_missing_count = null_count + blank_count
        total_missing_pct = (total_missing_count / total_rows) * 100.0

        # Evaluate against thresholds
        null_failed = null_pct > self.threshold_null_pct
        blank_failed = blank_pct > self.threshold_blank_pct
        is_fail = null_failed or blank_failed

        status = DataQualityStatus.FAIL if is_fail else DataQualityStatus.PASS

        if is_fail:
            message = (
                f"Field '{self.field_name}' completeness violation: "
                f"{null_count} nulls ({null_pct:.2f}%, threshold: {self.threshold_null_pct}%), "
                f"{blank_count} blanks ({blank_pct:.2f}%, threshold: {self.threshold_blank_pct}%)."
            )
        else:
            message = (
                f"Field '{self.field_name}' completeness satisfied: "
                f"{null_count} nulls ({null_pct:.2f}%), {blank_count} blanks ({blank_pct:.2f}%)."
            )

        return self._build_result(
            status=status,
            expected={
                "max_null_pct": self.threshold_null_pct,
                "max_blank_pct": self.threshold_blank_pct,
            },
            actual={
                "null_count": null_count,
                "null_pct": round(null_pct, 4),
                "blank_count": blank_count,
                "blank_pct": round(blank_pct, 4),
                "total_missing_count": total_missing_count,
                "total_missing_pct": round(total_missing_pct, 4),
            },
            affected_row_count=total_missing_count,
            total_rows=total_rows,
            message=message,
            fields=[self.field_name],
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={
                "null_count": null_count,
                "blank_count": blank_count,
                "threshold_null_pct": self.threshold_null_pct,
                "threshold_blank_pct": self.threshold_blank_pct,
            },
        )
