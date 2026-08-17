"""
Rule Group B: Duplicate & Uniqueness Quality Rules.
Evaluates composite primary key uniqueness, respecting CMS claim-line grain (CLM_ID + CLM_LINE_NUM).
"""

import time
from typing import Any, Dict, List, Optional
import pandas as pd

from ..models import (
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    RuleResult,
    UniquenessRuleConfig,
)
from .base import BaseDataQualityRule


class UniquenessRule(BaseDataQualityRule):
    """Evaluates uniqueness over a configured composite key set."""

    def __init__(self, config: UniquenessRuleConfig, dataset_name: str):
        super().__init__(
            rule_id=config.id,
            rule_name=config.name,
            category=DataQualityCategory.UNIQUENESS,
            dataset=dataset_name,
            severity=config.severity,
            description=config.description,
            enabled=config.enabled,
        )
        self.fields = config.fields
        self.threshold_duplicate_pct = config.threshold_duplicate_pct

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
                expected=f"duplicate_pct <= {self.threshold_duplicate_pct}%",
                actual="0 rows evaluated",
                affected_row_count=0,
                total_rows=0,
                message=f"Dataset is empty; uniqueness rule '{self.rule_name}' passed trivially.",
                fields=self.fields,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        missing_fields = [f for f in self.fields if f not in df.columns]
        if missing_fields:
            return self._build_result(
                status=DataQualityStatus.FAIL,
                expected=f"Key fields {self.fields} present",
                actual=f"Missing key fields: {missing_fields}",
                affected_row_count=total_rows,
                total_rows=total_rows,
                message=f"Cannot evaluate uniqueness: missing key fields {missing_fields}.",
                fields=self.fields,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Compute duplicates using keep=False (flags all participating duplicate rows)
        dup_mask = df.duplicated(subset=self.fields, keep=False)
        duplicate_row_count = int(dup_mask.sum())

        # Also compute redundant excess count (keep='first' flags excess copies)
        excess_dup_mask = df.duplicated(subset=self.fields, keep="first")
        excess_duplicate_count = int(excess_dup_mask.sum())

        # Distinct duplicate keys count
        if duplicate_row_count > 0:
            dup_keys_count = int(df.loc[dup_mask, self.fields].drop_duplicates().shape[0])
        else:
            dup_keys_count = 0

        duplicate_pct = (duplicate_row_count / total_rows) * 100.0
        is_fail = duplicate_pct > self.threshold_duplicate_pct
        status = DataQualityStatus.FAIL if is_fail else DataQualityStatus.PASS

        if is_fail:
            message = (
                f"Uniqueness violation on key {self.fields}: "
                f"{duplicate_row_count} affected duplicate rows ({duplicate_pct:.2f}%), "
                f"{dup_keys_count} distinct duplicate keys (threshold: {self.threshold_duplicate_pct}%)."
            )
        else:
            message = (
                f"Uniqueness satisfied on key {self.fields}: "
                f"0 duplicate keys found across {total_rows:,} records."
            )

        return self._build_result(
            status=status,
            expected={"max_duplicate_pct": self.threshold_duplicate_pct, "key": self.fields},
            actual={
                "duplicate_row_count": duplicate_row_count,
                "excess_duplicate_count": excess_duplicate_count,
                "duplicate_keys_count": dup_keys_count,
                "duplicate_pct": round(duplicate_pct, 4),
            },
            affected_row_count=duplicate_row_count,
            total_rows=total_rows,
            message=message,
            fields=self.fields,
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={
                "duplicate_keys_count": dup_keys_count,
                "excess_duplicate_count": excess_duplicate_count,
            },
        )
