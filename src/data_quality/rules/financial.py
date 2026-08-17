"""
Rule Group C: Financial and Amount Validation Quality Rules.
Evaluates healthcare amount fields for non-negativity, valid numeric domains, and financial consistency.
"""

import time
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ..models import (
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    FinancialRuleConfig,
    RuleResult,
)
from .base import BaseDataQualityRule


class FinancialAmountRule(BaseDataQualityRule):
    """Evaluates numeric and financial domain rules on healthcare amount fields."""

    def __init__(self, config: FinancialRuleConfig, dataset_name: str):
        super().__init__(
            rule_id=config.id,
            rule_name=config.name,
            category=DataQualityCategory.FINANCIAL,
            dataset=dataset_name,
            severity=config.severity,
            description=config.description,
            enabled=config.enabled,
        )
        self.field_name = config.field
        self.allow_negative = config.allow_negative
        self.min_value = config.min_value
        self.max_value = config.max_value
        self.payment_field = config.payment_field
        self.charge_field = config.charge_field

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
                expected="Valid financial amounts",
                actual="0 rows evaluated",
                affected_row_count=0,
                total_rows=0,
                message=f"Dataset is empty; financial rule '{self.rule_name}' passed trivially.",
                fields=[self.field_name] if self.field_name else [],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Mode 1: Relational check between payment and charge (e.g. payment <= charge)
        if self.payment_field and self.charge_field:
            return self._evaluate_payment_vs_charge(df, total_rows, start_time)

        # Mode 2: Single-field financial amount validation
        if not self.field_name:
            return self._build_result(
                status=DataQualityStatus.FAIL,
                expected="Target field defined",
                actual="No field specified",
                affected_row_count=total_rows,
                total_rows=total_rows,
                message="Financial rule configuration missing target field.",
                execution_time_seconds=time.perf_counter() - start_time,
            )

        if self.field_name not in df.columns:
            return self._build_result(
                status=DataQualityStatus.FAIL,
                expected=f"Field '{self.field_name}' present",
                actual="Field missing from columns",
                affected_row_count=total_rows,
                total_rows=total_rows,
                message=f"Financial field '{self.field_name}' not found in dataset.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        raw_series = df[self.field_name]
        # Clean string formatting (commas, dollar signs, whitespace) for numeric parsing check
        if pd.api.types.is_numeric_dtype(raw_series):
            num_series = raw_series.astype(float)
            malformed_count = 0
        else:
            clean_str = raw_series.astype(str).str.strip().str.replace("$", "", regex=False).str.replace(",", "", regex=False)
            num_series = pd.to_numeric(clean_str, errors="coerce")
            # Unparseable non-null/non-blank strings are malformed numeric values
            non_empty_mask = ~raw_series.isna() & ~raw_series.astype(str).str.strip().isin(["", "NULL", "null", "None", "nan", "NaN"])
            malformed_mask = non_empty_mask & num_series.isna()
            malformed_count = int(malformed_mask.sum())

        violations_mask = pd.Series(False, index=df.index)

        # 1. Negative amounts check
        negative_count = 0
        if not self.allow_negative:
            negative_mask = num_series < 0.0
            negative_count = int(negative_mask.fillna(False).sum())
            violations_mask = violations_mask | negative_mask.fillna(False)

        # 2. Min value boundary check
        min_viol_count = 0
        if self.min_value is not None:
            min_viol_mask = num_series < self.min_value
            min_viol_count = int(min_viol_mask.fillna(False).sum())
            violations_mask = violations_mask | min_viol_mask.fillna(False)

        # 3. Max value boundary check
        max_viol_count = 0
        if self.max_value is not None:
            max_viol_mask = num_series > self.max_value
            max_viol_count = int(max_viol_mask.fillna(False).sum())
            violations_mask = violations_mask | max_viol_mask.fillna(False)

        total_violations = int(violations_mask.sum()) + malformed_count
        violation_pct = (total_violations / total_rows) * 100.0
        status = DataQualityStatus.FAIL if total_violations > 0 else DataQualityStatus.PASS

        if total_violations > 0:
            details = []
            if negative_count > 0:
                details.append(f"{negative_count} negative amounts")
            if min_viol_count > 0:
                details.append(f"{min_viol_count} below minimum ({self.min_value})")
            if max_viol_count > 0:
                details.append(f"{max_viol_count} above maximum ({self.max_value})")
            if malformed_count > 0:
                details.append(f"{malformed_count} malformed/non-numeric values")

            message = f"Financial rule violation on '{self.field_name}': {', '.join(details)} ({violation_pct:.2f}% of rows)."
        else:
            message = f"Financial amounts on '{self.field_name}' satisfied non-negative and range rules."

        return self._build_result(
            status=status,
            expected={
                "allow_negative": self.allow_negative,
                "min_value": self.min_value,
                "max_value": self.max_value,
            },
            actual={
                "negative_count": negative_count,
                "malformed_count": malformed_count,
                "total_violations": total_violations,
                "violation_pct": round(violation_pct, 4),
            },
            affected_row_count=total_violations,
            total_rows=total_rows,
            message=message,
            fields=[self.field_name],
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={
                "negative_count": negative_count,
                "malformed_count": malformed_count,
            },
        )

    def _evaluate_payment_vs_charge(
        self, df: pd.DataFrame, total_rows: int, start_time: float
    ) -> RuleResult:
        fields = [self.payment_field, self.charge_field]
        missing = [f for f in fields if f not in df.columns]
        if missing:
            return self._build_result(
                status=DataQualityStatus.WARNING,
                expected=f"Fields {fields} present",
                actual=f"Missing fields: {missing}",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"Payment vs charge check skipped due to missing fields: {missing}.",
                fields=fields,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        pmt_num = pd.to_numeric(df[self.payment_field].astype(str).str.replace(",", ""), errors="coerce")
        chrg_num = pd.to_numeric(df[self.charge_field].astype(str).str.replace(",", ""), errors="coerce")

        # Payment should not exceed charge when both are positive and present
        valid_both = ~pmt_num.isna() & ~chrg_num.isna() & (pmt_num > 0) & (chrg_num > 0)
        exceed_mask = valid_both & (pmt_num > chrg_num)
        exceed_count = int(exceed_mask.sum())
        exceed_pct = (exceed_count / total_rows) * 100.0

        status = DataQualityStatus.WARNING if exceed_count > 0 else DataQualityStatus.PASS
        if exceed_count > 0:
            message = f"Payment exceeds total charge in {exceed_count} rows ({exceed_pct:.2f}%)."
        else:
            message = f"Payment amount is within total charge amount across all {total_rows:,} records."

        return self._build_result(
            status=status,
            expected=f"{self.payment_field} <= {self.charge_field}",
            actual={"exceed_count": exceed_count, "exceed_pct": round(exceed_pct, 4)},
            affected_row_count=exceed_count,
            total_rows=total_rows,
            message=message,
            fields=fields,
            execution_time_seconds=time.perf_counter() - start_time,
        )
