"""
DataSentinal Data Quality Validation Engine (Layer 2 / Component 1).
"""

from .engine import DataQualityEngine, evaluate_data_quality
from .loader import load_rules_by_name, load_rules_from_dict, load_rules_from_yaml
from .models import (
    ClinicalCodeRuleConfig,
    CompletenessRuleConfig,
    DataQualityCategory,
    DataQualityDatasetConfig,
    DataQualityReport,
    DataQualitySeverity,
    DataQualityStatus,
    DateLogicRuleConfig,
    FinancialRuleConfig,
    ReferentialIntegrityRuleConfig,
    RuleResult,
    SchemaGateConfig,
    UniquenessRuleConfig,
    ValidityRuleConfig,
)
from .results import (
    format_quality_json,
    format_quality_markdown,
    format_quality_summary,
)

__all__ = [
    "DataQualityEngine",
    "evaluate_data_quality",
    "DataQualityReport",
    "RuleResult",
    "DataQualityStatus",
    "DataQualitySeverity",
    "DataQualityCategory",
    "DataQualityDatasetConfig",
    "CompletenessRuleConfig",
    "UniquenessRuleConfig",
    "FinancialRuleConfig",
    "ClinicalCodeRuleConfig",
    "DateLogicRuleConfig",
    "ReferentialIntegrityRuleConfig",
    "ValidityRuleConfig",
    "SchemaGateConfig",
    "load_rules_by_name",
    "load_rules_from_yaml",
    "load_rules_from_dict",
    "format_quality_summary",
    "format_quality_json",
    "format_quality_markdown",
]
