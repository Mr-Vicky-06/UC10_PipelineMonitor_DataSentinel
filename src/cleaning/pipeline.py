"""
Pipeline integration and execution orchestrator for the Data Cleaning Module.
Integrates Schema Validation gating before invoking DataCleaner.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
import uuid

import pandas as pd

from src.validation import ValidationStatus, validate_dataset

from .cleaner import DataCleaner
from .loader import load_cleaning_config_by_name
from .models import CleaningMetrics, CleaningReport, CleaningResult, CleaningStatus


def clean_dataset(
    dataset: str,
    input_path_or_df: Union[str, Path, pd.DataFrame],
    output_path: Optional[Union[str, Path]] = None,
    report_path: Optional[Union[str, Path]] = None,
    run_schema_validation: bool = True,
    schemas_dir: Optional[Union[str, Path]] = None,
    cleaning_configs_dir: Optional[Union[str, Path]] = None,
    output_base_dir: Optional[Union[str, Path]] = None,
    run_id: Optional[str] = None,
) -> CleaningResult:
    """
    Main pipeline entry point for Data Cleaning.
    1. Runs Schema Validation as an early gate (if enabled).
    2. If schema validation fails, stops and returns FAILED CleaningResult.
    3. If schema validation passes, executes DataCleaner.
    4. Writes cleaned data and JSON audit report to pipeline_output/ if paths are configured.
    """
    active_run_id = run_id or f"clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_time_iso = datetime.now().isoformat()

    # Determine file path string if applicable
    input_file_str = str(input_path_or_df) if isinstance(input_path_or_df, (str, Path)) else "In-Memory DataFrame"

    # 1. Early Gate: Schema Validation
    if run_schema_validation:
        val_result = validate_dataset(dataset, input_path_or_df, schemas_dir=schemas_dir)
        if not val_result.passed:
            # Schema Validation failed -> Halt cleaning and quarantine
            metrics = CleaningMetrics(
                input_rows=val_result.total_rows,
                output_rows=0,
                unresolved_records=val_result.total_rows,
            )
            report = CleaningReport(
                run_id=active_run_id,
                dataset=dataset,
                input_file=input_file_str,
                output_file=None,
                start_time=start_time_iso,
                end_time=datetime.now().isoformat(),
                metrics=metrics,
                status=CleaningStatus.FAILED,
                warnings=[f"Schema validation failed with {val_result.error_count} error(s). Cleaning halted."],
                schema_validation_passed=False,
            )
            return CleaningResult(cleaned_df=pd.DataFrame(), report=report, passed=False)

    # 2. Load In-Memory DataFrame
    if isinstance(input_path_or_df, pd.DataFrame):
        raw_df = input_path_or_df
    else:
        path = Path(input_path_or_df)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        # Detect delimiter
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            header = f.readline()
        delim = "|" if "|" in header else ("," if "," in header else "\t")
        raw_df = pd.read_csv(path, sep=delim, dtype=str, keep_default_na=False)

    # 3. Load Cleaning Config & Execute Cleaner
    config = load_cleaning_config_by_name(dataset, config_dir=cleaning_configs_dir)
    cleaner = DataCleaner(config)
    result = cleaner.clean(raw_df, run_id=active_run_id, input_file=input_file_str, output_file=str(output_path) if output_path else None)

    # 4. Resolve Output Directories if not provided
    if output_base_dir is None:
        project_root = Path(__file__).resolve().parent.parent.parent
        output_base_dir = project_root / "pipeline_output"

    output_base_dir = Path(output_base_dir)

    # Save cleaned file if requested or if output_base_dir is used
    if output_path is not None:
        target_out = Path(output_path)
        target_out.parent.mkdir(parents=True, exist_ok=True)
        result.cleaned_df.to_csv(target_out, sep=config.output_delimiter, index=False)
        result.report.output_file = str(target_out)

    if report_path is not None:
        target_rep = Path(report_path)
        target_rep.parent.mkdir(parents=True, exist_ok=True)
        with open(target_rep, "w", encoding="utf-8") as f:
            f.write(result.report.to_json(indent=2))

    return result
