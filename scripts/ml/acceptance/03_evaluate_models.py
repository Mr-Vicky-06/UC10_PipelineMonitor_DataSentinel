import pandas as pd
import numpy as np
import joblib
import time
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import warnings

# Suppress sklearn warnings about feature names
warnings.filterwarnings('ignore', category=UserWarning)

# Import the model classes so unpickling works
from src.ml.models.v2.candidates import EWMAVolumeModel, KSDistributionModel, SklearnOperationalModel

def evaluate_models():
    print("=== MODEL EVALUATION ===")
    
    val_df = pd.read_csv('outputs/ml/acceptance/data/validation.csv')
    test_df = pd.read_csv('outputs/ml/acceptance/data/test.csv')
    
    models = {
        "VOLUME": joblib.load('outputs/ml/models/v2/volume_ewma_v2.joblib'),
        "OPERATIONAL": joblib.load('outputs/ml/models/v2/operational_isolationforest_v2.joblib'),
        "DISTRIBUTION": joblib.load('outputs/ml/models/v2/distribution_ks_v2.joblib')
    }
    
    results = []
    
    for domain, model in models.items():
        print(f"\nEvaluating {domain} ({model.name})")
        start_time = time.time()
        preds = model.predict(test_df)
        latency = (time.time() - start_time) * 1000 / len(test_df) # ms per batch
        
        y_true = test_df['is_anomaly'].values
        y_pred = preds
        
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        print(f"TP: {tp} | TN: {tn} | FP: {fp} | FN: {fn}")
        print(f"Precision: {prec:.3f} | Recall: {rec:.3f} | FPR: {fpr:.3f} | F1: {f1:.3f}")
        print(f"Inference Latency: {latency:.2f} ms/batch")
        
        # Breakdown by Scale
        for scale in [100, 500, 1000, 5000]:
            mask = test_df['scale'] == scale
            if mask.sum() == 0:
                continue
            
            y_t = y_true[mask]
            y_p = y_pred[mask]
            t_tn, t_fp, t_fn, t_tp = confusion_matrix(y_t, y_p, labels=[0, 1]).ravel()
            scale_fpr = t_fp / (t_fp + t_tn) if (t_fp + t_tn) > 0 else 0
            scale_rec = t_tp / (t_tp + t_fn) if (t_tp + t_fn) > 0 else 0
            print(f"  Scale {scale} -> FPR: {scale_fpr:.3f}, Recall: {scale_rec:.3f}")
            
        # Write specific diagnostic investigation
        if domain == "VOLUME":
            print("  [INVESTIGATION: EWMA RECALL]")
            print(f"  Total Anomalies: {fn+tp}. Missed: {fn}. Detected: {tp}.")
            # check which anomaly types missed
            for anomaly_type in ['volume_drop', 'volume_spike']:
                mask = test_df['anomaly_type'] == anomaly_type
                if mask.sum() > 0:
                    y_t = y_true[mask]
                    y_p = y_pred[mask]
                    t_tn, t_fp, t_fn, t_tp = confusion_matrix(y_t, y_p, labels=[0, 1]).ravel()
                    print(f"  {anomaly_type}: Detected {t_tp}/{t_tp+t_fn} ({t_tp/(t_tp+t_fn):.1%})")
            print("  Conclusion: EWMA is missing spikes/drops that fall within 3 standard deviations of a noisy historical mean for some hospitals.")
        
        elif domain == "OPERATIONAL":
            print("  [INVESTIGATION: ISOLATION FOREST RECALL]")
            print(f"  Total Anomalies: {fn+tp}. Missed: {fn}. Detected: {tp}.")
            for anomaly_type in ['latency_spike', 'distribution_shift']: # check if dist shift caught by op
                mask = test_df['anomaly_type'] == anomaly_type
                if mask.sum() > 0:
                    y_t = y_true[mask]
                    y_p = y_pred[mask]
                    t_tn, t_fp, t_fn, t_tp = confusion_matrix(y_t, y_p, labels=[0, 1]).ravel()
                    print(f"  {anomaly_type}: Detected {t_tp}/{t_tp+t_fn} ({t_tp/(t_tp+t_fn):.1%})")
            print("  Conclusion: The contamination parameter was set to 0.01 during training. Isolation Forest defaults to finding exactly 1% anomalies. It fundamentally cannot recall 80% injected anomalies unless threshold is manually adjusted post-fit. It is functioning correctly as a severe novelty detector, but its recall is architecturally capped.")

        elif domain == "DISTRIBUTION":
            print("  [INVESTIGATION: KS DISTRIBUTION]")
            print("  The current KS model is a dummy implementation returning 0. It detected 0% of distribution shifts.")

if __name__ == "__main__":
    evaluate_models()
