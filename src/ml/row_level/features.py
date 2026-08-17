import pandas as pd
import numpy as np

class FeatureEngineer:
    """Extracts features for row-level ML detection without data leakage."""
    
    def __init__(self):
        self.bene_freq = {}
        self.prvdr_freq = {}
        self.is_fitted = False
        
    def fit(self, df_train: pd.DataFrame):
        """Fit categorical encodings on training data only."""
        self.bene_freq = df_train['BENE_ID'].value_counts(normalize=True).to_dict()
        self.prvdr_freq = df_train['PRVDR_NUM'].value_counts(normalize=True).to_dict()
        self.is_fitted = True
        
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform dataset to feature matrix."""
        if not self.is_fitted:
            raise ValueError("FeatureEngineer must be fitted before transform.")
            
        features = pd.DataFrame(index=df.index)
        
        # Payment amounts
        features['pmt_amt'] = pd.to_numeric(df['CLM_PMT_AMT'], errors='coerce').fillna(0.0)
        features['tot_chrg_amt'] = pd.to_numeric(df['CLM_TOT_CHRG_AMT'], errors='coerce').fillna(0.0)
        
        # Payment to charge ratio
        # Avoid division by zero
        chrg_safe = np.where(features['tot_chrg_amt'] == 0, 1.0, features['tot_chrg_amt'])
        features['payment_to_charge_ratio'] = features['pmt_amt'] / chrg_safe
        
        # Length of stay
        from_dt = pd.to_datetime(df['CLM_FROM_DT'], format='%Y%m%d', errors='coerce')
        thru_dt = pd.to_datetime(df['CLM_THRU_DT'], format='%Y%m%d', errors='coerce')
        
        los_days = (thru_dt - from_dt).dt.days
        # If missing or impossible to parse, impute with 0
        features['length_of_stay'] = los_days.fillna(0.0)
        
        # Frequency encodings
        features['bene_freq'] = df['BENE_ID'].map(self.bene_freq).fillna(0.0)
        features['prvdr_freq'] = df['PRVDR_NUM'].map(self.prvdr_freq).fillna(0.0)
        
        return features
        
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self.fit(df)
        return self.transform(df)
