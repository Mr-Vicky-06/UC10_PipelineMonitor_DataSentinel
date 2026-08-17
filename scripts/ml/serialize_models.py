import pandas as pd
import json
import joblib
import os
from datetime import datetime

from src.ml.models.volume import VolumeMADModel, VolumeEWMAModel, VolumeCUSUMModel
from src.ml.models.distribution import DistributionWassersteinModel, DistributionKSModel, DistributionPSIModel
from src.ml.models.operational import OperationalIsolationForest, OperationalLOF, OperationalOneClassSVM

def main():
    print("Starting Model Serialization...")
    
    # 1. Read best models
    with open("outputs/ml/reports/evaluation_results.json", "r") as f:
        eval_data = json.load(f)
    best_models = eval_data.get("best_models", {})
    
    if not best_models:
        print("No best models found in evaluation report.")
        return
        
    # 2. Load baseline data (Train + Val, days 1-25)
    data_path = "outputs/ml/datasets/development/development_dataset.csv"
    df = pd.read_csv(data_path)
    df['service_date'] = pd.to_datetime(df['service_date'])
    df = df.sort_values(by=['service_date', 'hospital_id'])
    
    dates = sorted(df['service_date'].unique())
    baseline_dates = dates[0:25]
    df_baseline = df[df['service_date'].isin(baseline_dates)].copy()
    
    model_mapping = {
        "MAD": VolumeMADModel,
        "EWMA": VolumeEWMAModel,
        "CUSUM": VolumeCUSUMModel,
        "Wasserstein_Proxy": DistributionWassersteinModel,
        "KS_Proxy": DistributionKSModel,
        "PSI_Proxy": DistributionPSIModel,
        "IsolationForest": OperationalIsolationForest,
        "LOF": OperationalLOF,
        "OneClassSVM": OperationalOneClassSVM
    }
    
    domain_features = {
        "VOLUME": ['claim_volume', 'beneficiary_volume', 'provider_volume'],
        "DISTRIBUTION": ['claim_amount_mean', 'claim_amount_median', 'claim_amount_total'],
        "OPERATIONAL": ['processing_duration', 'throughput', 'failure_rate']
    }
    
    registry = []
    
    for domain, model_name in best_models.items():
        if model_name not in model_mapping:
            print(f"Model {model_name} not found in mapping.")
            continue
            
        ModelClass = model_mapping[model_name]
        features = domain_features[domain]
        
        # 3. Train on baseline
        model = ModelClass(feature_columns=features)
        model.fit(df_baseline)
        
        # 4. Serialize
        version = datetime.now().strftime("%Y%m%d%H%M%S")
        model_filename = f"{domain.lower()}_{model_name.lower()}_v{version}.joblib"
        model_path = os.path.join("outputs", "ml", "models", model_filename)
        
        joblib.dump(model, model_path)
        print(f"Saved {domain} model to {model_path}")
        
        # 5. Add to registry
        registry.append({
            "domain": domain,
            "model_name": model_name,
            "version": version,
            "path": model_path,
            "features": features,
            "status": "PROMOTED_FOR_INFERENCE",
            "trained_on": "Days 1-25 Simulation Baseline"
        })
        
    # Write Registry JSON
    registry_path = "outputs/ml/registry/model_registry.json"
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)
        
    # Write Registry Markdown Report
    report = [
        "# AI/ML Model Registry",
        "",
        "| Domain | Model | Version | Status | Trained On |",
        "|--------|-------|---------|--------|------------|"
    ]
    
    for r in registry:
        report.append(f"| {r['domain']} | {r['model_name']} | {r['version']} | {r['status']} | {r['trained_on']} |")
        
    with open("AI_ML_MODEL_REGISTRY.md", "w") as f:
        f.write("\n".join(report))
        
    print("Serialization completed. Registry updated.")

if __name__ == "__main__":
    main()
