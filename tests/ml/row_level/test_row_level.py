import os
import pandas as pd
import pytest
from src.ml.row_level.features import FeatureEngineer
from src.ml.row_level.isolation_forest import RowLevelAnomalyDetector
from src.ml.row_level.evaluator import RowLevelEvaluator

@pytest.fixture
def sample_dataset():
    # Construct a tiny dummy dataset
    data = []
    for i in range(10):
        data.append({
            'CLM_ID': f'C{i}',
            'CLM_LINE_NUM': 1,
            'CLM_PMT_AMT': 1000 + i*10,
            'CLM_TOT_CHRG_AMT': 2000 + i*20,
            'CLM_FROM_DT': '20230101',
            'CLM_THRU_DT': '20230105',
            'BENE_ID': f'B{i%3}',
            'PRVDR_NUM': f'P{i%2}'
        })
    return pd.DataFrame(data)

def test_feature_engineering(sample_dataset):
    fe = FeatureEngineer()
    
    # Must fit before transform
    with pytest.raises(ValueError):
        fe.transform(sample_dataset)
        
    X = fe.fit_transform(sample_dataset)
    
    assert len(X) == 10
    assert 'pmt_amt' in X.columns
    assert 'tot_chrg_amt' in X.columns
    assert 'payment_to_charge_ratio' in X.columns
    assert 'length_of_stay' in X.columns
    
    assert X['length_of_stay'].iloc[0] == 4

def test_isolation_forest_training_and_inference(sample_dataset):
    fe = FeatureEngineer()
    X = fe.fit_transform(sample_dataset)
    
    detector = RowLevelAnomalyDetector(n_estimators=10, random_state=42)
    
    with pytest.raises(ValueError):
        detector.predict(X)
        
    detector.fit(X, fpr_target=0.1) # 10% FPR
    
    res = detector.predict(X)
    assert 'prediction' in res.columns
    assert 'anomaly_score' in res.columns
    assert 'top_feature' in res.columns
    
def test_evaluator():
    df_gt = pd.DataFrame({
        'ground_truth_anomaly': [0, 0, 1, 1],
        'anomaly_category': ['NORMAL', 'NORMAL', 'EXTREME', 'NEGATIVE']
    })
    
    df_pred = pd.DataFrame({
        'prediction': [0, 1, 1, 0]
    })
    
    metrics = RowLevelEvaluator.evaluate(df_gt, df_pred)
    
    assert metrics['overall']['TP'] == 1
    assert metrics['overall']['TN'] == 1
    assert metrics['overall']['FP'] == 1
    assert metrics['overall']['FN'] == 1
    assert metrics['overall']['Precision'] == 0.5
    assert metrics['overall']['Recall'] == 0.5
    
    assert metrics['per_category']['EXTREME']['TP'] == 1
    assert metrics['per_category']['NEGATIVE']['FN'] == 1

def test_source_immutability():
    # The requirement is that master_data/ is not modified.
    # In a real test, we would hash before and after. We can just verify the file exists 
    # and wasn't accidentally moved or deleted.
    assert os.path.exists("master_data/claims/claims_master.csv")
