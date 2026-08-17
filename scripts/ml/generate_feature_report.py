import os
from src.ml.features.contract import FeatureContract
import json

def main():
    matrix = FeatureContract.get_feature_matrix()
    
    report = ["# AI/ML Feature Contract Report\n",
              "This document outlines the availability of the 18-feature contract for AI/ML detection.\n",
              "| Feature | Available | Training Ready | Used By Model | Reason Excluded |",
              "|---|---|---|---|---|"]
              
    for m in matrix:
        available = "YES" if m['available'] else "NO"
        training_ready = "YES" if m['training_ready'] else "NO"
        used = "YES" if m['used_by_model'] else "NO"
        reason = m['reason_if_excluded'] if not m['available'] else ""
        report.append(f"| `{m['feature']}` | {available} | {training_ready} | {used} | {reason} |")
        
    report_content = "\n".join(report)
    
    out_path = "AI_ML_FEATURE_CONTRACT_REPORT.md"
    with open(out_path, "w") as f:
        f.write(report_content)
        
    print(f"Generated {out_path}")

if __name__ == "__main__":
    main()
