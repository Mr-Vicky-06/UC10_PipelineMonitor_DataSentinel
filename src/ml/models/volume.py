import pandas as pd
import numpy as np
from src.ml.models.base import BaseModel

class VolumeMADModel(BaseModel):
    """Rolling Median Absolute Deviation (MAD) for Volume."""
    
    def fit(self, df_train: pd.DataFrame) -> None:
        self.medians = {}
        self.mads = {}
        
        for col in self.feature_columns:
            vals = df_train[col].dropna().values
            if len(vals) == 0:
                continue
            median = np.median(vals)
            mad = np.median(np.abs(vals - median))
            if mad == 0:
                mad = 1.0 # Prevent division by zero
            self.medians[col] = median
            self.mads[col] = mad
            
        self.threshold = self.hyperparameters.get('threshold', 3.0)
        self.is_trained = True

    def predict(self, df_test: pd.DataFrame) -> pd.DataFrame:
        df_out = df_test.copy()
        
        is_anomaly = np.zeros(len(df_out), dtype=bool)
        scores = np.zeros(len(df_out))
        
        for col in self.feature_columns:
            if col not in self.medians:
                continue
            
            vals = df_out[col].fillna(self.medians[col]).values
            z_scores = np.abs(vals - self.medians[col]) / self.mads[col]
            
            is_anomaly = is_anomaly | (z_scores > self.threshold)
            scores = np.maximum(scores, z_scores)
            
        df_out['is_anomaly'] = is_anomaly
        df_out['anomaly_score'] = scores
        df_out['expected_value'] = self.medians.get(self.feature_columns[0], 0)
        df_out['baseline_value'] = self.medians.get(self.feature_columns[0], 0)
        return df_out

class VolumeEWMAModel(BaseModel):
    """Exponentially Weighted Moving Average (EWMA) for Volume."""
    
    def fit(self, df_train: pd.DataFrame) -> None:
        self.means = {}
        self.stds = {}
        
        alpha = self.hyperparameters.get('alpha', 0.2)
        
        for col in self.feature_columns:
            vals = df_train[col].dropna()
            if len(vals) == 0:
                continue
            ewma = vals.ewm(alpha=alpha).mean().iloc[-1]
            ewmstd = vals.ewm(alpha=alpha).std().iloc[-1]
            
            if pd.isna(ewmstd) or ewmstd == 0:
                ewmstd = 1.0
                
            self.means[col] = ewma
            self.stds[col] = ewmstd
            
        self.threshold = self.hyperparameters.get('threshold', 3.0)
        self.is_trained = True

    def predict(self, df_test: pd.DataFrame) -> pd.DataFrame:
        df_out = df_test.copy()
        is_anomaly = np.zeros(len(df_out), dtype=bool)
        scores = np.zeros(len(df_out))
        
        for col in self.feature_columns:
            if col not in self.means:
                continue
            
            vals = df_out[col].fillna(self.means[col]).values
            z_scores = np.abs(vals - self.means[col]) / self.stds[col]
            
            is_anomaly = is_anomaly | (z_scores > self.threshold)
            scores = np.maximum(scores, z_scores)
            
        df_out['is_anomaly'] = is_anomaly
        df_out['anomaly_score'] = scores
        return df_out

class VolumeCUSUMModel(BaseModel):
    """Cumulative Sum (CUSUM) for Volume."""
    
    def fit(self, df_train: pd.DataFrame) -> None:
        self.means = {}
        self.stds = {}
        for col in self.feature_columns:
            vals = df_train[col].dropna().values
            if len(vals) == 0:
                continue
            self.means[col] = np.mean(vals)
            self.stds[col] = np.std(vals) if np.std(vals) > 0 else 1.0
            
        self.threshold = self.hyperparameters.get('threshold', 5.0)
        self.drift = self.hyperparameters.get('drift', 0.5)
        self.is_trained = True

    def predict(self, df_test: pd.DataFrame) -> pd.DataFrame:
        df_out = df_test.copy()
        if not self.is_trained:
            df_out['is_anomaly'] = False
            df_out['anomaly_score'] = 0.0
            return df_out
            
        is_anomaly = np.zeros(len(df_out), dtype=bool)
        scores = np.zeros(len(df_out))
        
        for col in self.feature_columns:
            if col not in self.means:
                continue
                
            vals = df_out[col].fillna(self.means[col]).values
            pos_cusum = 0
            neg_cusum = 0
            
            col_anom = np.zeros(len(vals), dtype=bool)
            col_score = np.zeros(len(vals))
            
            for i, v in enumerate(vals):
                z = (v - self.means[col]) / self.stds[col]
                pos_cusum = max(0, pos_cusum + z - self.drift)
                neg_cusum = min(0, neg_cusum + z + self.drift)
                
                s = max(pos_cusum, abs(neg_cusum))
                col_score[i] = s
                if s > self.threshold:
                    col_anom[i] = True
                    # Reset after anomaly
                    pos_cusum = 0
                    neg_cusum = 0
                    
            is_anomaly = is_anomaly | col_anom
            scores = np.maximum(scores, col_score)
            
        df_out['is_anomaly'] = is_anomaly
        df_out['anomaly_score'] = scores
        return df_out
