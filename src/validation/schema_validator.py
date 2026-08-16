"""
Core Schema Validator module for DataSentinal.
Performs read-only structural and schema validation on incoming healthcare datasets.
"""

import csv
from datetime import datetime
from io import StringIO
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import pandas as pd

from .loader import load_schema_by_name, load_schema_from_yaml
from .models import (
    FieldSchema,
    SchemaContract,
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)


class SchemaValidator:
    """
    Non-mutating schema validator enforcing structural contracts,
    data types, date representations, nullability, and primary/composite keys.
    """

    def __init__(self, schema: Union[SchemaContract, str, Path]):
        if isinstance(schema, (str, Path)):
            path = Path(schema)
            if path.exists():
                self.schema = load_schema_from_yaml(path)
            else:
                self.schema = load_schema_by_name(str(schema))
        elif isinstance(schema, SchemaContract):
            self.schema = schema
        else:
            raise TypeError(f"Expected SchemaContract, str, or Path, got {type(schema)}")

    def validate_file(
        self,
        file_path: Union[str, Path],
        delimiter: Optional[str] = None,
        max_sample_errors: int = 5,
    ) -> ValidationResult:
        """
        Validate a CSV file against the schema contract.
        Reads file safely in read-only mode without mutating the source.
        """
        start_time = time.perf_counter()
        path = Path(file_path)
        issues: List[ValidationIssue] = []

        # 1. Check file existence
        if not path.exists():
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.FILE_STRUCTURE,
                    check_name="file_exists",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Dataset file does not exist: {path}",
                )
            )
            return ValidationResult(
                dataset=self.schema.dataset_name,
                file_path=str(path),
                status=ValidationStatus.FAIL,
                total_rows=0,
                total_columns=0,
                issues=issues,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # 2. Check file readability and delimiter/header structure
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                header_line = f.readline()
        except Exception as e:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.FILE_STRUCTURE,
                    check_name="file_readable",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"File could not be opened/read: {str(e)}",
                )
            )
            return ValidationResult(
                dataset=self.schema.dataset_name,
                file_path=str(path),
                status=ValidationStatus.FAIL,
                total_rows=0,
                total_columns=0,
                issues=issues,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        if not header_line or not header_line.strip():
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.FILE_STRUCTURE,
                    check_name="non_empty_file",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.CRITICAL,
                    message="File is empty (0 bytes or blank header)",
                )
            )
            return ValidationResult(
                dataset=self.schema.dataset_name,
                file_path=str(path),
                status=ValidationStatus.FAIL,
                total_rows=0,
                total_columns=0,
                issues=issues,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Detect delimiter if not explicitly provided
        active_delimiter = delimiter or self._detect_delimiter(header_line, self.schema.default_delimiter)

        # 3. Check for duplicate column names in raw header
        raw_headers = [col.strip() for col in header_line.strip().split(active_delimiter)]
        seen_headers: Set[str] = set()
        duplicate_headers: List[str] = []
        for h in raw_headers:
            if h in seen_headers:
                duplicate_headers.append(h)
            seen_headers.add(h)

        if duplicate_headers:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COLUMNS,
                    check_name="no_duplicate_columns",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate column names detected in header: {duplicate_headers}",
                    actual=duplicate_headers,
                )
            )

        # 4. Load dataframe safely in read-only manner
        try:
            df = pd.read_csv(
                path,
                sep=active_delimiter,
                dtype=str,
                keep_default_na=False,
                on_bad_lines="warn",
                engine="c",
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.FILE_STRUCTURE,
                    check_name="csv_parse_integrity",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.ERROR,
                    message=f"Failed to parse CSV records: {str(e)}",
                )
            )
            return ValidationResult(
                dataset=self.schema.dataset_name,
                file_path=str(path),
                status=ValidationStatus.FAIL,
                total_rows=0,
                total_columns=len(raw_headers),
                issues=issues,
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Validate dataframe content
        df_result = self.validate_dataframe(df, file_name=str(path), max_sample_errors=max_sample_errors)
        all_issues = issues + df_result.issues

        # Determine overall status
        status = self._compute_overall_status(all_issues)

        return ValidationResult(
            dataset=self.schema.dataset_name,
            file_path=str(path),
            status=status,
            total_rows=df_result.total_rows,
            total_columns=df_result.total_columns,
            issues=all_issues,
            execution_time_seconds=time.perf_counter() - start_time,
        )

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        file_name: Optional[str] = None,
        max_sample_errors: int = 5,
    ) -> ValidationResult:
        """
        Validate an in-memory DataFrame against the schema contract without mutating it.
        """
        start_time = time.perf_counter()
        issues: List[ValidationIssue] = []
        total_rows = len(df)
        total_columns = len(df.columns)

        # 1. Empty dataset check
        if total_rows == 0:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.FILE_STRUCTURE,
                    check_name="dataset_not_empty",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.WARNING,
                    message="Dataset contains 0 data rows (header only)",
                    affected_row_count=0,
                )
            )

        present_columns = list(df.columns)
        present_set = set(present_columns)

        # 2. Required columns check
        required_fields = self.schema.get_required_fields()
        missing_required = [f for f in required_fields if f not in present_set]
        if missing_required:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COLUMNS,
                    check_name="required_columns_present",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing {len(missing_required)} required column(s): {missing_required}",
                    expected=required_fields,
                    actual=list(present_columns),
                )
            )

        # 3. Unexpected / Additional columns check
        known_fields = set(self.schema.fields.keys())
        unexpected_columns = [col for col in present_columns if col not in known_fields]
        if unexpected_columns:
            if not self.schema.allow_additional_columns or self.schema.strict_mode:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.COLUMNS,
                        check_name="no_unexpected_columns",
                        status=ValidationStatus.FAIL,
                        severity=ValidationSeverity.ERROR,
                        message=f"Found {len(unexpected_columns)} unexpected column(s) under strict schema: {unexpected_columns}",
                        actual=unexpected_columns,
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.COLUMNS,
                        check_name="additional_columns_info",
                        status=ValidationStatus.WARNING,
                        severity=ValidationSeverity.WARNING,
                        message=f"Dataset contains {len(unexpected_columns)} additional undeclared column(s)",
                        actual=unexpected_columns[:10],
                    )
                )

        # 4. Field-level checks for each column present in dataset and defined in schema
        for col_name, field_schema in self.schema.fields.items():
            if col_name not in present_set:
                continue

            series = df[col_name]
            self._validate_field_nullability(series, field_schema, issues, max_sample_errors)
            self._validate_field_data_type(series, field_schema, issues, max_sample_errors)
            self._validate_field_allowed_values(series, field_schema, issues, max_sample_errors)

        # 5. Primary / Composite Key Uniqueness Check
        if self.schema.primary_key and all(pk in present_set for pk in self.schema.primary_key) and total_rows > 0:
            self._validate_primary_key_uniqueness(df, issues, max_sample_errors)

        # Determine overall status
        status = self._compute_overall_status(issues)

        return ValidationResult(
            dataset=self.schema.dataset_name,
            file_path=file_name,
            status=status,
            total_rows=total_rows,
            total_columns=total_columns,
            issues=issues,
            execution_time_seconds=time.perf_counter() - start_time,
        )

    def _validate_field_nullability(
        self,
        series: pd.Series,
        field_schema: FieldSchema,
        issues: List[ValidationIssue],
        max_samples: int,
    ) -> None:
        """Validate nullability constraints without mutating data."""
        if field_schema.nullable:
            return  # Nulls are explicitly allowed

        # Identify nulls, None, NaN, and whitespace-only strings
        is_null_mask = series.isna() | (series.astype(str).str.strip() == "") | (series.astype(str).str.upper() == "NULL") | (series.astype(str).str.upper() == "NONE")
        null_count = int(is_null_mask.sum())

        if null_count > 0:
            sample_indices = list(series[is_null_mask].index[:max_samples])
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.NULLABILITY,
                    check_name="non_nullable_field",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.ERROR,
                    column=field_schema.name,
                    expected="non-null value",
                    actual=f"{null_count} null/blank entries",
                    affected_row_count=null_count,
                    sample_indices=sample_indices,
                    message=f"Non-nullable column '{field_schema.name}' contains {null_count:,} null/empty values",
                )
            )

    def _validate_field_data_type(
        self,
        series: pd.Series,
        field_schema: FieldSchema,
        issues: List[ValidationIssue],
        max_samples: int,
    ) -> None:
        """Validate logical data types and date formats."""
        # Only evaluate non-null values for datatype compliance
        non_null_mask = ~series.isna() & (series.astype(str).str.strip() != "") & (series.astype(str).str.upper() != "NULL") & (series.astype(str).str.upper() != "NONE")
        non_null_series = series[non_null_mask].astype(str).str.strip()

        if non_null_series.empty:
            return

        expected_type = field_schema.type.lower()

        if expected_type == "integer":
            # Match integers (with optional leading minus/plus sign, no commas or decimal parts)
            invalid_mask = ~non_null_series.str.match(r"^[+-]?\d+$")
            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                samples = list(non_null_series[invalid_mask].index[:max_samples])
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.DATA_TYPES,
                        check_name="integer_type",
                        status=ValidationStatus.FAIL,
                        severity=ValidationSeverity.ERROR,
                        column=field_schema.name,
                        expected="integer (e.g. 123, -123)",
                        actual=f"{invalid_count} non-integer values",
                        affected_row_count=invalid_count,
                        sample_indices=samples,
                        message=f"Column '{field_schema.name}' has {invalid_count:,} value(s) that cannot be parsed as integer",
                    )
                )

        elif expected_type == "float":
            # Match float values (integers, formatted numbers with commas, decimals, scientific notation, optional sign)
            invalid_mask = ~non_null_series.str.match(r"^[+-]?(?:\d+(?:,\d+)*(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                samples = list(non_null_series[invalid_mask].index[:max_samples])
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.DATA_TYPES,
                        check_name="float_type",
                        status=ValidationStatus.FAIL,
                        severity=ValidationSeverity.ERROR,
                        column=field_schema.name,
                        expected="float/numeric (e.g. 123.45, -123.45)",
                        actual=f"{invalid_count} non-numeric values",
                        affected_row_count=invalid_count,
                        sample_indices=samples,
                        message=f"Column '{field_schema.name}' has {invalid_count:,} value(s) that cannot be parsed as float",
                    )
                )

        elif expected_type == "date":
            # Validate date formats against configured formats
            date_formats = field_schema.date_formats or ["%Y-%m-%d", "%d-%b-%Y", "%Y%m%d"]
            invalid_indices = []

            for idx, val in non_null_series.items():
                parsed = False
                for fmt in date_formats:
                    try:
                        datetime.strptime(val, fmt)
                        parsed = True
                        break
                    except ValueError:
                        continue
                if not parsed:
                    invalid_indices.append(idx)

            if invalid_indices:
                invalid_count = len(invalid_indices)
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.DATE_FORMATS,
                        check_name="date_format",
                        status=ValidationStatus.FAIL,
                        severity=ValidationSeverity.ERROR,
                        column=field_schema.name,
                        expected=f"date matching one of {date_formats}",
                        actual=f"{invalid_count} unparseable date values",
                        affected_row_count=invalid_count,
                        sample_indices=invalid_indices[:max_samples],
                        message=f"Column '{field_schema.name}' has {invalid_count:,} malformed date value(s)",
                    )
                )

    def _validate_field_allowed_values(
        self,
        series: pd.Series,
        field_schema: FieldSchema,
        issues: List[ValidationIssue],
        max_samples: int,
    ) -> None:
        """Validate categorical values against allowed_values if specified."""
        if not field_schema.allowed_values:
            return

        non_null_mask = ~series.isna() & (series.astype(str).str.strip() != "") & (series.astype(str).str.upper() != "NULL") & (series.astype(str).str.upper() != "NONE")
        non_null_series = series[non_null_mask].astype(str).str.strip()
        allowed_set = {str(val).upper() for val in field_schema.allowed_values}

        invalid_mask = ~non_null_series.str.upper().isin(allowed_set)
        invalid_count = int(invalid_mask.sum())

        if invalid_count > 0:
            samples = list(non_null_series[invalid_mask].index[:max_samples])
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.DATA_TYPES,
                    check_name="allowed_values",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.ERROR,
                    column=field_schema.name,
                    expected=list(field_schema.allowed_values),
                    actual=f"{invalid_count} invalid categorical values",
                    affected_row_count=invalid_count,
                    sample_indices=samples,
                    message=f"Column '{field_schema.name}' contains {invalid_count:,} value(s) outside allowed set: {field_schema.allowed_values}",
                )
            )

    def _validate_primary_key_uniqueness(
        self,
        df: pd.DataFrame,
        issues: List[ValidationIssue],
        max_samples: int,
    ) -> None:
        """
        Validate primary / composite key uniqueness across the dataset.
        For claims, respects composite grain ['CLM_ID', 'CLM_LINE_NUM'].
        """
        pk_cols = self.schema.primary_key
        duplicated_mask = df.duplicated(subset=pk_cols, keep=False)
        dup_count = int(duplicated_mask.sum())

        if dup_count > 0:
            sample_indices = list(df[duplicated_mask].index[:max_samples])
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.KEYS,
                    check_name="primary_key_uniqueness",
                    status=ValidationStatus.FAIL,
                    severity=ValidationSeverity.ERROR,
                    column="+".join(pk_cols),
                    expected=f"Unique {pk_cols}",
                    actual=f"{dup_count} duplicate rows found",
                    affected_row_count=dup_count,
                    sample_indices=sample_indices,
                    message=f"Duplicate primary key entries detected on {pk_cols} ({dup_count:,} rows affected)",
                )
            )

    def _detect_delimiter(self, header_line: str, fallback: str = ",") -> str:
        """Detect file delimiter from header line."""
        delimiters = ["|", ",", "\t", ";"]
        counts = {d: header_line.count(d) for d in delimiters}
        best_delim = max(counts, key=counts.get)
        return best_delim if counts[best_delim] > 0 else fallback

    def _compute_overall_status(self, issues: Sequence[ValidationIssue]) -> ValidationStatus:
        """Compute the aggregate validation status from the issue list."""
        if any(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL) or i.status == ValidationStatus.FAIL for i in issues):
            return ValidationStatus.FAIL
        if any(i.severity == ValidationSeverity.WARNING or i.status == ValidationStatus.WARNING for i in issues):
            return ValidationStatus.WARNING
        return ValidationStatus.PASS


def validate_dataset(
    dataset_name: str,
    file_path_or_df: Union[str, Path, pd.DataFrame],
    schemas_dir: Optional[Union[str, Path]] = None,
    delimiter: Optional[str] = None,
) -> ValidationResult:
    """
    Convenience functional entry point for the pipeline to validate datasets.
    """
    validator = SchemaValidator(load_schema_by_name(dataset_name, schemas_dir))
    if isinstance(file_path_or_df, pd.DataFrame):
        return validator.validate_dataframe(file_path_or_df)
    return validator.validate_file(file_path_or_df, delimiter=delimiter)
