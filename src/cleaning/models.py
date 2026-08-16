"""
Data models and report schemas for the Data Cleaning Module.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Sequence, Union


class CleaningStatus(str, Enum):
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    FAILED = "FAILED"


@dataclass
class CleaningConfig:
    dataset_name: str
    version: str = "1.1.0"
    description: str = ""
    null_representations: List[str] = field(default_factory=list)
    canonical_null: str = ""
    mandatory_fields: List[str] = field(default_factory=list)
    canonical_date_format: str = "%Y-%m-%d"
    accepted_date_formats: List[str] = field(default_factory=list)
    date_fields: List[str] = field(default_factory=list)
    identifier_fields: List[str] = field(default_factory=list)
    code_fields: List[str] = field(default_factory=list)
    numeric_fields: List[str] = field(default_factory=list)
    categorical_fields: List[str] = field(default_factory=list)
    free_text_fields: List[str] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    output_delimiter: str = ","


@dataclass
class CleaningMetrics:
    # Row-level metrics
    input_rows: int = 0
    output_rows: int = 0
    rows_changed: int = 0
    rows_removed: int = 0
    exact_duplicate_rows_removed: int = 0
    conflicting_key_groups_found: int = 0
    unresolved_records: int = 0

    # Cell-level metrics
    null_cells_normalized: int = 0
    whitespace_cells_normalized: int = 0
    date_cells_normalized: int = 0
    numeric_cells_normalized: int = 0
    categorical_cells_normalized: int = 0
    code_cells_normalized: int = 0
    unresolved_mandatory_null_count: int = 0
    unresolved_invalid_date_count: int = 0

    # Performance
    execution_time_seconds: float = 0.0

    # Properties for backward compatibility with aliases
    @property
    def nulls_normalized(self) -> int:
        return self.null_cells_normalized

    @property
    def whitespace_normalized(self) -> int:
        return self.whitespace_cells_normalized

    @property
    def dates_normalized(self) -> int:
        return self.date_cells_normalized

    @property
    def numeric_values_normalized(self) -> int:
        return self.numeric_cells_normalized

    @property
    def categoricals_normalized(self) -> int:
        return self.categorical_cells_normalized

    @property
    def exact_duplicates_removed(self) -> int:
        return self.exact_duplicate_rows_removed

    @property
    def conflicting_duplicates_found(self) -> int:
        return self.conflicting_key_groups_found

    def to_dict(self) -> Dict[str, Any]:
        return {
            # Explicit Row-level counts
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "rows_changed": self.rows_changed,
            "rows_removed": self.rows_removed,
            "exact_duplicate_rows_removed": self.exact_duplicate_rows_removed,
            "conflicting_key_groups_found": self.conflicting_key_groups_found,
            "unresolved_records": self.unresolved_records,
            # Explicit Cell-level counts
            "null_cells_normalized": self.null_cells_normalized,
            "whitespace_cells_normalized": self.whitespace_cells_normalized,
            "date_cells_normalized": self.date_cells_normalized,
            "numeric_cells_normalized": self.numeric_cells_normalized,
            "categorical_cells_normalized": self.categorical_cells_normalized,
            "code_cells_normalized": self.code_cells_normalized,
            "unresolved_mandatory_null_count": self.unresolved_mandatory_null_count,
            "unresolved_invalid_date_count": self.unresolved_invalid_date_count,
            "execution_time_seconds": round(self.execution_time_seconds, 4),
        }


@dataclass
class CleaningReport:
    run_id: str
    dataset: str
    input_file: Optional[str]
    output_file: Optional[str]
    start_time: str
    end_time: str
    metrics: CleaningMetrics
    status: CleaningStatus
    warnings: List[str] = field(default_factory=list)
    schema_validation_passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dataset": self.dataset,
            "input_file": self.input_file,
            "output_file": self.output_file,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value,
            "schema_validation_passed": self.schema_validation_passed,
            "metrics": self.metrics.to_dict(),
            "warnings": self.warnings,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class CleaningResult:
    cleaned_df: Any  # pd.DataFrame
    report: CleaningReport
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "report": self.report.to_dict(),
        }
