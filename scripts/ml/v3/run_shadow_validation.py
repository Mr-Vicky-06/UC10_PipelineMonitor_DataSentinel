import pandas as pd
import numpy as np
import json
import os
import time
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

import sys
sys.path.append(os.path.abspath("."))

from src.ml.models.v2.candidates import MADVolumeModel, EWMAVolumeModel, CUSUMVolumeModel, SklearnOperationalModel
from src.ml.v3.models.candidates import MADVolumeModelV3, EWMAVolumeModelV3, CUSUMVolumeModelV3, SklearnOperationalModelV3

def calc_metrics(y_true, y_pred):
    if len(y_true) == 0:
        return 0, 0, 0, 0
    p = precision_score(y_true, y_pred, zero_division=0)
    r = recall_score(y_true, y_pred, zero_division=0)
    f = f1_score(y_true, y_pred, zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    else:
        tn = sum((y_true == 0) & (y_pred == 0))
        fp = sum((y_true == 0) & (y_pred == 1))
        fn = sum((y_true == 1) & (y_pred == 0))
        tp = sum((y_true == 1) & (y_pred == 1))
        
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return p, r, f, fpr

def evaluate_models():
    train_df = pd.read_csv("outputs/ml/v3/telemetry_train.csv")
    eval_normal_df = pd.read_csv("outputs/ml/v3/telemetry_eval_normal.csv")
    eval_anom_df = pd.read_csv("outputs/ml/v3/telemetry_eval_anomalous.csv")
    
    # Combine evals
    test_df = pd.concat([eval_normal_df, eval_anom_df], ignore_index=True)
    
    # Target definitions
    # For Volume: we only care about volume drops and spikes
    y_true_vol = np.where(test_df['injected_anomaly_type'].isin(['VOLUME_DROP_50', 'VOLUME_SPIKE_100']), 1, 0)
    
    # For Operational: latency and failure spikes
    y_true_op = np.where(test_df['injected_anomaly_type'].isin(['LATENCY_SPIKE', 'FAILURE_SPIKE']), 1, 0)
    
    results = []
    
    # --- V2 Models ---
    v2_vol_mad = MADVolumeModel()
    v2_vol_ewma = EWMAVolumeModel()
    v2_vol_cusum = CUSUMVolumeModel()
    
    v2_op_iso = SklearnOperationalModel("IsolationForest", IsolationForest(random_state=42))
    v2_op_lof = SklearnOperationalModel("LOF", LocalOutlierFactor(novelty=True))
    v2_op_svm = SklearnOperationalModel("OneClassSVM", OneClassSVM(nu=0.1))
    
    # Train
    v2_vol_mad.fit(train_df)
    v2_vol_ewma.fit(train_df)
    v2_vol_cusum.fit(train_df)
    v2_op_iso.fit(train_df)
    v2_op_lof.fit(train_df)
    v2_op_svm.fit(train_df)
    
    # --- V3 Models ---
    v3_vol_mad = MADVolumeModelV3()
    v3_vol_ewma = EWMAVolumeModelV3()
    v3_vol_cusum = CUSUMVolumeModelV3()
    
    v3_op_iso = SklearnOperationalModelV3("IsolationForest", IsolationForest(random_state=42, contamination=0.02))
    v3_op_lof = SklearnOperationalModelV3("LOF", LocalOutlierFactor(novelty=True, contamination=0.02))
    v3_op_svm = SklearnOperationalModelV3("OneClassSVM", OneClassSVM(nu=0.02))
    
    v3_vol_mad.fit(train_df)
    v3_vol_ewma.fit(train_df)
    v3_vol_cusum.fit(train_df)
    v3_op_iso.fit(train_df)
    v3_op_lof.fit(train_df)
    v3_op_svm.fit(train_df)
    
    models = [
        ("V2_VOLUME_MAD", v2_vol_mad, y_true_vol),
        ("V2_VOLUME_EWMA", v2_vol_ewma, y_true_vol),
        ("V2_VOLUME_CUSUM", v2_vol_cusum, y_true_vol),
        ("V2_OPERATIONAL_ISO", v2_op_iso, y_true_op),
        ("V2_OPERATIONAL_LOF", v2_op_lof, y_true_op),
        ("V2_OPERATIONAL_SVM", v2_op_svm, y_true_op),
        ("V3_VOLUME_MAD", v3_vol_mad, y_true_vol),
        ("V3_VOLUME_EWMA", v3_vol_ewma, y_true_vol),
        ("V3_VOLUME_CUSUM", v3_vol_cusum, y_true_vol),
        ("V3_OPERATIONAL_ISO", v3_op_iso, y_true_op),
        ("V3_OPERATIONAL_LOF", v3_op_lof, y_true_op),
        ("V3_OPERATIONAL_SVM", v3_op_svm, y_true_op)
    ]
    
    shadow_preds = []
    
    for name, model, y_true in models:
        start_t = time.time()
        y_pred = model.predict(test_df)
        latency = (time.time() - start_t) * 1000 / len(test_df) # per batch approx
        
        p, r, f, fpr = calc_metrics(y_true, y_pred)
        results.append({
            "model": name,
            "workload": "ALL",
            "precision": p,
            "recall": r,
            "f1": f,
            "fpr": fpr,
            "latency_ms": latency
        })
        
        # By workload band
        for band in ['MICRO', 'SMALL', 'MEDIUM', 'LARGE']:
            mask = test_df['workload_band'] == band
            if mask.sum() > 0:
                p_b, r_b, f_b, fpr_b = calc_metrics(y_true[mask], y_pred[mask])
                results.append({
                    "model": name,
                    "workload": band,
                    "precision": p_b,
                    "recall": r_b,
                    "f1": f_b,
                    "fpr": fpr_b,
                    "latency_ms": latency
                })
        
        # shadow log for the winners (we'll just log all to shadow output)
        for i, row in test_df.iterrows():
            shadow_preds.append({
                "batch_id": row['batch_id'],
                "hospital_id": row['hospital_id'],
                "workload_band": row['workload_band'],
                "model": name,
                "prediction": int(y_pred[i]),
                "actual": int(y_true[i]),
                "injected_anomaly_type": row['injected_anomaly_type']
            })
            
    res_df = pd.DataFrame(results)
    res_df.to_csv("outputs/ml/evaluation/v3/model_metrics.csv", index=False)
    
    with open("outputs/ml/evaluation/v3/shadow_predictions.jsonl", "w") as f:
        for p in shadow_preds:
            f.write(json.dumps(p) + "\n")
            
    return res_df

if __name__ == "__main__":
    df = evaluate_models()
    print("Evaluation complete. Metrics saved to outputs/ml/evaluation/v3/model_metrics.csv")
    print(df[df['workload'] == 'ALL'].to_string())
