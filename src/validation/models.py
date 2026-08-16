"""
Data models and contracts for the Schema Validation Module.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union


class ValidationStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ValidationCategory(str, Enum):
    FILE_STRUCTURE = "FILE_STRUCTURE"
    COLUMNS = "COLUMNS"
    DATA_TYPES = "DATA_TYPES"
    DATE_FORMATS = "DATE_FORMATS"
    NULLABILITY = "NULLABILITY"
    IDENTIFIERS = "IDENTIFIERS"
    KEYS = "KEYS"


@dataclass(frozen=True)
class FieldSchema:
    name: str
    type: str  # 'string', 'integer', 'float', 'date', 'boolean'
    required: bool = True
    nullable: bool = False
    date_formats: List[str] = field(default_factory=list)
    allowed_values: Optional[List[Any]] = None
    description: str = ""


@dataclass
class SchemaContract:
    dataset_name: str
    version: str = "1.0.0"
    description: str = ""
    primary_key: List[str] = field(default_factory=list)
    default_delimiter: str = ","
    allow_additional_columns: bool = True
    strict_mode: bool = False
    fields: Dict[str, FieldSchema] = field(default_factory=dict)

    def get_required_fields(self) -> List[str]:
        return [name for name, f in self.fields.items() if f.required]

    def get_non_nullable_fields(self) -> List[str]:
        return [name for name, f in self.fields.items() if not f.nullable]

    def get_date_fields(self) -> Dict[str, List[str]]:
        return {name: f.date_formats for name, f in self.fields.items() if f.type == "date"}


@dataclass
class ValidationIssue:
    category: ValidationCategory
    check_name: str
    status: ValidationStatus
    severity: ValidationSeverity
    message: str
    column: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    affected_row_count: int = 0
    sample_indices: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "check": self.check_name,
            "status": self.status.value,
            "severity": self.severity.value,
            "column": self.column,
            "expected": self.expected,
            "actual": self.actual,
            "affected_row_count": self.affected_row_count,
            "message": self.message,
        }


@dataclass
class ValidationResult:
    dataset: str
    file_path: Optional[str]
    status: ValidationStatus
    total_rows: int
    total_columns: int
    issues: List[ValidationIssue] = field(default_factory=list)
    execution_time_seconds: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status != ValidationStatus.FAIL

    @property
    def has_warnings(self) -> bool:
        return self.status == ValidationStatus.WARNING

    @property
    def error_count(self) -> int:
        return sum(
            1
            for i in self.issues
            if i.status == ValidationStatus.FAIL
            or i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1
            for i in self.issues
            if i.status == ValidationStatus.WARNING
            or i.severity == ValidationSeverity.WARNING
        )

    @property
    def info_count(self) -> int:
        return sum(
            1
            for i in self.issues
            if i.status == ValidationStatus.PASS
            and i.severity == ValidationSeverity.INFO
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "file": self.file_path,
            "status": self.status.value,
            "passed": self.passed,
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "execution_time_seconds": round(self.execution_time_seconds, 4),
            "issues": [issue.to_dict() for issue in self.issues],
        }
