import joblib
import os
import json
import numpy as np

def audit_artifacts():
    print("=== MODEL ARTIFACT AUDIT ===")
    
    models_to_check = {
        "VOLUME (EWMA)": "outputs/ml/models/v2/volume_ewma_v2.joblib",
        "OPERATIONAL (Isolation Forest)": "outputs/ml/models/v2/operational_isolationforest_v2.joblib",
        "DISTRIBUTION (KS)": "outputs/ml/models/v2/distribution_ks_v2.joblib"
    }
    
    audit_lines = ["# MODEL ARTIFACT AUDIT", ""]
    
    for name, path in models_to_check.items():
        audit_lines.append(f"## {name}")
        audit_lines.append(f"- **Artifact Path**: `{path}`")
        if not os.path.exists(path):
            audit_lines.append("- **Status**: FILE NOT FOUND")
            continue
            
        try:
            model = joblib.load(path)
            audit_lines.append(f"- **Python Type**: `{type(model).__name__}`")
            audit_lines.append(f"- **Domain Name**: `{getattr(model, 'domain', 'UNKNOWN')}`")
            audit_lines.append(f"- **Algorithm Name**: `{getattr(model, 'name', 'UNKNOWN')}`")
            
            # Extract features depending on type
            if hasattr(model, 'hospital_means'):
                audit_lines.append(f"- **State Tracks**: `{len(model.hospital_means)}` hospitals")
            if hasattr(model, 'features'):
                audit_lines.append(f"- **Features**: `{model.features}`")
            if hasattr(model, 'model') and hasattr(model.model, 'get_params'):
                audit_lines.append(f"- **Hyperparameters**: `{model.model.get_params()}`")
            if hasattr(model, 'threshold'):
                audit_lines.append(f"- **Threshold**: `{model.threshold}`")
                
            audit_lines.append("- **Status**: LOADED SUCCESSFULLY")
        except Exception as e:
            audit_lines.append(f"- **Status**: LOAD FAILED ({str(e)})")
            
        audit_lines.append("")
        
    with open("outputs/ml/acceptance/MODEL_ARTIFACT_AUDIT.md", "w") as f:
        f.write("\n".join(audit_lines))
        
    print("Generated MODEL_ARTIFACT_AUDIT.md")

if __name__ == "__main__":
    audit_artifacts()
