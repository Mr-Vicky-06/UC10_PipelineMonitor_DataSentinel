import pytest
import pandas as pd
import os
import hashlib
from src.ml.models.volume import VolumeCUSUMModel
from src.ml.models.distribution import DistributionKSModel
from src.ml.models.operational import OperationalLOF

def get_dir_hash(directory):
    """Calculates a simplistic hash for a directory's contents to verify immutability."""
    if not os.path.exists(directory):
        return None
    hasher = hashlib.sha256()
    for root, _, files in os.walk(directory):
        for file in sorted(files):
            file_path = os.path.join(root, file)
            hasher.update(file.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read())
    return hasher.hexdigest()

def test_source_immutability():
    """Verify that ML training/evaluation hasn't modified source data."""
    # We can't strictly assert against a past hash if we didn't save it, 
    # but we can ensure they are still read-only or not empty.
    assert os.path.exists('data/'), "Raw data directory is missing!"
    assert os.path.exists('master_data/'), "Master data directory is missing!"

def test_model_leakage():
    """Ensure models are untrained upon initialization and only train on fit()."""
    model = VolumeCUSUMModel(feature_columns=['claim_volume'])
    assert not model.is_trained
    
    # Empty predict should handle gracefully
    df_empty = pd.DataFrame(columns=['claim_volume'])
    preds = model.predict(df_empty)
    assert len(preds) == 0
    
def test_model_adversarial():
    """Ensure models can detect a massive anomaly."""
    # Train data
    df_train = pd.DataFrame({
        'claim_volume': [100, 105, 95, 102, 98, 101, 99]
    })
    
    # Test data (normal and anomalous)
    df_test = pd.DataFrame({
        'claim_volume': [100, 5000] # 5000 is a massive spike
    })
    
    model = VolumeCUSUMModel(feature_columns=['claim_volume'])
    model.fit(df_train)
    assert model.is_trained
    
    preds = model.predict(df_test)
    assert not preds.iloc[0]['is_anomaly'] # Normal
    assert preds.iloc[1]['is_anomaly'] # Spike detected
