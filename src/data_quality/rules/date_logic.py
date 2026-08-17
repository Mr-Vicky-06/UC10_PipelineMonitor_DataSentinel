"""
Rule Group F: Date Quality and Logical Sequence Rules.
Evaluates healthcare date ordering, admission/discharge consistency, and future date constraints.
"""

from datetime import date, datetime
import time
from typing import Any, Dict, List, Optional
import pandas as pd

from ..models import (
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    DateLogicRuleConfig,
    RuleResult,
)
from .base import BaseDataQualityRule


def _parse_dates_vectorized(series: pd.Series) -> pd.Series:
    """Parse dates across common healthcare formats (%d-%b-%Y, %Y-%m-%d, %Y%m%d)."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    clean_str = series.astype(str).str.strip()
    # Replace empty-like strings with NA
    clean_str = clean_str.replace(["", "NULL", "null", "None", "nan", "NaN", "0"], pd.NA)

    # First attempt standard pandas parsing (handles ISO %Y-%m-%d and %d-%b-%Y)
    parsed = pd.to_datetime(clean_str, errors="coerce", format="mixed")
    return parsed


class DateLogicRule(BaseDataQualityRule):
    """Evaluates business and chronological date relationships."""

    def __init__(self, config: DateLogicRuleConfig, dataset_name: str):
        super().__init__(
            rule_id=config.id,
            rule_name=config.name,
            category=DataQualityCategory.DATE_LOGIC,
            dataset=dataset_name,
            severity=config.severity,
            description=config.description,
            enabled=config.enabled,
        )
        self.from_date_field = config.from_date_field
        self.thru_date_field = config.thru_date_field
        self.admission_date_field = config.admission_date_field
        self.discharge_date_field = config.discharge_date_field
        self.service_date_field = config.service_date_field
        self.date_field = config.date_field
        self.operator = config.operator
        self.allow_future = config.allow_future
        self.reference_date = config.reference_date

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
                expected="Valid date chronology",
                actual="0 rows evaluated",
                affected_row_count=0,
                total_rows=0,
                message=f"Dataset is empty; date rule '{self.rule_name}' passed trivially.",
                fields=[],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Mode 1: Future date validation
        if self.date_field and not self.allow_future:
            return self._evaluate_future_date(df, total_rows, start_time, context)

        # Mode 2: Pairwise date ordering validation
        return self._evaluate_date_ordering(df, total_rows, start_time)

    def _evaluate_future_date(
        self,
        df: pd.DataFrame,
        total_rows: int,
        start_time: float,
        context: Optional[Dict[str, Any]],
    ) -> RuleResult:
        field = self.date_field
        if field not in df.columns:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected=f"Field '{field}' present",
                actual="Field not present in dataset",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"Date field '{field}' not applicable (not present in dataset); skipped.",
                fields=[field],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        ref_dt = None
        if self.reference_date:
            try:
                ref_dt = pd.to_datetime(self.reference_date)
            except Exception:
                pass
        if ref_dt is None and context and "reference_date" in context:
            try:
                ref_dt = pd.to_datetime(context["reference_date"])
            except Exception:
                pass
        if ref_dt is None:
            # Current date
            ref_dt = pd.to_datetime(datetime.now().date())

        dates = _parse_dates_vectorized(df[field])
        future_mask = ~dates.isna() & (dates > ref_dt)
        future_count = int(future_mask.sum())
        future_pct = (future_count / total_rows) * 100.0

        status = DataQualityStatus.FAIL if future_count > 0 else DataQualityStatus.PASS
        if future_count > 0:
            message = (
                f"Found {future_count} future date(s) ({future_pct:.2f}%) in '{field}' "
                f"occurring after reference date {ref_dt.strftime('%Y-%m-%d')}."
            )
        else:
            message = f"No future dates detected in '{field}' relative to {ref_dt.strftime('%Y-%m-%d')}."

        return self._build_result(
            status=status,
            expected=f"{field} <= {ref_dt.strftime('%Y-%m-%d')}",
            actual={"future_count": future_count, "future_pct": round(future_pct, 4)},
            affected_row_count=future_count,
            total_rows=total_rows,
            message=message,
            fields=[field],
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={"reference_date": ref_dt.strftime("%Y-%m-%d")},
        )

    def _evaluate_date_ordering(
        self, df: pd.DataFrame, total_rows: int, start_time: float
    ) -> RuleResult:
        # Determine the two target date fields
        if self.from_date_field and self.thru_date_field:
            f1, f2 = self.from_date_field, self.thru_date_field
            rule_desc = f"{f1} <= {f2}"
        elif self.admission_date_field and self.discharge_date_field:
            f1, f2 = self.admission_date_field, self.discharge_date_field
            rule_desc = f"{f1} <= {f2}"
        elif self.admission_date_field and self.service_date_field:
            f1, f2 = self.admission_date_field, self.service_date_field
            rule_desc = f"{f1} <= {f2}"
        else:
            return self._build_result(
                status=DataQualityStatus.FAIL,
                expected="Date field pair configured",
                actual="Missing date field pair configuration",
                affected_row_count=total_rows,
                total_rows=total_rows,
                message="Date logic rule missing field pair configuration.",
                execution_time_seconds=time.perf_counter() - start_time,
            )

        fields = [f1, f2]
        missing = [f for f in fields if f not in df.columns]
        if missing:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected=f"Date fields {fields} present",
                actual=f"Fields not present: {missing}",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"Date ordering check '{self.rule_name}' skipped (optional fields {missing} absent).",
                fields=fields,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        d1 = _parse_dates_vectorized(df[f1])
        d2 = _parse_dates_vectorized(df[f2])

        # Evaluate only where both dates are successfully parsed and populated
        valid_both = ~d1.isna() & ~d2.isna()
        evaluated_pairs_count = int(valid_both.sum())

        if evaluated_pairs_count == 0:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected=rule_desc,
                actual="0 populated date pairs to compare",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"No populated date pairs found for {fields}; rule passed.",
                fields=fields,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Ordering violation: d1 > d2 (e.g. from > thru, or admission > discharge)
        violation_mask = valid_both & (d1 > d2)
        violation_count = int(violation_mask.sum())
        violation_pct = (violation_count / total_rows) * 100.0

        status = DataQualityStatus.FAIL if violation_count > 0 else DataQualityStatus.PASS
        if violation_count > 0:
            message = (
                f"Date ordering violation ({rule_desc}): {violation_count} records ({violation_pct:.2f}%) "
                f"where '{f1}' is after '{f2}'."
            )
        else:
            message = f"Date chronology satisfied: {rule_desc} holds across all {evaluated_pairs_count:,} evaluated pairs."

        return self._build_result(
            status=status,
            expected=rule_desc,
            actual={
                "violation_count": violation_count,
                "violation_pct": round(violation_pct, 4),
                "evaluated_pairs_count": evaluated_pairs_count,
            },
            affected_row_count=violation_count,
            total_rows=total_rows,
            message=message,
            fields=fields,
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={"evaluated_pairs_count": evaluated_pairs_count},
        )
