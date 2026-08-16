"""
Results formatting and reporting utilities for the Schema Validation Module.
"""

import json
from typing import Any, Dict, List, Optional

from .models import ValidationResult, ValidationSeverity, ValidationStatus


def format_validation_summary(result: ValidationResult) -> str:
    """Format a ValidationResult into a clean, human-readable summary string."""
    status_icon = "✅" if result.passed else "❌"
    if result.has_warnings and result.passed:
        status_icon = "⚠️"

    lines = [
        f"{status_icon} Schema Validation Summary: {result.dataset.upper()}",
        f"  File: {result.file_path or 'In-Memory DataFrame'}",
        f"  Overall Status: {result.status.value}",
        f"  Rows Evaluated: {result.total_rows:,}",
        f"  Columns Present: {result.total_columns}",
        f"  Issues Found: {len(result.issues)} ({result.error_count} Errors, {result.warning_count} Warnings)",
        f"  Execution Time: {result.execution_time_seconds:.4f}s",
    ]

    if result.issues:
        lines.append("  Details:")
        for idx, issue in enumerate(result.issues, 1):
            col_info = f" [Column: {issue.column}]" if issue.column else ""
            rows_info = f" (Affected rows: {issue.affected_row_count})" if issue.affected_row_count > 0 else ""
            lines.append(
                f"    {idx}. [{issue.severity.value}] {issue.category.value} -> {issue.check_name}{col_info}{rows_info}: {issue.message}"
            )

    return "\n".join(lines)


def format_validation_json(result: ValidationResult, indent: int = 2) -> str:
    """Format a ValidationResult into structured JSON."""
    return json.dumps(result.to_dict(), indent=indent)
