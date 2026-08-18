import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

class WorkloadAwareModelV3:
    def __init__(self, name, domain):
        self.name = name
        self.domain = domain
        self.threshold = None

class MADVolumeModelV3(WorkloadAwareModelV3):
    def __init__(self):
        super().__init__("MAD", "VOLUME")
        self.global_median = 0
        self.global_mad = 1
        
    def fit(self, df):
        vols = df['normalized_volume_zscore'].values
        self.global_median = np.median(vols)
        mad = np.median(np.abs(vols - self.global_median))
        self.global_mad = mad if mad > 0 else 1.0
        self.threshold = 3.0 
            
    def predict(self, df):
        vols = df['normalized_volume_zscore'].values
        dev = np.abs(vols - self.global_median) / self.global_mad
        return np.where(dev > self.threshold, 1, 0)

class EWMAVolumeModelV3(WorkloadAwareModelV3):
    def __init__(self):
        super().__init__("EWMA", "VOLUME")
        self.global_mean = 0
        self.global_std = 1
        
    def fit(self, df):
        vols = df['normalized_volume_zscore'].values
        self.global_mean = vols.mean()
        std = vols.std()
        self.global_std = std if pd.notnull(std) and std > 0 else 1.0
        self.threshold = 4.0
            
    def predict(self, df):
        vols = df['normalized_volume_zscore'].values
        dev = np.abs(vols - self.global_mean) / self.global_std
        return np.where(dev > self.threshold, 1, 0)

class CUSUMVolumeModelV3(WorkloadAwareModelV3):
    def __init__(self):
        super().__init__("CUSUM", "VOLUME")
        self.global_mean = 0
        self.global_std = 1
        self.hospital_cusums = {}
        
    def fit(self, df):
        vols = df['normalized_volume_zscore'].values
        self.global_mean = vols.mean()
        std = vols.std()
        self.global_std = std if pd.notnull(std) and std > 0 else 1.0
        
        for hosp in df['hospital_id'].unique():
            self.hospital_cusums[hosp] = 0.0
        self.threshold = 15.0 
            
    def predict(self, df):
        preds = []
        for _, row in df.iterrows():
            hosp = row['hospital_id']
            vol = row['normalized_volume_zscore']
            if hosp not in self.hospital_cusums:
                self.hospital_cusums[hosp] = 0.0
            
            # CUSUM accumulation
            z = (vol - self.global_mean) / self.global_std
            
            # For volume drops, z is negative, so we track negative deviations
            # We also track positive deviations. 
            # In our anomalies, we inject volume_drop_50 and volume_spike_100
            self.hospital_cusums[hosp] = max(0, self.hospital_cusums[hosp] + abs(z) - 0.5)
            preds.append(1 if self.hospital_cusums[hosp] > self.threshold else 0) 
        return np.array(preds)

class SklearnOperationalModelV3(WorkloadAwareModelV3):
    def __init__(self, name, model):
        super().__init__(name, "OPERATIONAL")
        self.model = model
        self.features = ['normalized_volume_zscore', 'throughput', 'failure_rate']
        
    def _prepare(self, df):
        X = df[self.features].copy()
        X.fillna(0, inplace=True)
        return X
        
    def fit(self, df):
        X = self._prepare(df)
        if len(X) > 0:
            self.model.fit(X)
        self.threshold = "auto"
        
    def predict(self, df):
        X = self._prepare(df)
        if len(X) == 0:
            return np.array([])
        
        preds = self.model.predict(X)
        return np.where(preds == -1, 1, 0)
