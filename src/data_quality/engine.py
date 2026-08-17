
"""
Data Quality Validation Engine (Layer 2 / Component 1).
Orchestrates rule instantiation, execution, measurement, and result aggregation for healthcare datasets.
"""

from datetime import datetime
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union
import uuid
import pandas as pd

from .loader import load_rules_by_name, load_rules_from_dict, load_rules_from_yaml
from .models import (
    DataQualityDatasetConfig,
    DataQualityReport,
    DataQualitySeverity,
    DataQualityStatus,
    RuleResult,
)
from .rules import (
    BaseDataQualityRule,
    ClinicalCodeRule,
    CompletenessRule,
    DateLogicRule,
    FinancialAmountRule,
    ReferentialIntegrityRule,
    SchemaGateRule,
    UniquenessRule,
    ValidityRule,
)

logger = logging.getLogger("DataSentinal.DataQualityEngine")


class DataQualityEngine:
    """
    Production Data Quality Validation Engine.
    Evaluates in-memory DataFrames or files against centralized YAML rule definitions.
    Strictly non-mutating (Read-Only).
    """

    def __init__(self, config: Union[DataQualityDatasetConfig, str, Path, Dict[str, Any]]):
        if isinstance(config, DataQualityDatasetConfig):
            self.config = config
        elif isinstance(config, (str, Path)):
            self.config = load_rules_from_yaml(config)
        elif isinstance(config, dict):
            self.config = load_rules_from_dict(config)
        else:
            raise TypeError(f"Unsupported config type: {type(config)}")

        self.dataset_name = self.config.dataset_name
        self.rules: List[BaseDataQualityRule] = self._instantiate_rules()

    def _instantiate_rules(self) -> List[BaseDataQualityRule]:
        """Instantiate configured rule evaluators in logical order."""
        instantiated: List[BaseDataQualityRule] = []

        # 1. Schema gate (upstream gate result)
        if self.config.schema_gate and self.config.schema_gate.enabled:
            instantiated.append(SchemaGateRule(self.config.schema_gate, self.dataset_name))

        # 2. Completeness rules (Group A)
        for comp_cfg in self.config.completeness_rules:
            if comp_cfg.enabled:
                instantiated.append(CompletenessRule(comp_cfg, self.dataset_name))

        # 3. Uniqueness rules (Group B)
        for unq_cfg in self.config.uniqueness_rules:
            if unq_cfg.enabled:
                instantiated.append(UniquenessRule(unq_cfg, self.dataset_name))

        # 4. Financial rules (Group C)
        for fin_cfg in self.config.financial_rules:
            if fin_cfg.enabled:
                instantiated.append(FinancialAmountRule(fin_cfg, self.dataset_name))

        # 5. Clinical code rules (Groups D & E)
        for clin_cfg in self.config.clinical_code_rules:
            if clin_cfg.enabled:
                instantiated.append(ClinicalCodeRule(clin_cfg, self.dataset_name))

        # 6. Date logic rules (Group F)
        for dt_cfg in self.config.date_logic_rules:
            if dt_cfg.enabled:
                instantiated.append(DateLogicRule(dt_cfg, self.dataset_name))

        # 7. Validity / Domain rules
        for val_cfg in self.config.validity_rules:
            if val_cfg.enabled:
                instantiated.append(ValidityRule(val_cfg, self.dataset_name))

        # 8. Referential integrity rules (Group G)
        for ref_cfg in self.config.referential_integrity_rules:
            if ref_cfg.enabled:
                instantiated.append(ReferentialIntegrityRule(ref_cfg, self.dataset_name))

        return instantiated

    def evaluate_dataframe(
        self,
        df: pd.DataFrame,
        reference_datasets: Optional[Dict[str, Any]] = None,
        schema_validation_result: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
    ) -> DataQualityReport:
        """
        Evaluate all configured data quality rules against the given DataFrame.
        Zero mutation guarantee: Does NOT modify input DataFrame.
        """
        start_time = time.perf_counter()
        total_rows = len(df)
        total_cols = len(df.columns)

        ctx = dict(context or {})
        if schema_validation_result is not None:
            ctx["schema_validation_result"] = schema_validation_result

        run_id = ctx.get("run_id")
        batch_id = ctx.get("batch_id")
        hospital_id = ctx.get("hospital_id")
        report_id = f"DQR_{self.dataset_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        rule_results: List[RuleResult] = []

        # Execute rules sequentially
        for rule in self.rules:
            try:
                res = rule.evaluate(df, context=ctx, reference_datasets=reference_datasets)
                rule_results.append(res)
            except Exception as exc:
                # Catch unexpected rule exceptions and record as critical failure without crashing engine
                err_res = RuleResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    category=rule.category,
                    dataset=self.dataset_name,
                    fields=[],
                    status=DataQualityStatus.FAIL,
                    severity=DataQualitySeverity.CRITICAL,
                    expected="Clean rule execution",
                    actual=f"Exception: {type(exc).__name__}",
                    affected_row_count=total_rows,
                    affected_percentage=100.0,
                    message=f"Unhandled exception during rule execution: {str(exc)}",
                    execution_time_seconds=0.0,
                    metadata={"error": str(exc)},
                )
                rule_results.append(err_res)

        total_duration = time.perf_counter() - start_time

        # Determine overall status
        failed_count = sum(1 for r in rule_results if r.status == DataQualityStatus.FAIL)
        warning_count = sum(1 for r in rule_results if r.status == DataQualityStatus.WARNING)

        if failed_count > 0:
            overall_status = DataQualityStatus.FAIL
        elif warning_count > 0:
            overall_status = DataQualityStatus.WARNING
        else:
            overall_status = DataQualityStatus.PASS

        # Schema status string for summary
        schema_status_str = None
        if schema_validation_result is not None:
            if hasattr(schema_validation_result, "status"):
                schema_status_str = str(
                    schema_validation_result.status.value
                    if hasattr(schema_validation_result.status, "value")
                    else schema_validation_result.status
                )
            elif isinstance(schema_validation_result, dict):
                schema_status_str = str(schema_validation_result.get("status", "PASS"))
            elif isinstance(schema_validation_result, str):
                schema_status_str = schema_validation_result

        report = DataQualityReport(
            report_id=report_id,
            dataset=self.dataset_name,
            file_path=file_path,
            run_id=run_id,
            batch_id=batch_id,
            hospital_id=hospital_id,
            total_rows=total_rows,
            total_columns=total_cols,
            overall_status=overall_status,
            schema_validation_status=schema_status_str,
            execution_time_seconds=total_duration,
            rule_results=rule_results,
        )

        logger.info(
            "Data Quality evaluation completed for dataset '%s': %d rows, %d rules, %d failed, %d warnings in %.4fs (Status: %s)",
            self.dataset_name,
            total_rows,
            len(rule_results),
            failed_count,
            warning_count,
            total_duration,
            overall_status.value,
        )

        return report

    def evaluate_file(
        self,
        file_path: Union[str, Path],
        delimiter: Optional[str] = None,
        reference_datasets: Optional[Dict[str, Any]] = None,
        schema_validation_result: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        low_memory: bool = False,
    ) -> DataQualityReport:
        """Read a dataset file and evaluate data quality rules against it (Read-Only)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        # Auto-detect delimiter if not specified
        sep = delimiter
        if sep is None:
            if "claims" in path.name.lower() or path.name.endswith(".csv"):
                # Read sample line to detect pipe vs comma
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline()
                sep = "|" if "|" in first_line else ","
            else:
                sep = ","

        df = pd.read_csv(path, sep=sep, low_memory=low_memory, dtype=str)

        return self.evaluate_dataframe(
            df=df,
            reference_datasets=reference_datasets,
            schema_validation_result=schema_validation_result,
            context=context,
            file_path=str(path),
        )


def evaluate_data_quality(
    dataset: str,
    data: Union[pd.DataFrame, str, Path],
    reference_datasets: Optional[Dict[str, Any]] = None,
    schema_validation_result: Optional[Any] = None,
    context: Optional[Dict[str, Any]] = None,
    config_path: Optional[Union[str, Path]] = None,
) -> DataQualityReport:
    """
    Primary functional public entrypoint for Layer 2 Data Quality Validation Engine.
    
    Args:
        dataset: Dataset identifier (e.g. 'claims', 'authorization')
        data: In-memory pandas DataFrame or file path string/Path
        reference_datasets: Optional dictionary of reference DataFrames/paths (e.g. 'authorization', 'hospital_mapping')
        schema_validation_result: Optional upstream ValidationResult from Schema Validation module
        context: Optional dictionary with lineage metadata ('run_id', 'batch_id', 'hospital_id')
        config_path: Optional path to custom YAML rules config file
        
    Returns:
        Structured DataQualityReport with individual RuleResults and aggregated metrics
    """
    if config_path:
        config = load_rules_from_yaml(config_path)
    else:
        config = load_rules_by_name(dataset)

    engine = DataQualityEngine(config)

    if isinstance(data, pd.DataFrame):
        return engine.evaluate_dataframe(
            df=data,
            reference_datasets=reference_datasets,
            schema_validation_result=schema_validation_result,
            context=context,
        )
    elif isinstance(data, (str, Path)):
        return engine.evaluate_file(
            file_path=data,
            reference_datasets=reference_datasets,
            schema_validation_result=schema_validation_result,
            context=context,
        )
    else:
        raise TypeError(f"Expected pandas DataFrame or file path, got {type(data)}")
