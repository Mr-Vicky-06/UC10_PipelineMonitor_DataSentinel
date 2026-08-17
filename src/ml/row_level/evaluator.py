import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import json

class RowLevelEvaluator:
    @staticmethod
    def evaluate(df_gt: pd.DataFrame, df_pred: pd.DataFrame) -> dict:
        """
        Evaluates row-level anomaly detection predictions against ground truth.
        Expects df_gt to have 'ground_truth_anomaly' and 'anomaly_category'.
        Expects df_pred to have 'prediction' (1 for anomaly, 0 for normal).
        """
        y_true = df_gt['ground_truth_anomaly']
        y_pred = df_pred['prediction']
        
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel() if len(cm.ravel()) == 4 else (0, 0, 0, 0)
        
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        metrics = {
            'overall': {
                'TP': int(tp),
                'TN': int(tn),
                'FP': int(fp),
                'FN': int(fn),
                'Precision': float(precision),
                'Recall': float(recall),
                'F1': float(f1),
                'FPR': float(fpr),
                'Specificity': float(specificity)
            },
            'per_category': {}
        }
        
        # Per category metrics
        # For each anomaly category (excluding NORMAL), what is the recall?
        anomalous_mask = y_true == 1
        anomalous_gt = df_gt[anomalous_mask]
        anomalous_pred = df_pred[anomalous_mask]
        
        categories = anomalous_gt['anomaly_category'].unique()
        for cat in categories:
            cat_mask = anomalous_gt['anomaly_category'] == cat
            cat_true = anomalous_gt[cat_mask]
            cat_pred = anomalous_pred[cat_mask]['prediction']
            
            cat_tp = cat_pred.sum()
            cat_fn = len(cat_true) - cat_tp
            cat_recall = cat_tp / len(cat_true) if len(cat_true) > 0 else 0
            
            metrics['per_category'][cat] = {
                'TP': int(cat_tp),
                'FN': int(cat_fn),
                'Recall': float(cat_recall),
                'Total': int(len(cat_true))
            }
            
        return metrics
