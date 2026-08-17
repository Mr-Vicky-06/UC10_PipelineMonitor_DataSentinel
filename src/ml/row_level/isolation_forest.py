import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

class RowLevelAnomalyDetector:
    def __init__(self, n_estimators=100, max_samples='auto', contamination='auto', random_state=42):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            max_samples=max_samples,
            max_features=1.0,
            contamination=contamination,
            random_state=random_state
        )
        self.threshold = 0.0
        self.is_fitted = False
        
    def fit(self, X_train: pd.DataFrame, X_calib: pd.DataFrame = None, fpr_target: float = 0.05):
        """
        Train the Isolation Forest in an unsupervised manner.
        If X_calib is provided, the threshold is calibrated to achieve a specific FPR 
        on the calibration set (e.g., allow 5% false positives).
        If X_calib is not provided, we use the training data for calibration.
        """
        self.model.fit(X_train)
        
        # Calculate anomaly scores (lower is more anomalous in sklearn, but we invert it 
        # so higher = more anomalous for intuitive scoring)
        # sklearn's score_samples returns negative anomaly scores.
        
        calib_data = X_calib if X_calib is not None else X_train
        scores = -self.model.score_samples(calib_data)
        
        # We want to set a threshold such that only 'fpr_target' fraction of the clean calibration 
        # data is flagged as anomalous.
        self.threshold = np.percentile(scores, 100 * (1 - fpr_target))
        self.is_fitted = True
        
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Returns predictions and scores. 1 for anomaly, 0 for normal.
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predict.")
            
        scores = -self.model.score_samples(X)
        predictions = (scores > self.threshold).astype(int)
        
        # Extract top contributing features (heuristic based on deviation from median)
        # True SHAP for IsolationForest is complex, so we use a simple heuristic
        # for interpretability.
        median_vals = X.median()
        scaled_deviations = np.abs((X - median_vals) / (X.std() + 1e-9))
        
        # For each row, find the feature with the max deviation
        top_features = scaled_deviations.idxmax(axis=1)
        
        results = pd.DataFrame({
            'anomaly_score': scores,
            'prediction': predictions,
            'top_feature': top_features
        }, index=X.index)
        
        return results
        
    def save(self, filepath: str):
        joblib.dump({
            'model': self.model,
            'threshold': self.threshold
        }, filepath)
        
    @classmethod
    def load(cls, filepath: str) -> "RowLevelAnomalyDetector":
        data = joblib.load(filepath)
        instance = cls()
        instance.model = data['model']
        instance.threshold = data['threshold']
        instance.is_fitted = True
        return instance
