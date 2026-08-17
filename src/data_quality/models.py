"""
Data models, enums, and result contracts for the Data Quality Validation Engine (Layer 2 / Component 1).
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Sequence, Union


class DataQualityStatus(str, Enum):
    """Execution outcome status for a data quality rule or entire report."""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class DataQualitySeverity(str, Enum):
    """Impact severity level associated with a data quality rule."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DataQualityCategory(str, Enum):
    """Quality dimensions / rule categories."""
    COMPLETENESS = "COMPLETENESS"
    UNIQUENESS = "UNIQUENESS"
    FINANCIAL = "FINANCIAL"
    CLINICAL_CODE = "CLINICAL_CODE"
    DATE_LOGIC = "DATE_LOGIC"
    REFERENTIAL_INTEGRITY = "REFERENTIAL_INTEGRITY"
    VALIDITY = "VALIDITY"
    SCHEMA_CONFORMANCE = "SCHEMA_CONFORMANCE"


@dataclass
class RuleResult:
    """Standardized outcome for an individual data quality rule execution."""
    rule_id: str
    rule_name: str
    category: DataQualityCategory
    dataset: str
    fields: List[str]
    status: DataQualityStatus
    severity: DataQualitySeverity
    expected: Any
    actual: Any
    affected_row_count: int
    affected_percentage: float
    message: str
    execution_time_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "category": self.category.value if isinstance(self.category, DataQualityCategory) else str(self.category),
            "dataset": self.dataset,
            "fields": self.fields,
            "status": self.status.value if isinstance(self.status, DataQualityStatus) else str(self.status),
            "severity": self.severity.value if isinstance(self.severity, DataQualitySeverity) else str(self.severity),
            "expected": self.expected,
            "actual": self.actual,
            "affected_row_count": self.affected_row_count,
            "affected_percentage": round(self.affected_percentage, 4),
            "message": self.message,
            "execution_time_seconds": round(self.execution_time_seconds, 4),
            "metadata": self.metadata,
        }


