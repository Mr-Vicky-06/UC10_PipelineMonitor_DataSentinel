import pandas as pd
import json
import joblib
import os
from datetime import datetime
from typing import List, Dict, Any

from src.monitoring.models import AnomalyEvent
from src.monitoring.metrics_repository import MetricsRepository

class MLDetectionEngine:
    """
    Production Inference Engine for AI/ML anomaly detection.
    Loads models from the registry and evaluates incoming pipeline telemetry batches.
    """
    
    def __init__(self, registry_path: str = "outputs/ml/registry/model_registry.json"):
        self.registry_path = registry_path
        self.models = {}
        self.domain_features = {}
        self.metrics_repo = MetricsRepository()
        self._load_models()
        
    def _load_models(self):
        """Loads PROMOTED models from the registry."""
        if not os.path.exists(self.registry_path):
            raise FileNotFoundError(f"Model registry not found at {self.registry_path}")
            
        with open(self.registry_path, "r") as f:
            registry = json.load(f)
            
        for entry in registry:
            if entry.get("status") == "PROMOTED_FOR_INFERENCE":
                domain = entry["domain"]
                model_path = entry["path"]
                features = entry["features"]
                
                if not os.path.exists(model_path):
                    print(f"Warning: Model file {model_path} missing for domain {domain}.")
                    continue
                    
                model = joblib.load(model_path)
                self.models[domain] = model
                self.domain_features[domain] = features
                print(f"Loaded {domain} model from {model_path}")
                
    def detect_anomalies(self, df_batch: pd.DataFrame) -> List[AnomalyEvent]:
        """
        Run inference on a batch of telemetry data.
        Returns a list of AnomalyEvent objects for any detected anomalies.
        """
        events = []
        if df_batch.empty:
            return events
            
        for domain, model in self.models.items():
            # Get features needed for this domain
            features = self.domain_features[domain]
            
            # Predict
            df_pred = model.predict(df_batch)
            
            # Extract anomalies
            anomalous_rows = df_pred[df_pred['is_anomaly'] == True]
            
            for _, row in anomalous_rows.iterrows():
                # Get the most anomalous feature's value and expected value
                # We simplify here by just taking the first feature's values if present,
                # or just generic values if not easily extracting from model.
                # In a robust implementation, the model would return feature contributions.
                
                # We will pick the feature that deviated the most if possible.
                feature_name = features[0]
                feature_value = float(row.get(feature_name, 0.0))
                
                expected = float(row.get('expected_value', 0.0))
                
                event = AnomalyEvent(
                    run_id="ML-INFERENCE-RUN",
                    hospital_id=str(row.get('hospital_id', 'UNKNOWN')),
                    batch_id=str(row.get('batch_id', 'UNKNOWN')),
                    stage="ML_INFERENCE",
                    feature_name=feature_name,
                    detector=domain,
                    model_name=model.__class__.__name__,
                    model_version="1.0",
                    anomaly_type=domain,
                    observed_value=feature_value,
                    expected_value=expected,
                    baseline_value=expected,
                    anomaly_score=float(row.get('anomaly_score', 0.0)),
                    confidence_score=1.0,
                    severity="HIGH",
                    evidence={"description": f"{domain} anomaly detected by {model.__class__.__name__}. Score: {row.get('anomaly_score', 0.0):.4f}"}
                )
                events.append(event)
                
        return events
        
    def evaluate_and_store(self, df_batch: pd.DataFrame):
        """Run inference and store results in the metrics repository."""
        anomalies = self.detect_anomalies(df_batch)
        if anomalies:
            self.metrics_repo.save_anomalies(anomalies)
        return anomalies
