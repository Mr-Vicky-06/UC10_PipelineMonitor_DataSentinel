"""
Configuration loader for Data Quality Validation rules from YAML definitions.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml

from .models import (
    ClinicalCodeRuleConfig,
    CompletenessRuleConfig,
    DataQualityDatasetConfig,
    DataQualitySeverity,
    DateLogicRuleConfig,
    FinancialRuleConfig,
    ReferentialIntegrityRuleConfig,
    SchemaGateConfig,
    UniquenessRuleConfig,
    ValidityRuleConfig,
)


def _parse_severity(val: Any, default: DataQualitySeverity = DataQualitySeverity.ERROR) -> DataQualitySeverity:
    if isinstance(val, DataQualitySeverity):
        return val
    if isinstance(val, str):
        try:
            return DataQualitySeverity(val.upper())
        except ValueError:
            pass
    return default


def load_rules_from_dict(raw: Dict[str, Any]) -> DataQualityDatasetConfig:
    """Parse a raw dictionary into a strongly typed DataQualityDatasetConfig."""
    dataset_name = raw.get("dataset_name", "unknown")
    version = raw.get("version", "1.0.0")
    description = raw.get("description", "")

    # Completeness rules
    completeness_rules = []
    for r in raw.get("completeness_rules", []):
        completeness_rules.append(
            CompletenessRuleConfig(
                id=r.get("id", f"DQ-COMP-{len(completeness_rules)+1}"),
                name=r.get("name", "unnamed_completeness"),
                field=r.get("field", ""),
                threshold_null_pct=float(r.get("threshold_null_pct", 0.0)),
                threshold_blank_pct=float(r.get("threshold_blank_pct", 0.0)),
                severity=_parse_severity(r.get("severity"), DataQualitySeverity.ERROR),
                description=r.get("description", ""),
                enabled=r.get("enabled", True),
            )
        )

    # Uniqueness rules
    uniqueness_rules = []
    for r in raw.get("uniqueness_rules", []):
        fields = r.get("fields", [])
        if isinstance(fields, str):
            fields = [fields]
        uniqueness_rules.append(
            UniquenessRuleConfig(
                id=r.get("id", f"DQ-DUP-{len(uniqueness_rules)+1}"),
                name=r.get("name", "unnamed_uniqueness"),
                fields=fields,
                threshold_duplicate_pct=float(r.get("threshold_duplicate_pct", 0.0)),
                severity=_parse_severity(r.get("severity"), DataQualitySeverity.ERROR),
                description=r.get("description", ""),
                enabled=r.get("enabled", True),
            )
        )

    # Financial rules
    financial_rules = []
    for r in raw.get("financial_rules", []):
        min_val = r.get("min_value")
        max_val = r.get("max_value")
        financial_rules.append(
            FinancialRuleConfig(
                id=r.get("id", f"DQ-FIN-{len(financial_rules)+1}"),
                name=r.get("name", "unnamed_financial"),
                field=r.get("field"),
                allow_negative=bool(r.get("allow_negative", False)),
                min_value=float(min_val) if min_val is not None else None,
                max_value=float(max_val) if max_val is not None else None,
                payment_field=r.get("payment_field"),
                charge_field=r.get("charge_field"),
                severity=_parse_severity(r.get("severity"), DataQualitySeverity.ERROR),
                description=r.get("description", ""),
                enabled=r.get("enabled", True),
            )
        )

    # Clinical code rules
    clinical_code_rules = []
    for r in raw.get("clinical_code_rules", []):
        clinical_code_rules.append(
            ClinicalCodeRuleConfig(
                id=r.get("id", f"DQ-CLIN-{len(clinical_code_rules)+1}"),
                name=r.get("name", "unnamed_clinical"),
                field=r.get("field", ""),
                code_system=r.get("code_system", "UNKNOWN"),
                reference_dataset=r.get("reference_dataset", ""),
                reference_field=r.get("reference_field", "code"),
                reference_path=r.get("reference_path"),
                severity=_parse_severity(r.get("severity"), DataQualitySeverity.WARNING),
                on_missing_reference=r.get("on_missing_reference", "REPORT_DEPENDENCY"),
                description=r.get("description", ""),
                enabled=r.get("enabled", True),
            )
        )

    # Date logic rules
    date_logic_rules = []
    for r in raw.get("date_logic_rules", []):
        date_logic_rules.append(
            DateLogicRuleConfig(
                id=r.get("id", f"DQ-DATE-{len(date_logic_rules)+1}"),
                name=r.get("name", "unnamed_date_logic"),
                from_date_field=r.get("from_date_field"),
                thru_date_field=r.get("thru_date_field"),
                admission_date_field=r.get("admission_date_field"),
                discharge_date_field=r.get("discharge_date_field"),
                service_date_field=r.get("service_date_field"),
                date_field=r.get("date_field"),
                operator=r.get("operator", "<="),
                allow_future=bool(r.get("allow_future", True)),
                reference_date=r.get("reference_date"),
                severity=_parse_severity(r.get("severity"), DataQualitySeverity.ERROR),
                description=r.get("description", ""),
                enabled=r.get("enabled", True),
            )
        )

    # Referential integrity rules
    referential_integrity_rules = []
    for r in raw.get("referential_integrity_rules", []):
        referential_integrity_rules.append(
            ReferentialIntegrityRuleConfig(
                id=r.get("id", f"DQ-REF-{len(referential_integrity_rules)+1}"),
                name=r.get("name", "unnamed_referential"),
                foreign_key=r.get("foreign_key"),
                reference_dataset=r.get("reference_dataset", ""),
                reference_key=r.get("reference_key"),
                match_key=r.get("match_key"),
                reference_match_key=r.get("reference_match_key"),
                provider_field=r.get("provider_field"),
                reference_provider_field=r.get("reference_provider_field"),
                procedure_field=r.get("procedure_field"),
                reference_procedure_field=r.get("reference_procedure_field"),
                service_date_field=r.get("service_date_field"),
                reference_eff_date_field=r.get("reference_eff_date_field"),
                reference_exp_date_field=r.get("reference_exp_date_field"),
                reference_status_field=r.get("reference_status_field"),
                valid_auth_status=r.get("valid_auth_status", "APPROVED"),
                severity=_parse_severity(r.get("severity"), DataQualitySeverity.ERROR),
                description=r.get("description", ""),
                enabled=r.get("enabled", True),
            )
        )

    # Validity rules
    validity_rules = []
    for r in raw.get("validity_rules", []):
        validity_rules.append(
            ValidityRuleConfig(
                id=r.get("id", f"DQ-VAL-{len(validity_rules)+1}"),
                name=r.get("name", "unnamed_validity"),
                field=r.get("field", ""),
                allowed_values=r.get("allowed_values", []),
                severity=_parse_severity(r.get("severity"), DataQualitySeverity.WARNING),
                description=r.get("description", ""),
                enabled=r.get("enabled", True),
            )
        )

    # Schema gate
    sg_raw = raw.get("schema_gate", {})
    schema_gate = SchemaGateConfig(
        enabled=sg_raw.get("enabled", True),
        severity_on_fail=_parse_severity(sg_raw.get("severity_on_fail"), DataQualitySeverity.CRITICAL),
        severity_on_warning=_parse_severity(sg_raw.get("severity_on_warning"), DataQualitySeverity.WARNING),
        description=sg_raw.get("description", ""),
    )

    return DataQualityDatasetConfig(
        dataset_name=dataset_name,
        version=version,
        description=description,
        completeness_rules=completeness_rules,
        uniqueness_rules=uniqueness_rules,
        financial_rules=financial_rules,
        clinical_code_rules=clinical_code_rules,
        date_logic_rules=date_logic_rules,
        referential_integrity_rules=referential_integrity_rules,
        validity_rules=validity_rules,
        schema_gate=schema_gate,
    )


def load_rules_from_yaml(file_path: Union[str, Path]) -> DataQualityDatasetConfig:
    """Load and parse a data quality YAML configuration file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data quality config file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_dict = yaml.safe_load(f)

    if not isinstance(raw_dict, dict):
        raise ValueError(f"Invalid YAML content in {path}, expected dictionary.")

    return load_rules_from_dict(raw_dict)


def load_rules_by_name(
    dataset_name: str,
    configs_dir: Optional[Union[str, Path]] = None,
) -> DataQualityDatasetConfig:
    """Find and load rules for a dataset by looking up configs/data_quality/<name>_rules.yaml."""
    if configs_dir is None:
        # Default to configs/data_quality relative to workspace or package
        base_dir = Path(__file__).resolve().parent.parent.parent
        configs_dir = base_dir / "configs" / "data_quality"
    else:
        configs_dir = Path(configs_dir)

    target_file = configs_dir / f"{dataset_name.lower()}_rules.yaml"
    if not target_file.exists():
        raise FileNotFoundError(
            f"No data quality config found for dataset '{dataset_name}' at {target_file}"
        )

    return load_rules_from_yaml(target_file)
