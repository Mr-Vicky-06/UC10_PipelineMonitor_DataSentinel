"""
Result formatting and reporting utilities for the Data Quality Validation Engine.
Provides clean terminal summaries, markdown tables, and JSON outputs without exposing PHI.
Designed with ASCII-safe indicators for cross-platform terminal compatibility.
"""

import json
from typing import Any, Dict, Optional
from .models import DataQualityReport, DataQualitySeverity, DataQualityStatus


def format_quality_summary(report: DataQualityReport) -> str:
    """Format a DataQualityReport into a clean, human-readable summary string."""
    if report.overall_status == DataQualityStatus.PASS:
        status_tag = "[PASS]"
    elif report.overall_status == DataQualityStatus.WARNING:
        status_tag = "[WARN]"
    else:
        status_tag = "[FAIL]"

    lines = [
        f"{status_tag} Data Quality Report: {report.dataset.upper()}",
        f"  Report ID: {report.report_id}",
        f"  File / Source: {report.file_path or 'In-Memory DataFrame'}",
        f"  Overall Status: {report.overall_status.value}",
        f"  Total Rows: {report.total_rows:,} | Columns: {report.total_columns}",
        f"  Rules Executed: {report.rules_executed} (Passed: {report.passed_rules}, Failed: {report.failed_rules}, Warnings: {report.warning_rules})",
        f"  Execution Time: {report.execution_time_seconds:.4f}s ({report.throughput_rows_per_second:,.1f} rows/sec)",
    ]

    if report.schema_validation_status:
        lines.append(f"  Upstream Schema Status: {report.schema_validation_status}")

    if report.failed_rules > 0 or report.warning_rules > 0:
        lines.append("  Rule Violations & Warnings:")
        for idx, rule in enumerate(report.rule_results, 1):
            if rule.status in (DataQualityStatus.FAIL, DataQualityStatus.WARNING):
                r_tag = "[FAIL]" if rule.status == DataQualityStatus.FAIL else "[WARN]"
                fields_str = f" [{', '.join(rule.fields)}]" if rule.fields else ""
                lines.append(
                    f"    {idx}. {r_tag} [{rule.severity.value}] {rule.category.value} -> {rule.rule_id} ({rule.rule_name}){fields_str}: {rule.message}"
                )

    return "\n".join(lines)


def format_quality_json(report: DataQualityReport, indent: int = 2) -> str:
    """Format a DataQualityReport into structured JSON."""
    return report.to_json(indent=indent)


def format_quality_markdown(report: DataQualityReport) -> str:
    """Format a DataQualityReport into a Markdown document with summary tables."""
    status_badge = f"**`{report.overall_status.value}`**"
    lines = [
        f"# Data Quality Report — {report.dataset.upper()}",
        "",
        f"- **Report ID:** `{report.report_id}`",
        f"- **Status:** {status_badge}",
        f"- **Total Rows:** {report.total_rows:,}",
        f"- **Total Columns:** {report.total_columns}",
        f"- **Rules Executed:** {report.rules_executed} ({report.passed_rules} Passed, {report.failed_rules} Failed, {report.warning_rules} Warnings)",
        f"- **Execution Time:** {report.execution_time_seconds:.4f}s ({report.throughput_rows_per_second:,.1f} rows/s)",
        "",
        "## Evaluated Rules Summary",
        "",
        "| Rule ID | Rule Name | Category | Status | Severity | Affected Rows | Violation % | Message |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in report.rule_results:
        status_str = "PASS" if r.status == DataQualityStatus.PASS else ("WARN" if r.status == DataQualityStatus.WARNING else "FAIL")
        clean_msg = r.message.replace("|", "\\|")
        lines.append(
            f"| `{r.rule_id}` | `{r.rule_name}` | `{r.category.value}` | `{status_str}` | `{r.severity.value}` | {r.affected_row_count:,} | {r.affected_percentage:.2f}% | {clean_msg} |"
        )

    return "\n".join(lines)
