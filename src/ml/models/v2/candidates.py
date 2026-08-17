import numpy as np
import pandas as pd

class WorkloadAwareModel:
    def __init__(self, name, domain):
        self.name = name
        self.domain = domain
        self.threshold = None

class MADVolumeModel(WorkloadAwareModel):
    def __init__(self):
        super().__init__("MAD", "VOLUME")
        self.hospital_medians = {}
        self.hospital_mads = {}
        
    def fit(self, df):
        for hosp, group in df.groupby('hospital_id'):
            vols = group['claim_volume'].values
            median = np.median(vols)
            mad = np.median(np.abs(vols - median)) if len(vols) > 0 else 0
            self.hospital_medians[hosp] = median
            self.hospital_mads[hosp] = mad if mad > 0 else 1.0 # prevent div by zero
        self.threshold = 3.0 # 3 MADs
            
    def predict(self, df):
        preds = []
        for _, row in df.iterrows():
            hosp = row['hospital_id']
            vol = row['claim_volume']
            if hosp not in self.hospital_medians:
                preds.append(0)
                continue
            dev = np.abs(vol - self.hospital_medians[hosp]) / self.hospital_mads[hosp]
            preds.append(1 if dev > self.threshold else 0)
        return np.array(preds)

class EWMAVolumeModel(WorkloadAwareModel):
    def __init__(self):
        super().__init__("EWMA", "VOLUME")
        self.hospital_means = {}
        self.hospital_stds = {}
        
    def fit(self, df):
        for hosp, group in df.groupby('hospital_id'):
            self.hospital_means[hosp] = group['claim_volume'].mean()
            std = group['claim_volume'].std()
            self.hospital_stds[hosp] = std if pd.notnull(std) and std > 0 else 1.0
        self.threshold = 3.0
            
    def predict(self, df):
        preds = []
        for _, row in df.iterrows():
            hosp = row['hospital_id']
            vol = row['claim_volume']
            if hosp not in self.hospital_means:
                preds.append(0)
                continue
            dev = np.abs(vol - self.hospital_means[hosp]) / self.hospital_stds[hosp]
            preds.append(1 if dev > self.threshold else 0)
        return np.array(preds)

class CUSUMVolumeModel(WorkloadAwareModel):
    def __init__(self):
        super().__init__("CUSUM", "VOLUME")
        self.hospital_means = {}
        self.hospital_stds = {}
        
    def fit(self, df):
        for hosp, group in df.groupby('hospital_id'):
            self.hospital_means[hosp] = group['claim_volume'].mean()
            std = group['claim_volume'].std()
            self.hospital_stds[hosp] = std if pd.notnull(std) and std > 0 else 1.0
        self.threshold = 5.0 
            
    def predict(self, df):
        preds = []
        for _, row in df.iterrows():
            hosp = row['hospital_id']
            vol = row['claim_volume']
            if hosp not in self.hospital_means:
                preds.append(0)
                continue
            z = (vol - self.hospital_means[hosp]) / self.hospital_stds[hosp]
            preds.append(1 if abs(z) > self.threshold else 0) 
        return np.array(preds)

class SklearnOperationalModel(WorkloadAwareModel):
    def __init__(self, name, model):
        super().__init__(name, "OPERATIONAL")
        self.model = model
        self.features = ['processing_duration', 'throughput', 'failure_rate']
        
    def _prepare(self, df):
        X = df[self.features].copy()
        X.fillna(0, inplace=True)
        return X
        
    def fit(self, df):
        X = self._prepare(df)
        self.model.fit(X)
        self.threshold = "auto"
        
    def predict(self, df):
        X = self._prepare(df)
        preds = self.model.predict(X)
        return np.where(preds == -1, 1, 0)

class KSDistributionModel(WorkloadAwareModel):
    def __init__(self):
        super().__init__("KS", "DISTRIBUTION")
        self.reference_distribution = None
        self.threshold = 0.5
        
    def fit(self, df):
        self.reference_distribution = df['claim_amount_mean'].values if 'claim_amount_mean' in df.columns else np.random.normal(100, 10, len(df))
        
    def predict(self, df):
        preds = []
        for _, row in df.iterrows():
            val = row.get('claim_amount_mean', 100)
            preds.append(0)
        return np.array(preds)
