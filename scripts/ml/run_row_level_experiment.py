import pandas as pd
import json
import os
from src.ml.row_level.features import FeatureEngineer
from src.ml.row_level.isolation_forest import RowLevelAnomalyDetector
from src.ml.row_level.evaluator import RowLevelEvaluator
from src.ml.row_level.comparison import BusinessRuleComparator

def main():
    print("Running Row-Level ML Experiment...")
    
    # 1. Load Data
    dir_path = "outputs/ml/row_level/dataset"
    df_normal = pd.read_csv(f"{dir_path}/claims_1000_normal.csv", sep=',', dtype=str)
    df_adv = pd.read_csv(f"{dir_path}/claims_1000_adversarial.csv", sep=',', dtype=str)
    df_gt = pd.read_csv(f"{dir_path}/ground_truth.csv", sep=',', dtype=str)
    df_gt['ground_truth_anomaly'] = df_gt['ground_truth_anomaly'].astype(int)
    
    # In the dataset script, df_normal is just the original 1000 records.
    # We should train on the NORMAL records ONLY.
    # Since df_normal is the 1000 clean records, let's use the first 500 for training, 
    # 200 for calibration. Or just use the 700 that remain clean in df_adv!
    
    # Find the indices of normal records in the ground truth
    normal_indices = df_gt[df_gt['ground_truth_anomaly'] == 0].index
    
    # X_train is the normal records from df_adv (which are identical to df_normal for those indices)
    df_train_raw = df_adv.loc[normal_indices]
    
    # 2. Feature Engineering
    fe = FeatureEngineer()
    # Fit only on the 700 normal
    X_train = fe.fit_transform(df_train_raw)
    
    # Transform all 1000
    X_all = fe.transform(df_adv)
    
    # 3. Model Training
    detector = RowLevelAnomalyDetector(
        n_estimators=100,
        contamination=0.01, # this gets overridden by threshold calibration
        random_state=42
    )
    
    # We fit on the 700 normal records. We set fpr_target to 0.05 (5% FP on normal data)
    detector.fit(X_train, fpr_target=0.05)
    
    # 4. Inference
    df_pred = detector.predict(X_all)
    
    # 5. Evaluation
    evaluator = RowLevelEvaluator()
    metrics = evaluator.evaluate(df_gt, df_pred)
    
    # 6. Business Rule Comparison
    comparator = BusinessRuleComparator()
    comp_results = comparator.evaluate(df_adv, df_gt, df_pred)
    
    # 7. Save Artifacts
    out_model = "outputs/ml/row_level/models"
    out_eval = "outputs/ml/row_level/evaluation"
    out_report = "outputs/ml/row_level/reports"
    os.makedirs(out_model, exist_ok=True)
    os.makedirs(out_eval, exist_ok=True)
    os.makedirs(out_report, exist_ok=True)
    
    detector.save(f"{out_model}/row_level_isolation_forest.joblib")
    df_pred.to_csv(f"{out_eval}/predictions.csv", index=False)
    comp_results['detailed_results'].to_csv(f"{out_eval}/comparison_detailed.csv", index=False)
    
    with open(f"{out_eval}/model_metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    # Generate Markdown Report
    generate_markdown_report(metrics, comp_results, df_pred, df_gt)
    print("Experiment completed successfully.")

def generate_markdown_report(metrics, comp_results, df_pred, df_gt):
    report_path = "C:/Users/ASUS/.gemini/antigravity-ide/brain/be32f287-9a70-4206-9fc5-749279cab130/ROW_LEVEL_ML_EVALUATION.md"
    
    md = f"""# ROW-LEVEL ML DETECTION EXPERIMENT EVALUATION

## 1. Objective
Demonstrate whether an unsupervised ML model (Isolation Forest) can identify statistically anomalous individual healthcare claim lines independently of the existing deterministic Business Rule Engine, using a Row-Level analysis on exactly 1,000 real claims.

## 2. Dataset Construction
- **Source**: 1,000 real records from `master_data/claims/claims_master.csv`
- **700 Normal**: Kept perfectly clean (0 anomalies).
- **300 Anomalous**: Modified through controlled defect injection.

## 3. Anomaly Categories
We injected the following controlled categories:
- EXTREME_AMOUNT (100-500x multiplier)
- NEGATIVE_AMOUNT (Negative sign)
- ZERO_AMOUNT (Payment = 0)
- EXTREME_LOS (Length of stay > 1000 days)
- IMPOSSIBLE_CHRONOLOGY (Thru date before From date)

## 4. Feature Contract
The row-level ML model utilizes the following extracted features:
- `pmt_amt` (CLM_PMT_AMT)
- `tot_chrg_amt` (CLM_TOT_CHRG_AMT)
- `payment_to_charge_ratio`
- `length_of_stay`
- `bene_freq` (Target frequency encoding)
- `prvdr_freq` (Target frequency encoding)

## 5. Model Configuration & Methodology
- **Model**: Isolation Forest (`sklearn.ensemble.IsolationForest`)
- **n_estimators**: 100
- **Training**: Fitted exclusively on the 700 normal records (Semi-supervised novelty detection).
- **Leakage Controls**: The model did not see any anomalous records during training. Frequency encoding was fitted only on the 700 normal records.
- **Threshold Methodology**: We calibrated the decision threshold on the training (normal) set to allow a 5% False Positive Rate on normal data (95th percentile of normal anomaly scores). This ensures we did not cheat by setting `contamination=0.30`.

## 6. Overall Performance

| Metric | Value |
|--------|-------|
| True Positives | {metrics['overall']['TP']} |
| True Negatives | {metrics['overall']['TN']} |
| False Positives| {metrics['overall']['FP']} |
| False Negatives| {metrics['overall']['FN']} |
| Precision | {metrics['overall']['Precision']:.4f} |
| Recall | {metrics['overall']['Recall']:.4f} |
| F1 Score | {metrics['overall']['F1']:.4f} |
| FPR | {metrics['overall']['FPR']:.4f} |
| Specificity | {metrics['overall']['Specificity']:.4f} |

## 7. Per-Category Performance
"""
    for cat, stats in metrics['per_category'].items():
        if cat == "NORMAL": continue
        md += f"- **{cat}**: {stats['TP']} / {stats['Total']} (Recall: {stats['Recall']:.2%})\n"

    md += f"""
## 8. ML vs Business Rules Comparison
Comparison against the existing deterministic Phase 4A BusinessRuleEngine:

- **ML ONLY (TRUE)**: {comp_results['comparison_stats'].get('ML_ONLY_TRUE', 0)} (ML caught this, BR missed it)
- **ML ONLY (FALSE)**: {comp_results['comparison_stats'].get('ML_ONLY_FALSE', 0)} (False Positive by ML)
- **BR ONLY**: {comp_results['comparison_stats'].get('BR_ONLY', 0)} (BR caught this, ML missed it)
- **BOTH DETECTED**: {comp_results['comparison_stats'].get('BOTH_DETECTED', 0)} (Both caught it)
- **BOTH MISSED**: {comp_results['comparison_stats'].get('BOTH_MISSED', 0)} (Neither caught the anomaly)

## 9. Final Interpretation
"""
    f1 = metrics['overall']['F1']
    if f1 > 0.8:
        md += "The Isolation Forest performed exceptionally well at isolating the synthetic defects entirely based on statistical distributions."
    elif f1 > 0.5:
        md += "The Isolation Forest successfully isolated a significant portion of defects, but struggled with specific categories that are hard to distinguish statistically without domain knowledge (rules)."
    else:
        md += "The Isolation Forest performed poorly. This highlights that many healthcare anomalies (like chronological errors) are difficult to detect via pure statistical distributions and are much better handled by deterministic business rules."

    with open(report_path, "w") as f:
        f.write(md)
        
    print(f"Report written to {report_path}")

if __name__ == "__main__":
    main()
