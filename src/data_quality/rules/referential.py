"""
Rule Group G: Referential Integrity and Cross-Dataset Validation Quality Rules.
Performs deterministic, structured matching between healthcare datasets (Claims -> Authorization, Claims -> Hospital Mapping).
Strictly NO RAG or semantic similarity for data validation.
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set, Union
import numpy as np
import pandas as pd

from ..models import (
    DataQualityCategory,
    DataQualitySeverity,
    DataQualityStatus,
    ReferentialIntegrityRuleConfig,
    RuleResult,
)
from .base import BaseDataQualityRule
from .date_logic import _parse_dates_vectorized


def _normalize_id_series(series: pd.Series, zfill_len: Optional[int] = 6) -> pd.Series:
    """Normalize identifier strings by stripping, removing float '.0', and optional zfill."""
    s = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    if zfill_len:
        # If it is purely numeric, pad with leading zeros
        numeric_mask = s.str.isdigit()
        s = s.where(~numeric_mask, s.str.zfill(zfill_len))
    return s


class ReferentialIntegrityRule(BaseDataQualityRule):
    """Evaluates cross-dataset foreign key and authorization relationship integrity."""

    def __init__(self, config: ReferentialIntegrityRuleConfig, dataset_name: str):
        super().__init__(
            rule_id=config.id,
            rule_name=config.name,
            category=DataQualityCategory.REFERENTIAL_INTEGRITY,
            dataset=dataset_name,
            severity=config.severity,
            description=config.description,
            enabled=config.enabled,
        )
        self.foreign_key = config.foreign_key
        self.reference_dataset = config.reference_dataset
        self.reference_key = config.reference_key
        self.match_key = config.match_key
        self.reference_match_key = config.reference_match_key or config.match_key
        self.provider_field = config.provider_field
        self.reference_provider_field = config.reference_provider_field
        self.procedure_field = config.procedure_field
        self.reference_procedure_field = config.reference_procedure_field
        self.service_date_field = config.service_date_field
        self.reference_eff_date_field = config.reference_eff_date_field
        self.reference_exp_date_field = config.reference_exp_date_field
        self.reference_status_field = config.reference_status_field
        self.valid_auth_status = config.valid_auth_status or "APPROVED"

    def evaluate(
        self,
        df: pd.DataFrame,
        context: Optional[Dict[str, Any]] = None,
        reference_datasets: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        start_time = time.perf_counter()
        total_rows = len(df)

        if total_rows == 0:
            return self._build_result(
                status=DataQualityStatus.PASS,
                expected=f"Valid references in {self.reference_dataset}",
                actual="0 rows evaluated",
                affected_row_count=0,
                total_rows=0,
                message=f"Dataset is empty; referential rule '{self.rule_name}' passed trivially.",
                fields=[self.foreign_key or self.match_key or ""],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # 1. Resolve reference dataset
        ref_df = self._resolve_reference_df(reference_datasets)
        if ref_df is None:
            return self._build_result(
                status=DataQualityStatus.WARNING,
                expected=f"Reference dataset '{self.reference_dataset}' available",
                actual="Reference dataset missing in context",
                affected_row_count=0,
                total_rows=total_rows,
                message=f"Referential check skipped: reference dataset '{self.reference_dataset}' was not supplied.",
                fields=[self.foreign_key or self.match_key or ""],
                execution_time_seconds=time.perf_counter() - start_time,
                metadata={"missing_reference": True, "reference_dataset": self.reference_dataset},
            )

        # Mode A: Simple foreign key lookup (e.g. claims PRVDR_NUM -> hospital_mapping PRVDR_NUM)
        if self.foreign_key and self.reference_key:
            return self._evaluate_foreign_key_lookup(df, ref_df, total_rows, start_time)

        # Mode B: Complex authorization cross-dataset validation
        return self._evaluate_authorization_integrity(df, ref_df, total_rows, start_time, reference_datasets)

    def _evaluate_foreign_key_lookup(
        self, df: pd.DataFrame, ref_df: pd.DataFrame, total_rows: int, start_time: float
    ) -> RuleResult:
        if self.foreign_key not in df.columns:
            return self._build_result(
                status=DataQualityStatus.FAIL,
                expected=f"Foreign key '{self.foreign_key}' present",
                actual="Field missing from columns",
                affected_row_count=total_rows,
                total_rows=total_rows,
                message=f"Foreign key column '{self.foreign_key}' not found in dataset.",
                fields=[self.foreign_key],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        if self.reference_key not in ref_df.columns:
            return self._build_result(
                status=DataQualityStatus.FAIL,
                expected=f"Reference key '{self.reference_key}' present in {self.reference_dataset}",
                actual="Reference key missing from reference table",
                affected_row_count=total_rows,
                total_rows=total_rows,
                message=f"Reference key '{self.reference_key}' not found in reference dataset '{self.reference_dataset}'.",
                fields=[self.foreign_key],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Normalize keys preserving leading zeros (e.g. PRVDR_NUM '030115')
        source_keys = _normalize_id_series(df[self.foreign_key].dropna(), zfill_len=6)
        ref_keys_raw = _normalize_id_series(ref_df[self.reference_key].dropna(), zfill_len=6)
        ref_keys_set = set(ref_keys_raw)

        # Check membership
        valid_mask = source_keys.isin(ref_keys_set)
        orphan_count = int((~valid_mask).sum())
        orphan_pct = (orphan_count / total_rows) * 100.0

        status = DataQualityStatus.FAIL if orphan_count > 0 else DataQualityStatus.PASS
        if orphan_count > 0:
            message = (
                f"Referential integrity failure: {orphan_count} record(s) ({orphan_pct:.2f}%) in '{self.foreign_key}' "
                f"do not exist in reference dataset '{self.reference_dataset}'."
            )
        else:
            message = (
                f"Referential integrity satisfied: all {len(source_keys):,} foreign keys in '{self.foreign_key}' "
                f"match reference dataset '{self.reference_dataset}'."
            )

        return self._build_result(
            status=status,
            expected=f"All {self.foreign_key} exist in {self.reference_dataset}.{self.reference_key}",
            actual={"orphan_count": orphan_count, "orphan_pct": round(orphan_pct, 4)},
            affected_row_count=orphan_count,
            total_rows=total_rows,
            message=message,
            fields=[self.foreign_key],
            execution_time_seconds=time.perf_counter() - start_time,
            metadata={
                "orphan_count": orphan_count,
                "reference_key_count": len(ref_keys_set),
            },
        )

    def _evaluate_authorization_integrity(
        self,
        claims_df: pd.DataFrame,
        auth_df: pd.DataFrame,
        total_rows: int,
        start_time: float,
        reference_datasets: Optional[Dict[str, Any]],
    ) -> RuleResult:
        """
        Evaluates full deterministic authorization referential integrity against CMS claims.
        Checks for:
          - MISSING (claim has no corresponding authorization)
          - PROVIDER_MISMATCH (PRVDR_NUM != PRF_PHYSN_NPI)
          - PROCEDURE_MISMATCH (HCPCS_CD != HCPCS_CD)
          - EXPIRED (CLM_FROM_DT > AUTH_EXP_DT)
          - NOT_YET_EFFECTIVE (CLM_FROM_DT < AUTH_EFF_DT)
          - INVALID_STATUS (AUTH_STATUS_CD != APPROVED)
        """
        match_k = self.match_key or "BENE_ID"
        ref_match_k = self.reference_match_key or "BENE_ID"

        if match_k not in claims_df.columns or ref_match_k not in auth_df.columns:
            return self._build_result(
                status=DataQualityStatus.FAIL,
                expected=f"Join key '{match_k}' present",
                actual="Join key missing",
                affected_row_count=total_rows,
                total_rows=total_rows,
                message=f"Authorization referential check missing key '{match_k}'.",
                fields=[match_k],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Check if ground truth / scenario link table is provided in reference_datasets
        link_df = None
        if reference_datasets and "ground_truth" in reference_datasets:
            link_df = self._to_dataframe(reference_datasets["ground_truth"])
        elif reference_datasets and "anomaly_ground_truth" in reference_datasets:
            link_df = self._to_dataframe(reference_datasets["anomaly_ground_truth"])

        # Determine claim-level view by selecting only essential columns and dropping duplicate lines
        claim_id_col = "CLM_ID" if "CLM_ID" in claims_df.columns else None
        needed_cols = [c for c in [claim_id_col, match_k, "PRVDR_NUM", "HCPCS_CD", "CLM_FROM_DT", "CLM_THRU_DT"] if c and c in claims_df.columns]
        
        if claim_id_col and len(needed_cols) > 0:
            claims_eval = claims_df[needed_cols].drop_duplicates(subset=[claim_id_col]).copy()
        else:
            claims_eval = claims_df[needed_cols].copy() if needed_cols else claims_df.copy()

        num_eval_claims = len(claims_eval)

        # Prepare normalized join keys and columns
        c_df = claims_eval.copy()
        c_df["_join_bene"] = _normalize_id_series(c_df[match_k], zfill_len=None)

        auth_needed_cols = [c for c in ["AUTH_ID", ref_match_k, "PRF_PHYSN_NPI", "HCPCS_CD", "AUTH_EFF_DT", "AUTH_EXP_DT", "AUTH_STATUS_CD", "AUTH_AMT"] if c in auth_df.columns]
        a_df = auth_df[auth_needed_cols].copy()
        a_df["_join_bene"] = _normalize_id_series(a_df[ref_match_k], zfill_len=None)

        # If link_df is provided, link directly via CLM_ID -> AUTH_ID
        if link_df is not None and "CLM_ID" in link_df.columns and "AUTH_ID" in link_df.columns and claim_id_col and claim_id_col in c_df.columns:
            c_df["_clm_id_str"] = c_df[claim_id_col].astype(str).str.strip()
            link_copy = link_df[["CLM_ID", "AUTH_ID"]].copy()
            link_copy["_clm_id_str"] = link_copy["CLM_ID"].astype(str).str.strip()
            link_copy["_auth_id_str"] = link_copy["AUTH_ID"].astype(str).str.strip()

            c_df = c_df.merge(link_copy[["_clm_id_str", "_auth_id_str"]], on="_clm_id_str", how="left")
            a_df["_auth_id_str"] = a_df["AUTH_ID"].astype(str).str.strip()
            merged = c_df.merge(a_df, on="_auth_id_str", how="left", suffixes=("_claim", "_auth"))
        else:
            # Match directly on BENE_ID (deduplicated by BENE_ID)
            a_dedup = a_df.drop_duplicates(subset=["_join_bene"]).copy()
            merged = c_df.merge(a_dedup, on="_join_bene", how="left", suffixes=("_claim", "_auth"))

        # Resolve column names in merged dataframe
        prov_c = self.provider_field if self.provider_field in merged.columns else ("PRVDR_NUM" if "PRVDR_NUM" in merged.columns else "PRVDR_NUM_claim")
        prov_a = self.reference_provider_field if self.reference_provider_field in merged.columns else ("PRF_PHYSN_NPI" if "PRF_PHYSN_NPI" in merged.columns else "PRF_PHYSN_NPI_auth")

        proc_c = self.procedure_field if self.procedure_field in merged.columns else ("HCPCS_CD" if "HCPCS_CD" in merged.columns else "HCPCS_CD_claim")
        proc_a = self.reference_procedure_field if self.reference_procedure_field in merged.columns else ("HCPCS_CD_auth" if "HCPCS_CD_auth" in merged.columns else "HCPCS_CD")

        dt_claim = self.service_date_field if self.service_date_field in merged.columns else ("CLM_FROM_DT" if "CLM_FROM_DT" in merged.columns else "CLM_FROM_DT_claim")
        dt_eff = self.reference_eff_date_field if self.reference_eff_date_field in merged.columns else ("AUTH_EFF_DT" if "AUTH_EFF_DT" in merged.columns else "AUTH_EFF_DT_auth")
        dt_exp = self.reference_exp_date_field if self.reference_exp_date_field in merged.columns else ("AUTH_EXP_DT" if "AUTH_EXP_DT" in merged.columns else "AUTH_EXP_DT_auth")

        status_a = self.reference_status_field if self.reference_status_field in merged.columns else ("AUTH_STATUS_CD" if "AUTH_STATUS_CD" in merged.columns else "AUTH_STATUS_CD_auth")

        # 1. MISSING
        auth_id_col = "AUTH_ID" if "AUTH_ID" in merged.columns else ("AUTH_ID_auth" if "AUTH_ID_auth" in merged.columns else None)
        if auth_id_col:
            missing_auth_mask = merged[auth_id_col].isna() | merged[auth_id_col].astype(str).str.strip().isin(["", "nan", "NaN", "None"])
        else:
            missing_auth_mask = merged["_join_bene"].isna()

        missing_count = int(missing_auth_mask.sum())

        # For records with authorization present:
        present_mask = ~missing_auth_mask
        present_df = merged[present_mask]

        # 2. PROVIDER MISMATCH
        if prov_c in present_df.columns and prov_a in present_df.columns:
            c_prov = _normalize_id_series(present_df[prov_c], zfill_len=6)
            a_prov = _normalize_id_series(present_df[prov_a], zfill_len=6)
            prov_mismatch_mask = (c_prov != a_prov) & (c_prov != "") & (a_prov != "")
            prov_mismatch_count = int(prov_mismatch_mask.sum())
        else:
            prov_mismatch_count = 0
            prov_mismatch_mask = pd.Series(False, index=present_df.index)

        # 3. PROCEDURE MISMATCH
        if proc_c in present_df.columns and proc_a in present_df.columns:
            c_proc = present_df[proc_c].astype(str).str.strip()
            a_proc = present_df[proc_a].astype(str).str.strip()
            proc_mismatch_mask = (c_proc != a_proc) & (c_proc != "") & (a_proc != "")
            proc_mismatch_count = int(proc_mismatch_mask.sum())
        else:
            proc_mismatch_count = 0
            proc_mismatch_mask = pd.Series(False, index=present_df.index)

        # 4. DATE WINDOW (EXPIRED & NOT_YET_EFFECTIVE)
        expired_count = 0
        not_yet_effective_count = 0
        if dt_claim in present_df.columns and dt_eff in present_df.columns and dt_exp in present_df.columns:
            claim_dts = _parse_dates_vectorized(present_df[dt_claim])
            eff_dts = _parse_dates_vectorized(present_df[dt_eff])
            exp_dts = _parse_dates_vectorized(present_df[dt_exp])

            exp_mask = ~claim_dts.isna() & ~exp_dts.isna() & (claim_dts > exp_dts)
            expired_count = int(exp_mask.sum())

            not_eff_mask = ~claim_dts.isna() & ~eff_dts.isna() & (claim_dts < eff_dts)
            not_yet_effective_count = int(not_eff_mask.sum())
        else:
            exp_mask = pd.Series(False, index=present_df.index)
            not_eff_mask = pd.Series(False, index=present_df.index)

        # 5. INVALID STATUS
        if status_a in present_df.columns:
            auth_st = present_df[status_a].astype(str).str.strip().str.upper()
            inv_status_mask = auth_st != self.valid_auth_status.upper()
            invalid_status_count = int(inv_status_mask.sum())
        else:
            invalid_status_count = 0
            inv_status_mask = pd.Series(False, index=present_df.index)

        # Overall violation calculation
        total_violations = (
            missing_count
            + prov_mismatch_count
            + proc_mismatch_count
            + expired_count
            + not_yet_effective_count
            + invalid_status_count
        )
        total_eval = num_eval_claims
        violation_pct = (total_violations / total_eval * 100.0) if total_eval > 0 else 0.0

        status = DataQualityStatus.FAIL if total_violations > 0 else DataQualityStatus.PASS

        breakdown = {
            "missing_authorization_count": missing_count,
            "provider_mismatch_count": prov_mismatch_count,
            "procedure_mismatch_count": proc_mismatch_count,
            "expired_authorization_count": expired_count,
            "not_yet_effective_count": not_yet_effective_count,
            "invalid_status_count": invalid_status_count,
            "total_violations": total_violations,
            "evaluated_claims": total_eval,
        }

        if total_violations > 0:
            details = []
            if missing_count > 0:
                details.append(f"{missing_count} missing auth")
            if prov_mismatch_count > 0:
                details.append(f"{prov_mismatch_count} provider mismatch")
            if proc_mismatch_count > 0:
                details.append(f"{proc_mismatch_count} procedure mismatch")
            if expired_count > 0:
                details.append(f"{expired_count} expired")
            if not_yet_effective_count > 0:
                details.append(f"{not_yet_effective_count} not yet effective")
            if invalid_status_count > 0:
                details.append(f"{invalid_status_count} invalid status")

            message = f"Authorization referential violations detected: {', '.join(details)} ({violation_pct:.2f}% of claims)."
        else:
            message = f"All {total_eval:,} claims matched valid, active authorizations within effective service dates."

        return self._build_result(
            status=status,
            expected="All claims have valid, active matching authorization within effective date window",
            actual=breakdown,
            affected_row_count=total_violations,
            total_rows=total_eval,
            message=message,
            fields=[match_k, self.provider_field or "PRVDR_NUM", self.procedure_field or "HCPCS_CD"],
            execution_time_seconds=time.perf_counter() - start_time,
            metadata=breakdown,
        )

    def _resolve_reference_df(
        self, reference_datasets: Optional[Dict[str, Any]]
    ) -> Optional[pd.DataFrame]:
        if not reference_datasets:
            return None
        if self.reference_dataset in reference_datasets:
            return self._to_dataframe(reference_datasets[self.reference_dataset])
        return None

    def _to_dataframe(self, val: Any) -> Optional[pd.DataFrame]:
        if val is None:
            return None
        if isinstance(val, pd.DataFrame):
            return val
        if isinstance(val, (str, Path)):
            p = Path(val)
            if p.exists():
                sep = "|" if p.suffix == ".csv" and "claims" in p.name else ","
                return pd.read_csv(p, sep=sep, low_memory=False, dtype=str)
        return None
