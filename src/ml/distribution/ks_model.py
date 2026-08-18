import duckdb
import json
import uuid
import numpy as np
from scipy.stats import ks_2samp
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from src.monitoring.models import AnomalyEvent

class KSDistributionDetector:
    """
    Kolmogorov-Smirnov (KS) Distribution Anomaly Detector (Phase 4.5 Prototype)
    
    This detector compares the claim amount distribution of a current batch against
    the historical claim amount distribution for the same hospital.
    """
    
    def __init__(self, db_path: str = "outputs/pipeline_workspace/processed_claims.duckdb", p_value_threshold: float = 0.05, min_sample_size: int = 30):
        self.db_path = db_path
        self.p_value_threshold = p_value_threshold
        self.min_sample_size = min_sample_size
        self.feature_name = "CLM_PMT_AMT"
        self.model_name = "KSDistributionDetector"
        self.model_version = "1.0_prototype"

    def _fetch_samples(self, hospital_id: str, batch_id: Optional[str] = None) -> np.ndarray:
        """
        Fetches CLM_PMT_AMT samples from duckdb for a specific hospital.
        If batch_id is provided, fetches only for that batch. 
        If batch_id is None, fetches historical data (all batches).
        In a true production setting, historical data would exclude the current batch.
        """
        try:
            conn = duckdb.connect(self.db_path)
            
            query = f"""
                SELECT CAST(json_extract_string(transformed_data, '$.{self.feature_name}') AS DOUBLE) as val
                FROM processed_claims
                WHERE hospital_id = ? 
            """
            params = [hospital_id]
            
            if batch_id:
                query += " AND batch_id = ?"
                params.append(batch_id)
                
            query += f" AND json_extract_string(transformed_data, '$.{self.feature_name}') IS NOT NULL"
            
            results = conn.execute(query, params).fetchall()
            conn.close()
            
            # Filter out None and return as numpy array
            return np.array([r[0] for r in results if r[0] is not None])
        except Exception as e:
            print(f"Error fetching samples for {hospital_id}, batch {batch_id}: {e}")
            return np.array([])

    def detect_batch(self, run_id: str, hospital_id: str, current_batch_id: str, reference_samples: np.ndarray = None, current_samples: np.ndarray = None) -> List[AnomalyEvent]:
        """
        Run the KS test between a reference distribution and the current batch distribution.
        If reference_samples or current_samples are not provided, it will attempt to fetch them from duckdb.
        """
        events = []
        
        # 1. Acquire Data
        if current_samples is None:
            current_samples = self._fetch_samples(hospital_id, current_batch_id)
            
        if reference_samples is None:
            # Fetch all historical data for the hospital.
            # Realistically, we fetch everything for the hospital except the current batch.
            try:
                conn = duckdb.connect(self.db_path)
                query = f"""
                    SELECT CAST(json_extract_string(transformed_data, '$.{self.feature_name}') AS DOUBLE) as val
                    FROM processed_claims
                    WHERE hospital_id = ? AND batch_id != ?
                    AND json_extract_string(transformed_data, '$.{self.feature_name}') IS NOT NULL
                """
                results = conn.execute(query, [hospital_id, current_batch_id]).fetchall()
                conn.close()
                reference_samples = np.array([r[0] for r in results if r[0] is not None])
            except Exception:
                reference_samples = np.array([])
        
        # If still none or invalid, we can't test
        if reference_samples is None or len(reference_samples) < self.min_sample_size:
            return events # INSUFFICIENT DATA
            
        if current_samples is None or len(current_samples) < self.min_sample_size:
            return events # INSUFFICIENT DATA
            
        # 2. Perform KS Test
        ks_stat, p_value = ks_2samp(reference_samples, current_samples)
        
        # 3. Decision
        if p_value < self.p_value_threshold:
            # Anomaly detected
            ref_mean = float(np.mean(reference_samples))
            curr_mean = float(np.mean(current_samples))
            
            evidence = {
                "description": f"Significant distribution shift detected in {self.feature_name} using KS Test.",
                "ks_statistic": float(ks_stat),
                "p_value": float(p_value),
                "reference_sample_size": len(reference_samples),
                "current_sample_size": len(current_samples),
                "reference_mean": ref_mean,
                "current_mean": curr_mean,
                "threshold": self.p_value_threshold
            }
            
            event = AnomalyEvent(
                run_id=run_id,
                hospital_id=hospital_id,
                batch_id=current_batch_id,
                stage="DISTRIBUTION_DETECTION",
                feature_name=self.feature_name,
                detector="DISTRIBUTION",
                model_name=self.model_name,
                model_version=self.model_version,
                anomaly_type="DISTRIBUTION_SHIFT",
                observed_value=curr_mean,
                expected_value=ref_mean,
                baseline_value=ref_mean,
                anomaly_score=float(ks_stat),
                confidence_score=float(1.0 - p_value),
                severity="HIGH" if p_value < (self.p_value_threshold / 10) else "MEDIUM",
                evidence=evidence
            )
            events.append(event)
            
        return events