@dataclass
class DataQualityReport:
    """Aggregated data quality report across all evaluated rules."""
    report_id: str
    dataset: str
    total_rows: int
    total_columns: int
    overall_status: DataQualityStatus
    file_path: Optional[str] = None
    run_id: Optional[str] = None
    batch_id: Optional[str] = None
    hospital_id: Optional[str] = None
    schema_validation_status: Optional[str] = None
    execution_time_seconds: float = 0.0
    rule_results: List[RuleResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.overall_status != DataQualityStatus.FAIL

    @property
    def has_warnings(self) -> bool:
        return self.overall_status == DataQualityStatus.WARNING

    @property
    def has_failures(self) -> bool:
        return self.overall_status == DataQualityStatus.FAIL

    @property
    def rules_executed(self) -> int:
        return len(self.rule_results)

    @property
    def passed_rules(self) -> int:
        return sum(1 for r in self.rule_results if r.status == DataQualityStatus.PASS)

    @property
    def failed_rules(self) -> int:
        return sum(1 for r in self.rule_results if r.status == DataQualityStatus.FAIL)

    @property
    def warning_rules(self) -> int:
        return sum(1 for r in self.rule_results if r.status == DataQualityStatus.WARNING)

    @property
    def throughput_rows_per_second(self) -> float:
        if self.execution_time_seconds > 0:
            return round(self.total_rows / self.execution_time_seconds, 2)
        return 0.0

    def get_failures(self) -> List[RuleResult]:
        return [r for r in self.rule_results if r.status == DataQualityStatus.FAIL]

    def get_warnings(self) -> List[RuleResult]:
        return [r for r in self.rule_results if r.status == DataQualityStatus.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "dataset": self.dataset,
            "file_path": self.file_path,
            "run_id": self.run_id,
            "batch_id": self.batch_id,
            "hospital_id": self.hospital_id,
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "rules_executed": self.rules_executed,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "warning_rules": self.warning_rules,
            "overall_status": self.overall_status.value if isinstance(self.overall_status, DataQualityStatus) else str(self.overall_status),
            "passed": self.passed,
            "schema_validation_status": self.schema_validation_status,
            "execution_time_seconds": round(self.execution_time_seconds, 4),
            "throughput_rows_per_second": self.throughput_rows_per_second,
            "rule_results": [r.to_dict() for r in self.rule_results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# -----------------------------------------------------------------------------
# Configuration Dataclasses
# -----------------------------------------------------------------------------

@dataclass
class CompletenessRuleConfig:
    id: str
    name: str
    field: str
    threshold_null_pct: float = 0.0
    threshold_blank_pct: float = 0.0
    severity: DataQualitySeverity = DataQualitySeverity.ERROR
    description: str = ""
    enabled: bool = True


@dataclass
class UniquenessRuleConfig:
    id: str
    name: str
    fields: List[str] = field(default_factory=list)
    threshold_duplicate_pct: float = 0.0
    severity: DataQualitySeverity = DataQualitySeverity.ERROR
    description: str = ""
    enabled: bool = True


@dataclass
class FinancialRuleConfig:
    id: str
    name: str
    field: Optional[str] = None
    allow_negative: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    payment_field: Optional[str] = None
    charge_field: Optional[str] = None
    severity: DataQualitySeverity = DataQualitySeverity.ERROR
    description: str = ""
    enabled: bool = True


@dataclass
class ClinicalCodeRuleConfig:
    id: str
    name: str
    field: str
    code_system: str
    reference_dataset: str
    reference_field: str = "code"
    reference_path: Optional[str] = None
    severity: DataQualitySeverity = DataQualitySeverity.WARNING
    on_missing_reference: str = "REPORT_DEPENDENCY"  # REPORT_DEPENDENCY, FAIL, PASS
    description: str = ""
    enabled: bool = True


@dataclass
class DateLogicRuleConfig:
    id: str
    name: str
    from_date_field: Optional[str] = None
    thru_date_field: Optional[str] = None
    admission_date_field: Optional[str] = None
    discharge_date_field: Optional[str] = None
    service_date_field: Optional[str] = None
    date_field: Optional[str] = None
    operator: str = "<="
    allow_future: bool = True
    reference_date: Optional[str] = None
    severity: DataQualitySeverity = DataQualitySeverity.ERROR
    description: str = ""
    enabled: bool = True


@dataclass
class ReferentialIntegrityRuleConfig:
    id: str
    name: str
    foreign_key: Optional[str] = None
    reference_dataset: str = ""
    reference_key: Optional[str] = None
    match_key: Optional[str] = None
    reference_match_key: Optional[str] = None
    provider_field: Optional[str] = None
    reference_provider_field: Optional[str] = None
    procedure_field: Optional[str] = None
    reference_procedure_field: Optional[str] = None
    service_date_field: Optional[str] = None
    reference_eff_date_field: Optional[str] = None
    reference_exp_date_field: Optional[str] = None
    reference_status_field: Optional[str] = None
    valid_auth_status: Optional[str] = "APPROVED"
    severity: DataQualitySeverity = DataQualitySeverity.ERROR
    description: str = ""
    enabled: bool = True


@dataclass
class ValidityRuleConfig:
    id: str
    name: str
    field: str
    allowed_values: List[Any] = field(default_factory=list)
    severity: DataQualitySeverity = DataQualitySeverity.WARNING
    description: str = ""
    enabled: bool = True


@dataclass
class SchemaGateConfig:
    enabled: bool = True
    severity_on_fail: DataQualitySeverity = DataQualitySeverity.CRITICAL
    severity_on_warning: DataQualitySeverity = DataQualitySeverity.WARNING
    description: str = ""


@dataclass
class DataQualityDatasetConfig:
    """Complete configured ruleset for a specific dataset."""
    dataset_name: str
    version: str = "1.0.0"
    description: str = ""
    completeness_rules: List[CompletenessRuleConfig] = field(default_factory=list)
    uniqueness_rules: List[UniquenessRuleConfig] = field(default_factory=list)
    financial_rules: List[FinancialRuleConfig] = field(default_factory=list)
    clinical_code_rules: List[ClinicalCodeRuleConfig] = field(default_factory=list)
    date_logic_rules: List[DateLogicRuleConfig] = field(default_factory=list)
    referential_integrity_rules: List[ReferentialIntegrityRuleConfig] = field(default_factory=list)
    validity_rules: List[ValidityRuleConfig] = field(default_factory=list)
    schema_gate: SchemaGateConfig = field(default_factory=SchemaGateConfig)
