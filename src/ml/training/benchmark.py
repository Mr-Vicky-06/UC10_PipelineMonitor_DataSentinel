import pandas as pd
import numpy as np
import os
import json
import time

from src.ml.models.volume import VolumeMADModel, VolumeEWMAModel, VolumeCUSUMModel
from src.ml.models.distribution import DistributionWassersteinModel, DistributionKSModel, DistributionPSIModel
from src.ml.models.operational import OperationalIsolationForest, OperationalLOF, OperationalOneClassSVM

def calculate_metrics(df: pd.DataFrame, expected_domain: str):
    """Calculates confusion matrix metrics for a given dataframe and expected domain anomaly."""
    # An actual anomaly is defined as a row where is_anomalous is True and anomaly_domain == expected_domain
    actual_anomaly = (df['is_anomalous'] == True) & (df['anomaly_domain'] == expected_domain)
    predicted_anomaly = df['is_anomaly'] == True
    
    tp = (actual_anomaly & predicted_anomaly).sum()
    tn = (~actual_anomaly & ~predicted_anomaly).sum()
    fp = (~actual_anomaly & predicted_anomaly).sum()
    fn = (actual_anomaly & ~predicted_anomaly).sum()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    return {
        "TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn),
        "Precision": float(precision), "Recall": float(recall), "F1": float(f1), "FPR": float(fpr)
    }

def main():
    print("Starting ML Benchmarking...")
    
    data_path = "outputs/ml/datasets/development/development_dataset.csv"
    df = pd.read_csv(data_path)
    df['service_date'] = pd.to_datetime(df['service_date'])
    df = df.sort_values(by=['service_date', 'hospital_id'])
    
    # Chronological Split
    dates = sorted(df['service_date'].unique())
    if len(dates) < 30:
        raise ValueError("Need at least 30 days of data for splitting.")
        
    train_dates = dates[0:20]
    val_dates = dates[20:25]
    test_dates = dates[25:30]
    
    df_train = df[df['service_date'].isin(train_dates)].copy()
    df_val = df[df['service_date'].isin(val_dates)].copy()
    df_test = df[df['service_date'].isin(test_dates)].copy()
    
    domains = {
        "VOLUME": {
            "features": ['claim_volume', 'beneficiary_volume', 'provider_volume'],
            "candidates": {
                "MAD": VolumeMADModel,
                "EWMA": VolumeEWMAModel,
                "CUSUM": VolumeCUSUMModel
            }
        },
        "DISTRIBUTION": {
            "features": ['claim_amount_mean', 'claim_amount_median', 'claim_amount_total'],
            "candidates": {
                "Wasserstein_Proxy": DistributionWassersteinModel,
                "KS_Proxy": DistributionKSModel,
                "PSI_Proxy": DistributionPSIModel
            }
        },
        "OPERATIONAL": {
            "features": ['processing_duration', 'throughput', 'failure_rate'],
            "candidates": {
                "IsolationForest": OperationalIsolationForest,
                "LOF": OperationalLOF,
                "OneClassSVM": OperationalOneClassSVM
            }
        }
    }
    
    results = []
    best_models = {}
    
    # Train and Evaluate
    for domain_name, domain_info in domains.items():
        best_f1 = -1
        best_model_name = None
        features = domain_info["features"]
        
        for model_name, ModelClass in domain_info["candidates"].items():
            model = ModelClass(feature_columns=features)
            
            # Measure Training Latency
            t0 = time.time()
            model.fit(df_train)
            t_train = time.time() - t0
            
            # Predict on Test (Adversarial) Set
            t0 = time.time()
            df_pred = model.predict(df_test)
            t_infer = time.time() - t0
            
            # Calculate metrics
            metrics = calculate_metrics(df_pred, expected_domain=domain_name)
            metrics["Domain"] = domain_name
            metrics["Model"] = model_name
            metrics["Train Latency (s)"] = t_train
            metrics["Inference Latency (s)"] = t_infer
            
            results.append(metrics)
            
            if metrics["F1"] > best_f1:
                best_f1 = metrics["F1"]
                best_model_name = model_name
                
        best_models[domain_name] = best_model_name

    # Generate Report
    report = [
        "# AI/ML Model Benchmark Report",
        "",
        "## Training / Validation / Test Splitting",
        "- **Train (Days 1-20)**: Normal baseline data",
        "- **Validation (Days 21-25)**: Unseen normal baseline data (for hyperparameter checking)",
        "- **Test (Days 26-30)**: Adversarial simulated data with controlled anomalies",
        "",
        "## Performance Metrics (Test Set)",
        "| Domain | Model | Precision | Recall | F1 | FPR | TP | TN | FP | FN | Latency (ms) |",
        "|--------|-------|-----------|--------|----|-----|----|----|----|----|--------------|"
    ]
    
    for r in results:
        lat_ms = r['Inference Latency (s)'] * 1000
        row = f"| {r['Domain']} | {r['Model']} | {r['Precision']:.2f} | {r['Recall']:.2f} | {r['F1']:.2f} | {r['FPR']:.4f} | {r['TP']} | {r['TN']} | {r['FP']} | {r['FN']} | {lat_ms:.2f} |"
        report.append(row)
        
    report.extend([
        "",
        "## Selection Decisions",
        ""
    ])
    
    for domain_name, best_model_name in best_models.items():
        report.append(f"### Domain: {domain_name}")
        report.append(f"- **Best Model**: {best_model_name}")
        
        # Sort domain models by F1
        domain_results = sorted([r for r in results if r['Domain'] == domain_name], key=lambda x: x['F1'], reverse=True)
        backup_model = domain_results[1]['Model'] if len(domain_results) > 1 else "None"
        
        report.append(f"- **Backup Model**: {backup_model}")
        report.append(f"- **Reason**: Highest empirical F1 score on chronological adversarial test split.")
        report.append("")
        
    with open("MODEL_BENCHMARK_REPORT.md", "w") as f:
        f.write("\n".join(report))
        
    # Also write a simpler JSON evaluation report
    with open("outputs/ml/reports/evaluation_results.json", "w") as f:
        json.dump({"results": results, "best_models": best_models}, f, indent=2)
        
    print("Benchmarking completed. Report saved to MODEL_BENCHMARK_REPORT.md.")

if __name__ == "__main__":
    main()
