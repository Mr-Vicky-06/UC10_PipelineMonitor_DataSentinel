"""
Rule Groups D & E: Clinical Code (ICD-10 & HCPCS/CPT) Validation Rules.
Validates diagnosis and procedure codes against authoritative reference tables if provided,
or explicitly reports the missing reference dependency.
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set, Union
import pandas as pd

from ..models import (
    ClinicalCodeRuleConfig,
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    RuleResult,
)
from .base import BaseDataQualityRule


class ClinicalCodeRule(BaseDataQualityRule):
    """Validates clinical coding systems (ICD-10 diagnosis, HCPCS/CPT procedures)."""

    def __init__(self, config: ClinicalCodeRuleConfig, dataset_name: str):
        super().__init__(
            rule_id=config.id,
            rule_name=config.name,
            category=DataQualityCategory.CLINICAL_CODE,
            dataset=dataset_name,
            severity=config.severity,
            description=config.description,
            enabled=config.enabled,
        )
        self.field_name = config.field
        self.code_system = config.code_system
        self.reference_dataset = config.reference_dataset
        self.reference_field = config.reference_field
        self.reference_path = config.reference_path
        self.on_missing_reference = config.on_missing_reference

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
                expected=f"Valid {self.code_system} codes",
                actual="0 rows evaluated",
                affected_row_count=0,
                total_rows=0,
                message=f"Dataset is empty; clinical code rule '{self.rule_name}' passed trivially.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        if self.field_name not in df.columns:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected=f"Field '{self.field_name}' present",
                actual="Field not present in dataset",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"Clinical field '{self.field_name}' not present in dataset; check skipped.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # 1. Resolve reference code set
        valid_codes = self._resolve_reference_codes(reference_datasets)

        if valid_codes is None:
            # Reference dataset is unavailable — DO NOT guess or download external data
            status = DataQualityStatus.WARNING if self.severity == DataQualitySeverity.WARNING else DataQualityStatus.PASS
            message = (
                f"{self.code_system} reference dataset '{self.reference_dataset}' unavailable in environment. "
                f"Rule '{self.rule_name}' skipped (explicit reference dependency)."
            )
            return self._build_result(
                status=status,
                expected=f"Authoritative {self.code_system} dictionary",
                actual="Reference dataset unavailable",
                affected_row_count=0,
                total_rows=total_rows,
                message=message,
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
                metadata={
                    "missing_reference": True,
                    "reference_dataset": self.reference_dataset,
                    "code_system": self.code_system,
                },
            )

        # 2. Evaluate codes against reference
        series = df[self.field_name].dropna().astype(str).str.strip()
        # Exclude blanks/null representations
        valid_non_empty = series[~series.isin(["", "NULL", "null", "None", "nan", "NaN"])]

        if len(valid_non_empty) == 0:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected=f"Valid {self.code_system} codes",
                actual="No non-null clinical codes present",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"No non-null codes to validate in '{self.field_name}'.",
                fields=[self.field_name],
                execution_time_seconds=time.perf_counter() - start_time,
                metadata={"valid_codes_in_reference": len(valid_codes)},
            )

        invalid_mask = ~valid_non_empty.isin(valid_codes)
        invalid_count = int(invalid_mask.sum())
        invalid_pct = (invalid_count / total_rows) * 100.0

        status = DataQualityStatus.FAIL if invalid_count > 0 else DataQualityStatus.PASS
        if invalid_count > 0:
            message = (
                f"Found {invalid_count} invalid {self.code_system} code(s) ({invalid_pct:.2f}%) "
                f"in '{self.field_name}' not matching reference dictionary."
            )
        else:
            message = f"All {len(valid_non_empty):,} populated codes in '{self.field_name}' match {self.code_system} reference."

        return self._build_result(
            status=status,
            expected=f"Codes in {self.code_system} reference dictionary ({len(valid_codes):,} entries)",
            actual={"invalid_code_count": invalid_count, "invalid_pct": round(invalid_pct, 4)},
            affected_row_count=invalid_count,
            total_rows=total_rows,
            message=message,
            fields=[self.field_name],
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={
                "code_system": self.code_system,
                "invalid_code_count": invalid_count,
                "reference_size": len(valid_codes),
            },
        )

    def _resolve_reference_codes(
        self, reference_datasets: Optional[Dict[str, Any]]
    ) -> Optional[Set[str]]:
        """Look for reference dataset in passed dictionary or on disk."""
        if reference_datasets and self.reference_dataset in reference_datasets:
            ref_data = reference_datasets[self.reference_dataset]
            if ref_data is None:
                return None
            if isinstance(ref_data, (set, list, tuple)):
                return set(str(c).strip() for c in ref_data)
            if isinstance(ref_data, pd.DataFrame):
                col = self.reference_field if self.reference_field in ref_data.columns else ref_data.columns[0]
                return set(ref_data[col].dropna().astype(str).str.strip().unique())
            if isinstance(ref_data, (str, Path)):
                ref_path = Path(ref_data)
                if ref_path.exists():
                    df_ref = pd.read_csv(ref_path)
                    col = self.reference_field if self.reference_field in df_ref.columns else df_ref.columns[0]
                    return set(df_ref[col].dropna().astype(str).str.strip().unique())

        if self.reference_path:
            ref_path = Path(self.reference_path)
            if ref_path.exists():
                df_ref = pd.read_csv(ref_path)
                col = self.reference_field if self.reference_field in df_ref.columns else df_ref.columns[0]
                return set(df_ref[col].dropna().astype(str).str.strip().unique())

        return None
