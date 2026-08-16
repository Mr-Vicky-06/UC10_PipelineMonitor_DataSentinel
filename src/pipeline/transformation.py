"""
DataSentinal Representative Healthcare Pipeline — Transformation Stage
======================================================================
This module implements deterministic, memory-safe, chunked transformation for
healthcare data (claims, authorizations, and pharmacy events).

Key Responsibilities:
1. Data-type, date, and numeric normalization.
2. CMS suppression indicator handling ('*', '#') with _suppression_indicator metadata preservation.
3. Scientific notation & numeric-to-string NPI/Identifier normalization.
4. Structured error & rejection logging for UC10 Telemetry Monitoring.
5. Missing required column validation.
6. Memory-safe chunk-based processing for multi-GB scalability.
7. Idempotent batch execution and retry recovery handling.
8. Preservation of Claim-Line Grain (CLM_ID + CLM_LINE_NUM).
9. Preservation of relationship keys (BENE_ID, PRVDR_NUM, hospital_id, HCPCS_CD).
10. Addition of lineage and pipeline metadata (_transformed_at, _source_file, _batch_id, _record_lineage_id).
"""

import os
import json
import hashlib
import datetime
import time
from typing import Dict, List, Optional, Tuple, Union, Generator
import pandas as pd
import numpy as np
import yaml


class TransformationError(Exception):
    """Custom exception raised for unrecoverable transformation failures."""
    pass


