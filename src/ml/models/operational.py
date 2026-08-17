import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from src.ml.models.base import BaseModel

class OperationalIsolationForest(BaseModel):
    """Isolation Forest for Operational metrics."""
    
    def fit(self, df_train: pd.DataFrame) -> None:
        contamination = self.hyperparameters.get('contamination', 0.05)
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        
        # We need to impute or dropna for training. We will impute with mean.
        self.means = df_train[self.feature_columns].mean().to_dict()
        X_train = df_train[self.feature_columns].fillna(self.means).values
        
        if len(X_train) > 0:
            self.model.fit(X_train)
            self.is_trained = True

    def predict(self, df_test: pd.DataFrame) -> pd.DataFrame:
        df_out = df_test.copy()
        if not self.is_trained:
            df_out['is_anomaly'] = False
            df_out['anomaly_score'] = 0.0
            return df_out
            
        X_test = df_test[self.feature_columns].fillna(self.means).values
        if len(X_test) == 0:
            df_out['is_anomaly'] = False
            df_out['anomaly_score'] = 0.0
            return df_out
            
        preds = self.model.predict(X_test)
        # IsolationForest returns -1 for anomaly, 1 for normal
        is_anomaly = preds == -1
        
        # score_samples returns opposite of anomaly score (smaller/negative means more anomalous)
        # We negate it so higher = more anomalous
        scores = -self.model.score_samples(X_test)
        
        df_out['is_anomaly'] = is_anomaly
        df_out['anomaly_score'] = scores
        return df_out


class OperationalLOF(BaseModel):
    """Local Outlier Factor (LOF) for Operational metrics."""
    
    def fit(self, df_train: pd.DataFrame) -> None:
        contamination = self.hyperparameters.get('contamination', 0.05)
        n_neighbors = self.hyperparameters.get('n_neighbors', 20)
        # For LOF to predict on new data, novelty=True is required
        self.model = LocalOutlierFactor(
            n_neighbors=min(n_neighbors, len(df_train)-1) if len(df_train) > 1 else 1,
            contamination=contamination,
            novelty=True
        )
        
        self.means = df_train[self.feature_columns].mean().to_dict()
        X_train = df_train[self.feature_columns].fillna(self.means).values
        
        if len(X_train) > 1:
            self.model.fit(X_train)
            self.is_trained = True

    def predict(self, df_test: pd.DataFrame) -> pd.DataFrame:
        df_out = df_test.copy()
        if not self.is_trained:
            df_out['is_anomaly'] = False
            df_out['anomaly_score'] = 0.0
            return df_out
            
        X_test = df_test[self.feature_columns].fillna(self.means).values
        if len(X_test) == 0:
            df_out['is_anomaly'] = False
            df_out['anomaly_score'] = 0.0
            return df_out
            
        preds = self.model.predict(X_test)
        is_anomaly = preds == -1
        
        scores = -self.model.score_samples(X_test)
        
        df_out['is_anomaly'] = is_anomaly
        df_out['anomaly_score'] = scores
        return df_out


class OperationalOneClassSVM(BaseModel):
    """One-Class SVM for Operational metrics."""
    
    def fit(self, df_train: pd.DataFrame) -> None:
        nu = self.hyperparameters.get('nu', 0.05) # Upper bound on fraction of margin errors
        self.model = OneClassSVM(nu=nu, kernel="rbf", gamma="scale")
        
        self.means = df_train[self.feature_columns].mean().to_dict()
        self.stds = df_train[self.feature_columns].std().to_dict()
        
        # For SVM, scaling is critical
        X_train = df_train[self.feature_columns].fillna(self.means).values
        if len(X_train) > 0:
            std_arr = np.array([self.stds.get(c, 1.0) for c in self.feature_columns])
            std_arr[std_arr == 0] = 1.0
            X_train_scaled = (X_train - np.array([self.means[c] for c in self.feature_columns])) / std_arr
            
            self.model.fit(X_train_scaled)
            self.is_trained = True
            self.std_arr = std_arr

    def predict(self, df_test: pd.DataFrame) -> pd.DataFrame:
        df_out = df_test.copy()
        if not self.is_trained:
            df_out['is_anomaly'] = False
            df_out['anomaly_score'] = 0.0
            return df_out
            
        X_test = df_test[self.feature_columns].fillna(self.means).values
        if len(X_test) == 0:
            df_out['is_anomaly'] = False
            df_out['anomaly_score'] = 0.0
            return df_out
            
        X_test_scaled = (X_test - np.array([self.means[c] for c in self.feature_columns])) / self.std_arr
        
        preds = self.model.predict(X_test_scaled)
        is_anomaly = preds == -1
        
        scores = -self.model.score_samples(X_test_scaled)
        
        df_out['is_anomaly'] = is_anomaly
        df_out['anomaly_score'] = scores
        return df_out
