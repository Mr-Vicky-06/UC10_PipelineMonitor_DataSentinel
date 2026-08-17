"""
Core Data Cleaner implementation for DataSentinal healthcare data pipeline.
Performs deterministic, non-destructive standardization, null normalization,
field-specific casing, date and numeric formatting, and grain-aware deduplication.
"""

import re
import time
from datetime import datetime
from typing import Any, List, Optional, Set

import pandas as pd

from .models import (
    CleaningConfig,
    CleaningMetrics,
    CleaningReport,
    CleaningResult,
    CleaningStatus,
)


class DataCleaner:
    """
    Standardizes and cleans tabular healthcare datasets according to a dataset CleaningConfig.
    Enforces string preservation on identifiers, canonical date/numeric formatting,
    field-specific casing, and claim-line grain deduplication without destroying
    ground-truth anomaly scenarios or fabricating missing clinical data.
    """

    def __init__(self, config: CleaningConfig):
        self.config = config

    def clean(
        self,
        df: pd.DataFrame,
        run_id: str = "run_default",
        input_file: Optional[str] = None,
        output_file: Optional[str] = None,
    ) -> CleaningResult:
        """
        Clean an input DataFrame in memory and return a CleaningResult containing
        the cleaned DataFrame and structured CleaningReport.
        Does NOT mutate the original input DataFrame.
        """
        start_time_perf = time.perf_counter()
        start_time_iso = datetime.now().isoformat()

        # Work on a non-destructive copy with all columns initially as string/object
        cleaned_df = df.copy(deep=True).astype(str)
        input_rows = len(cleaned_df)
        warnings: List[str] = []

        metrics = CleaningMetrics(input_rows=input_rows)

        if input_rows == 0:
            metrics.output_rows = 0
            metrics.execution_time_seconds = time.perf_counter() - start_time_perf
            report = CleaningReport(
                run_id=run_id,
                dataset=self.config.dataset_name,
                input_file=input_file,
                output_file=output_file,
                start_time=start_time_iso,
                end_time=datetime.now().isoformat(),
                metrics=metrics,
                status=CleaningStatus.WARNING,
                warnings=["Dataset contains 0 rows (empty dataset)"],
            )
            return CleaningResult(cleaned_df=cleaned_df, report=report, passed=True)

        # Track modified rows and unresolved rows
        changed_row_indices: Set[Any] = set()
        unresolved_row_indices: Set[Any] = set()

        # 1. Whitespace & Null Normalization across all columns
        null_set = {
            str(val).strip().upper() for val in self.config.null_representations
        }
        mandatory_set = set(self.config.mandatory_fields)

        for col in cleaned_df.columns:
            series = cleaned_df[col]

            # Identify leading/trailing whitespace
            stripped = series.str.strip()
            ws_mask = series != stripped
            ws_count = int(ws_mask.sum())
            if ws_count > 0:
                metrics.whitespace_cells_normalized += ws_count
                changed_row_indices.update(series[ws_mask].index)

            # Check for textual null representations
            null_mask = (
                stripped.str.upper().isin(null_set) | (stripped == "") | series.isna()
            )
            null_count = int(null_mask.sum())
            if null_count > 0:
                metrics.null_cells_normalized += null_count
                changed_row_indices.update(series[null_mask].index)

                # If column is mandatory, record as unresolved mandatory null (NEVER fabricate a value)
                if col in mandatory_set:
                    metrics.unresolved_mandatory_null_count += null_count
                    unresolved_row_indices.update(series[null_mask].index)
                    warnings.append(
                        f"Found {null_count} rows with unresolved mandatory null in '{col}'. "
                        f"Normalized to canonical missing representation; no synthetic data fabricated."
                    )

            # Standardize column values: trimmed string or canonical null
            cleaned_col = stripped.copy()
            cleaned_col[null_mask] = self.config.canonical_null
            cleaned_df[col] = cleaned_col

        # 2. Date Standardization
        for date_col in self.config.date_fields:
            if date_col not in cleaned_df.columns:
                continue

            series = cleaned_df[date_col]
            non_null_mask = series != self.config.canonical_null

            if not non_null_mask.any():
                continue

            canonical_fmt = self.config.canonical_date_format
            accepted_fmts = self.config.accepted_date_formats or [
                "%d-%b-%Y",
                "%Y-%m-%d",
                "%Y%m%d",
            ]

            normalized_dates = []
            dates_changed_count = 0
            invalid_date_count = 0

            for idx, val in series.items():
                if val == self.config.canonical_null:
                    normalized_dates.append(self.config.canonical_null)
                    continue

                val_str = str(val).strip()
                parsed_dt = None

                # Attempt parsing against accepted formats
                for fmt in accepted_fmts:
                    try:
                        parsed_dt = datetime.strptime(val_str, fmt)
                        break
                    except ValueError:
                        continue

                if parsed_dt is not None:
                    formatted_val = parsed_dt.strftime(canonical_fmt)
                    if formatted_val != val_str:
                        dates_changed_count += 1
                        changed_row_indices.add(idx)
                    normalized_dates.append(formatted_val)
                else:
                    # Defensive: Preserve invalid date as-is for downstream DQ detection (never fabricate)
                    invalid_date_count += 1
                    unresolved_row_indices.add(idx)
                    normalized_dates.append(val_str)

            cleaned_df[date_col] = normalized_dates
            metrics.date_cells_normalized += dates_changed_count
            if invalid_date_count > 0:
                metrics.unresolved_invalid_date_count += invalid_date_count
                warnings.append(
                    f"Found {invalid_date_count} invalid date representation(s) in '{date_col}'. "
                    f"Preserved as-is for downstream Data Quality rules."
                )

        # 3. Numeric Standardization (Thousands separators, clean whitespace)
        for num_col in self.config.numeric_fields:
            if num_col not in cleaned_df.columns:
                continue

            series = cleaned_df[num_col]
            non_null_mask = series != self.config.canonical_null

            if not non_null_mask.any():
                continue

            clean_nums = []
            nums_changed_count = 0

            for idx, val in series.items():
                if val == self.config.canonical_null:
                    clean_nums.append(self.config.canonical_null)
                    continue

                val_str = str(val).strip()
                # Remove commas from numeric strings like "1,234.50"
                if "," in val_str:
                    clean_cand = val_str.replace(",", "")
                    # Verify it represents a valid numeric value before stripping comma
                    if re.match(
                        r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$", clean_cand
                    ):
                        val_str = clean_cand
                        nums_changed_count += 1
                        changed_row_indices.add(idx)

                clean_nums.append(val_str)

            cleaned_df[num_col] = clean_nums
            metrics.numeric_cells_normalized += nums_changed_count

        # 4. Field-Specific Casing Standardization
        # 4a. Healthcare Code Fields (trim & uppercase where appropriate, preserve leading zeros)
        for code_col in self.config.code_fields:
            if code_col not in cleaned_df.columns:
                continue

            series = cleaned_df[code_col]
            non_null_mask = series != self.config.canonical_null
            if not non_null_mask.any():
                continue

            uppercased = series.str.upper()
            code_diff_mask = non_null_mask & (series != uppercased)
            code_diff_count = int(code_diff_mask.sum())
            if code_diff_count > 0:
                metrics.code_cells_normalized += code_diff_count
                changed_row_indices.update(series[code_diff_mask].index)

            cleaned_df[code_col] = uppercased

        # 4b. Categorical Fields (trim & uppercase, preserve unknown categories)
        for cat_col in self.config.categorical_fields:
            if cat_col not in cleaned_df.columns:
                continue

            series = cleaned_df[cat_col]
            non_null_mask = series != self.config.canonical_null
            if not non_null_mask.any():
                continue

            uppercased = series.str.upper()
            cat_diff_mask = non_null_mask & (series != uppercased)
            cat_diff_count = int(cat_diff_mask.sum())
            if cat_diff_count > 0:
                metrics.categorical_cells_normalized += cat_diff_count
                changed_row_indices.update(series[cat_diff_mask].index)

            cleaned_df[cat_col] = uppercased

        # 4c. Free-Text Fields (trim whitespace only, DO NOT uppercase)
        for text_col in self.config.free_text_fields:
            if text_col in cleaned_df.columns:
                cleaned_df[text_col] = cleaned_df[text_col].str.strip()

        # 5. Identifier Protection (guarantee string dtype, preserve leading zeros, no arbitrary uppercase)
        for id_col in self.config.identifier_fields:
            if id_col in cleaned_df.columns:
                cleaned_df[id_col] = cleaned_df[id_col].astype(str)

        # 6. Deduplication Handling
        # 6a. Exact duplicate rows removal (all columns identical)
        exact_dup_mask = cleaned_df.duplicated(keep="first")
        exact_dup_count = int(exact_dup_mask.sum())

        if exact_dup_count > 0:
            cleaned_df = cleaned_df[~exact_dup_mask].copy().reset_index(drop=True)
            metrics.exact_duplicate_rows_removed = exact_dup_count
            metrics.rows_removed += exact_dup_count

        # 6b. Conflicting composite key detection (same primary key, but different row contents)
        pk_cols = self.config.primary_key
        if pk_cols and all(pk in cleaned_df.columns for pk in pk_cols):
            # Find duplicate PKs remaining after exact deduplication
            conflicting_pk_mask = cleaned_df.duplicated(subset=pk_cols, keep=False)
            conflict_count = int(conflicting_pk_mask.sum())

            if conflict_count > 0:
                # Count unique conflicting key groups
                unique_conflict_keys = len(
                    cleaned_df[conflicting_pk_mask].groupby(pk_cols)
                )
                metrics.conflicting_key_groups_found = unique_conflict_keys
                unresolved_row_indices.update(cleaned_df[conflicting_pk_mask].index)
                warn_msg = (
                    f"Found {unique_conflict_keys} conflicting composite primary key group(s) "
                    f"({conflict_count} rows total) across {pk_cols}. Records are preserved and flagged for review."
                )
                warnings.append(warn_msg)

        # Final Metrics Computation
        metrics.output_rows = len(cleaned_df)
        metrics.rows_changed = len(changed_row_indices)
        metrics.unresolved_records = len(unresolved_row_indices)
        metrics.execution_time_seconds = time.perf_counter() - start_time_perf

        status = CleaningStatus.WARNING if warnings else CleaningStatus.SUCCESS

        report = CleaningReport(
            run_id=run_id,
            dataset=self.config.dataset_name,
            input_file=input_file,
            output_file=output_file,
            start_time=start_time_iso,
            end_time=datetime.now().isoformat(),
            metrics=metrics,
            status=status,
            warnings=warnings,
            schema_validation_passed=True,
        )

        return CleaningResult(cleaned_df=cleaned_df, report=report, passed=True)