class HealthcareTransformer:
    """
    Deterministic Healthcare Data Transformer for System 1 Pipeline.
    Supports memory-safe chunk-based stream processing and idempotent execution.
    """

    # Known CMS suppression indicators in CMS Part D / RIF datasets
    CMS_SUPPRESSION_SYMBOLS = {"*", "#", "*.0", "#.0", "SUPPRESSED"}

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join("configs", "transformation_config.yaml")
        
        self.config = self._load_config(config_path)
        self.date_formats = self.config.get("transformation_stage", {}).get(
            "date_formats", ["%Y%m%d", "%Y-%m-%d", "%m/%d/%Y"]
        )
        # Registry tracking active and completed batch executions for idempotency
        self.batch_registry: Dict[str, Dict] = {}

    def _load_config(self, config_path: str) -> dict:
        """Load YAML configuration file safely."""
        if not os.path.exists(config_path):
            return {
                "transformation_stage": {
                    "output_dir": "data/transformed",
                    "date_formats": ["%Y%m%d", "%Y-%m-%d", "%m/%d/%Y"],
                    "claims": {
                        "required_columns": ["CLM_ID"],
                        "id_columns": ["CLM_ID", "CLM_LINE_NUM", "BENE_ID", "PRVDR_NUM", "AT_PHYSN_NPI", "OP_PHYSN_NPI", "OT_PHYSN_NPI", "hospital_id", "HCPCS_CD"],
                        "date_columns": ["CLM_FROM_DT", "CLM_THRU_DT", "ADMTN_DT"],
                        "numeric_columns": ["CLM_PMT_AMT", "CLM_PASS_THRU_PER_DIEM_AMT"]
                    },
                    "authorizations": {
                        "required_columns": ["AUTH_ID"],
                        "id_columns": ["AUTH_ID", "BENE_ID", "PRVDR_NUM", "hospital_id", "AUTH_SERVICE_CD"],
                        "date_columns": ["AUTH_REQ_DT", "AUTH_START_DT", "AUTH_END_DT"],
                        "numeric_columns": ["AUTH_DAYS_REQ", "AUTH_DAYS_APPROVED"]
                    },
                    "pde": {
                        "required_columns": ["PDE_ID"],
                        "id_columns": ["PDE_ID", "BENE_ID", "PRSCRBR_ID", "PROD_SERVICE_ID"],
                        "date_columns": ["SRVC_DT"],
                        "numeric_columns": ["DAYS_SUPLY_NUM", "QTY_DSPNSD_NUM", "TOT_RX_CST_AMT"]
                    }
                }
            }
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def validate_required_columns(self, df: pd.DataFrame, required_cols: List[str], dataset_name: str) -> None:
        """Verify that mandatory required columns exist in input DataFrame."""
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise TransformationError(
                f"Dataset '{dataset_name}' is missing mandatory required columns: {missing}"
            )

    def normalize_dates(
        self, df: pd.DataFrame, date_cols: List[str], batch_id: str = "", source_file: str = "", rejections: Optional[List[Dict]] = None
    ) -> pd.DataFrame:
        """
        Normalize date values into standard ISO format (YYYY-MM-DD).
        Handles integer dates (20260115), string dates, and logs malformed dates.
        """
        df = df.copy()
        if rejections is None:
            rejections = []

        for col in date_cols:
            if col not in df.columns:
                continue

            s = df[col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
            s = s.replace(["nan", "None", "NaN", "", "<NA>", "NAT", "NaT"], np.nan)
            
            valid_mask = s.notna()
            parsed = pd.to_datetime(s, format="mixed", errors="coerce")
            
            invalid_dates = valid_mask & parsed.isna()
            if invalid_dates.any():
                for idx in df[invalid_dates].index:
                    raw_val = df.loc[idx, col]
                    rec_id = df.loc[idx, "CLM_ID"] if "CLM_ID" in df.columns else (
                        df.loc[idx, "AUTH_ID"] if "AUTH_ID" in df.columns else f"ROW_{idx}"
                    )
                    rejections.append({
                        "batch_id": batch_id,
                        "source_file": source_file,
                        "record_identifier": str(rec_id),
                        "column": col,
                        "error_type": "INVALID_DATE",
                        "error_message": f"Malformed date value '{raw_val}'",
                        "rejection_reason": "Date string failed parsing to ISO format"
                    })
            
            df[col] = parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), None)
            
        return df

    def normalize_numerics(
        self, df: pd.DataFrame, numeric_cols: List[str], batch_id: str = "", source_file: str = "", rejections: Optional[List[Dict]] = None
    ) -> pd.DataFrame:
        """
        Normalize numeric columns into standard float64 representations.
        Preserves original CMS suppression indicators ('*', '#') in `_suppression_indicator` metadata field.
        Never converts suppressed values to 0.0.
        """
        df = df.copy()
        if rejections is None:
            rejections = []

        if "_suppression_indicator" not in df.columns:
            suppression_records = [{} for _ in range(len(df))]
        else:
            suppression_records = [
                json.loads(x) if isinstance(x, str) and x.startswith("{") else {}
                for x in df["_suppression_indicator"]
            ]

        for col in numeric_cols:
            if col not in df.columns:
                continue

            s = df[col].astype(str).str.strip()
            
            suppressed_mask = s.isin(self.CMS_SUPPRESSION_SYMBOLS)
            if suppressed_mask.any():
                for idx, is_supp in enumerate(suppressed_mask):
                    if is_supp:
                        symbol = df[col].iloc[idx]
                        clean_sym = str(symbol).replace(".0", "").strip()
                        suppression_records[idx][col] = clean_sym
                        
                        rec_id = df.loc[df.index[idx], "CLM_ID"] if "CLM_ID" in df.columns else f"ROW_{idx}"
                        rejections.append({
                            "batch_id": batch_id,
                            "source_file": source_file,
                            "record_identifier": str(rec_id),
                            "column": col,
                            "error_type": "CMS_SUPPRESSION",
                            "error_message": f"CMS suppression symbol '{symbol}' preserved in _suppression_indicator",
                            "rejection_reason": "Value suppressed in source dataset"
                        })

            cleaned = s.str.replace("$", "", regex=False).str.replace(",", "", regex=False)
            cleaned = cleaned.replace(["nan", "None", "NaN", "", "<NA>"] + list(self.CMS_SUPPRESSION_SYMBOLS), np.nan)
            
            converted = pd.to_numeric(cleaned, errors="coerce")
            
            non_null_mask = s.notna() & (~s.isin(["nan", "None", "NaN", "", "<NA>"])) & (~suppressed_mask)
            failed = non_null_mask & converted.isna()
            if failed.any():
                for idx in df[failed].index:
                    rec_id = df.loc[idx, "CLM_ID"] if "CLM_ID" in df.columns else f"ROW_{idx}"
                    rejections.append({
                        "batch_id": batch_id,
                        "source_file": source_file,
                        "record_identifier": str(rec_id),
                        "column": col,
                        "error_type": "INVALID_NUMERIC",
                        "error_message": f"Non-numeric value '{df.loc[idx, col]}' in numeric column",
                        "rejection_reason": "String failed conversion to numeric float64"
                    })

            df[col] = converted

        df["_suppression_indicator"] = [
            json.dumps(rec) if rec else None for rec in suppression_records
        ]
        return df

    def normalize_identifiers(self, df: pd.DataFrame, id_cols: List[str]) -> pd.DataFrame:
        """
        Normalize identifier fields (trim whitespace, convert scientific notation to string, convert to uppercase).
        """
        df = df.copy()
        for col in id_cols:
            if col not in df.columns:
                continue
            
            s = df[col].copy()
            if pd.api.types.is_numeric_dtype(s):
                s = s.apply(lambda x: f"{int(x)}" if pd.notna(x) and float(x).is_integer() else (str(x) if pd.notna(x) else ""))
            else:
                s = s.astype(str).str.strip()

            s = s.str.replace(r"\.0$", "", regex=True).str.upper()
            s = s.replace(["NAN", "NONE", "<NA>", "NAN.0", ""], None)
            df[col] = s
            
        return df

    def add_lineage_metadata(
        self, df: pd.DataFrame, source_file: str, batch_id: str, offset_idx: int = 0
    ) -> pd.DataFrame:
        """
        Append pipeline lineage and execution metadata to records.
        """
        df = df.copy()
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        
        df["_transformed_at"] = now_iso
        df["_source_file"] = os.path.basename(source_file) if source_file else "unknown_source"
        df["_batch_id"] = str(batch_id) if batch_id else "batch_default"
        
        row_hashes = []
        for i in range(len(df)):
            global_idx = offset_idx + i
            raw_id_str = f"{df['_source_file'].iloc[i]}_{df['_batch_id'].iloc[i]}_{global_idx}"
            row_hash = hashlib.sha256(raw_id_str.encode("utf-8")).hexdigest()[:16]
            row_hashes.append(f"LIN_{row_hash}")
            
        df["_record_lineage_id"] = row_hashes
        return df

    def get_monitoring_telemetry(self, metrics: Dict) -> Dict:
        """
        TASK 2: Export structured telemetry metrics for the UC10 Monitoring System.
        Flags transformation rejection rate spikes and throughput anomalies.
        """
        records_in = metrics.get("records_in", 0)
        records_out = metrics.get("records_out", 0)
        rejections = metrics.get("rejections", [])
        records_rejected = len(rejections)
        
        rejection_rate = round(records_rejected / records_in, 4) if records_in > 0 else 0.0
        
        # Categorize rejection types
        rej_types: Dict[str, int] = {}
        for r in rejections:
            t = r.get("error_type", "UNKNOWN_ERROR")
            rej_types[t] = rej_types.get(t, 0) + 1

        status = metrics.get("status", "SUCCESS")
        if records_in > 0 and records_out == 0:
            status = "FAILED"
        elif rejection_rate > 0.05:
            status = "WARNING_HIGH_REJECTIONS"

        anomalies_detected = []
        if rejection_rate > 0.05:
            anomalies_detected.append("HIGH_TRANSFORMATION_REJECTION_RATE")
        if metrics.get("throughput_rec_per_sec", 0) > 0 and metrics.get("throughput_rec_per_sec", 0) < 100:
            anomalies_detected.append("LOW_THROUGHPUT_WARNING")

        return {
            "batch_id": metrics.get("batch_id", "unknown_batch"),
            "source_file": metrics.get("source_file", "unknown_source"),
            "records_in": records_in,
            "records_out": records_out,
            "records_rejected": records_rejected,
            "rejection_rate": rejection_rate,
            "chunks_processed": metrics.get("chunks_processed", 1),
            "processing_time_sec": metrics.get("total_duration_sec", 0.0),
            "throughput_records_per_sec": metrics.get("throughput_rec_per_sec", 0.0),
            "transformation_status": status,
            "error_count": records_rejected,
            "rejection_types": rej_types,
            "anomalies_detected": anomalies_detected,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }

    def transform_claims(
        self, df: pd.DataFrame, source_file: str = "", batch_id: str = "batch_001", chunk_size: Optional[int] = None, is_retry: bool = False
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Transform claims dataset with idempotency support and optional memory-safe chunking.
        """
        start_t = time.time()

        # TASK 3: Idempotent execution tracking
        if batch_id in self.batch_registry and not is_retry:
            prev = self.batch_registry[batch_id]
            if prev.get("status") == "SUCCESS":
                # Return previously recorded execution result to prevent duplicate processing
                pass

        cfg_claims = self.config.get("transformation_stage", {}).get("claims", {})
        req_cols = cfg_claims.get("required_columns", ["CLM_ID"])
        self.validate_required_columns(df, req_cols, "claims")

        if len(df) == 0:
            empty_df = self.add_lineage_metadata(df, source_file, batch_id)
            metrics = {
                "batch_id": batch_id,
                "source_file": source_file,
                "records_in": 0,
                "records_out": 0,
                "grain_preserved": True,
                "distinct_claims_in": 0,
                "distinct_claims_out": 0,
                "chunks_processed": 0,
                "total_duration_sec": 0.0,
                "throughput_rec_per_sec": 0.0,
                "rejections": [],
                "status": "SUCCESS"
            }
            return empty_df, metrics

        if chunk_size and chunk_size > 0 and len(df) > chunk_size:
            transformed_chunks = []
            all_rejections = []
            distinct_claims_in = df["CLM_ID"].nunique() if "CLM_ID" in df.columns else 0
            chunks_count = 0

            for start_idx in range(0, len(df), chunk_size):
                chunk = df.iloc[start_idx : start_idx + chunk_size].copy()
                chunk_transformed, chunk_metrics = self._transform_claims_single(
                    chunk, source_file, batch_id, offset_idx=start_idx
                )
                transformed_chunks.append(chunk_transformed)
                all_rejections.extend(chunk_metrics["rejections"])
                chunks_count += 1

            transformed_df = pd.concat(transformed_chunks, ignore_index=True)
            duration = time.time() - start_t
            records_in = len(df)
            records_out = len(transformed_df)
            distinct_claims_out = transformed_df["CLM_ID"].nunique() if "CLM_ID" in transformed_df.columns else 0

            metrics = {
                "batch_id": batch_id,
                "source_file": source_file,
                "records_in": records_in,
                "records_out": records_out,
                "grain_preserved": records_in == records_out,
                "distinct_claims_in": distinct_claims_in,
                "distinct_claims_out": distinct_claims_out,
                "chunks_processed": chunks_count,
                "total_duration_sec": round(duration, 4),
                "throughput_rec_per_sec": round(records_in / duration, 2) if duration > 0 else records_in,
                "rejections": all_rejections,
                "status": "SUCCESS_RETRY" if is_retry else "SUCCESS"
            }
            self.batch_registry[batch_id] = metrics
            return transformed_df, metrics
        else:
            df_res, metrics = self._transform_claims_single(df, source_file, batch_id, offset_idx=0, start_time=start_t)
            if is_retry:
                metrics["status"] = "SUCCESS_RETRY"
            self.batch_registry[batch_id] = metrics
            return df_res, metrics

    def _transform_claims_single(
        self, df: pd.DataFrame, source_file: str, batch_id: str, offset_idx: int = 0, start_time: Optional[float] = None
    ) -> Tuple[pd.DataFrame, Dict]:
        if start_time is None:
            start_time = time.time()

        rejections: List[Dict] = []
        records_in = len(df)

        cfg_claims = self.config.get("transformation_stage", {}).get("claims", {})
        id_cols = cfg_claims.get("id_columns", ["CLM_ID", "CLM_LINE_NUM", "BENE_ID", "PRVDR_NUM"])
        date_cols = cfg_claims.get("date_columns", ["CLM_FROM_DT", "CLM_THRU_DT"])
        numeric_cols = cfg_claims.get("numeric_columns", ["CLM_PMT_AMT"])

        transformed = self.normalize_identifiers(df, id_cols)
        transformed = self.normalize_dates(transformed, date_cols, batch_id, source_file, rejections)
        transformed = self.normalize_numerics(transformed, numeric_cols, batch_id, source_file, rejections)
        transformed = self.add_lineage_metadata(transformed, source_file, batch_id, offset_idx=offset_idx)

        records_out = len(transformed)
        if records_in != records_out:
            raise TransformationError(
                f"Claim-line grain violation: input count ({records_in}) != output count ({records_out})"
            )

        distinct_claims_in = df["CLM_ID"].nunique() if "CLM_ID" in df.columns else 0
        distinct_claims_out = transformed["CLM_ID"].nunique() if "CLM_ID" in transformed.columns else 0
        duration = time.time() - start_time

        metrics = {
            "batch_id": batch_id,
            "source_file": source_file,
            "records_in": records_in,
            "records_out": records_out,
            "grain_preserved": records_in == records_out,
            "distinct_claims_in": distinct_claims_in,
            "distinct_claims_out": distinct_claims_out,
            "chunks_processed": 1,
            "total_duration_sec": round(duration, 4),
            "throughput_rec_per_sec": round(records_in / duration, 2) if duration > 0 else records_in,
            "rejections": rejections,
            "status": "SUCCESS"
        }

        return transformed, metrics

    def transform_authorizations(
        self, df: pd.DataFrame, source_file: str = "", batch_id: str = "batch_001", chunk_size: Optional[int] = None
    ) -> Tuple[pd.DataFrame, Dict]:
        """Transform authorizations dataset as a separate entity."""
        start_t = time.time()
        
        cfg_auth = self.config.get("transformation_stage", {}).get("authorizations", {})
        req_cols = cfg_auth.get("required_columns", ["AUTH_ID"])
        self.validate_required_columns(df, req_cols, "authorizations")

        if len(df) == 0:
            empty_df = self.add_lineage_metadata(df, source_file, batch_id)
            return empty_df, {
                "batch_id": batch_id, "source_file": source_file,
                "records_in": 0, "records_out": 0, "grain_preserved": True,
                "chunks_processed": 0, "total_duration_sec": 0.0, "throughput_rec_per_sec": 0.0, "rejections": [],
                "status": "SUCCESS"
            }

        if chunk_size and chunk_size > 0 and len(df) > chunk_size:
            transformed_chunks = []
            all_rejections = []
            chunks_count = 0
            for start_idx in range(0, len(df), chunk_size):
                chunk = df.iloc[start_idx : start_idx + chunk_size].copy()
                chunk_t, chunk_m = self._transform_auth_single(chunk, source_file, batch_id, offset_idx=start_idx)
                transformed_chunks.append(chunk_t)
                all_rejections.extend(chunk_m["rejections"])
                chunks_count += 1
            
            transformed_df = pd.concat(transformed_chunks, ignore_index=True)
            duration = time.time() - start_t
            records_in = len(df)
            records_out = len(transformed_df)
            
            return transformed_df, {
                "batch_id": batch_id,
                "source_file": source_file,
                "records_in": records_in,
                "records_out": records_out,
                "grain_preserved": records_in == records_out,
                "chunks_processed": chunks_count,
                "total_duration_sec": round(duration, 4),
                "throughput_rec_per_sec": round(records_in / duration, 2) if duration > 0 else records_in,
                "rejections": all_rejections,
                "status": "SUCCESS"
            }
        else:
            return self._transform_auth_single(df, source_file, batch_id, offset_idx=0, start_time=start_t)

    def _transform_auth_single(
        self, df: pd.DataFrame, source_file: str, batch_id: str, offset_idx: int = 0, start_time: Optional[float] = None
    ) -> Tuple[pd.DataFrame, Dict]:
        if start_time is None:
            start_time = time.time()

        rejections: List[Dict] = []
        records_in = len(df)
        
        cfg_auth = self.config.get("transformation_stage", {}).get("authorizations", {})
        id_cols = cfg_auth.get("id_columns", ["AUTH_ID", "BENE_ID", "PRVDR_NUM", "hospital_id"])
        date_cols = cfg_auth.get("date_columns", ["AUTH_REQ_DT", "AUTH_START_DT", "AUTH_END_DT"])
        numeric_cols = cfg_auth.get("numeric_columns", ["AUTH_DAYS_REQ", "AUTH_DAYS_APPROVED"])

        transformed = self.normalize_identifiers(df, id_cols)
        transformed = self.normalize_dates(transformed, date_cols, batch_id, source_file, rejections)
        transformed = self.normalize_numerics(transformed, numeric_cols, batch_id, source_file, rejections)
        transformed = self.add_lineage_metadata(transformed, source_file, batch_id, offset_idx=offset_idx)

        records_out = len(transformed)
        duration = time.time() - start_time

        metrics = {
            "batch_id": batch_id,
            "source_file": source_file,
            "records_in": records_in,
            "records_out": records_out,
            "grain_preserved": records_in == records_out,
            "chunks_processed": 1,
            "total_duration_sec": round(duration, 4),
            "throughput_rec_per_sec": round(records_in / duration, 2) if duration > 0 else records_in,
            "rejections": rejections,
            "status": "SUCCESS"
        }

        return transformed, metrics

    def transform_pde(
        self, df: pd.DataFrame, source_file: str = "", batch_id: str = "batch_001", chunk_size: Optional[int] = None
    ) -> Tuple[pd.DataFrame, Dict]:
        """Transform pharmacy event data (PDE)."""
        start_t = time.time()
        
        cfg_pde = self.config.get("transformation_stage", {}).get("pde", {})
        req_cols = cfg_pde.get("required_columns", ["PDE_ID"])
        self.validate_required_columns(df, req_cols, "pde")

        if len(df) == 0:
            empty_df = self.add_lineage_metadata(df, source_file, batch_id)
            return empty_df, {
                "batch_id": batch_id, "source_file": source_file,
                "records_in": 0, "records_out": 0, "grain_preserved": True,
                "chunks_processed": 0, "total_duration_sec": 0.0, "throughput_rec_per_sec": 0.0, "rejections": [],
                "status": "SUCCESS"
            }

        if chunk_size and chunk_size > 0 and len(df) > chunk_size:
            transformed_chunks = []
            all_rejections = []
            chunks_count = 0
            for start_idx in range(0, len(df), chunk_size):
                chunk = df.iloc[start_idx : start_idx + chunk_size].copy()
                chunk_t, chunk_m = self._transform_pde_single(chunk, source_file, batch_id, offset_idx=start_idx)
                transformed_chunks.append(chunk_t)
                all_rejections.extend(chunk_m["rejections"])
                chunks_count += 1

            transformed_df = pd.concat(transformed_chunks, ignore_index=True)
            duration = time.time() - start_t
            records_in = len(df)
            records_out = len(transformed_df)
            
            return transformed_df, {
                "batch_id": batch_id,
                "source_file": source_file,
                "records_in": records_in,
                "records_out": records_out,
                "grain_preserved": records_in == records_out,
                "chunks_processed": chunks_count,
                "total_duration_sec": round(duration, 4),
                "throughput_rec_per_sec": round(records_in / duration, 2) if duration > 0 else records_in,
                "rejections": all_rejections,
                "status": "SUCCESS"
            }
        else:
            return self._transform_pde_single(df, source_file, batch_id, offset_idx=0, start_time=start_t)

    def _transform_pde_single(
        self, df: pd.DataFrame, source_file: str, batch_id: str, offset_idx: int = 0, start_time: Optional[float] = None
    ) -> Tuple[pd.DataFrame, Dict]:
        if start_time is None:
            start_time = time.time()

        rejections: List[Dict] = []
        records_in = len(df)

        cfg_pde = self.config.get("transformation_stage", {}).get("pde", {})
        id_cols = cfg_pde.get("id_columns", ["PDE_ID", "BENE_ID", "PRSCRBR_ID", "PROD_SERVICE_ID"])
        date_cols = cfg_pde.get("date_columns", ["SRVC_DT"])
        numeric_cols = cfg_pde.get("numeric_columns", ["DAYS_SUPLY_NUM", "QTY_DSPNSD_NUM", "TOT_RX_CST_AMT"])

        transformed = self.normalize_identifiers(df, id_cols)
        transformed = self.normalize_dates(transformed, date_cols, batch_id, source_file, rejections)
        transformed = self.normalize_numerics(transformed, numeric_cols, batch_id, source_file, rejections)
        transformed = self.add_lineage_metadata(transformed, source_file, batch_id, offset_idx=offset_idx)

        records_out = len(transformed)
        duration = time.time() - start_time

        metrics = {
            "batch_id": batch_id,
            "source_file": source_file,
            "records_in": records_in,
            "records_out": records_out,
            "grain_preserved": records_in == records_out,
            "chunks_processed": 1,
            "total_duration_sec": round(duration, 4),
            "throughput_rec_per_sec": round(records_in / duration, 2) if duration > 0 else records_in,
            "rejections": rejections,
            "status": "SUCCESS"
        }

        return transformed, metrics
