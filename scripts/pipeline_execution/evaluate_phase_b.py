import sys
import json
from datetime import datetime
import time
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Add src to python path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.transformation import HealthcareTransformer
from src.business_rules.engine import BusinessRuleEngine
from src.business_rules.rules import (
    ClaimChronologyRule,
    AdmissionDischargeRule,
    NegativeAmountRule,
    PaymentChargeBalanceRule
)

def evaluate():
    out_dir = Path("outputs/business_rules/evaluation/phase_b")
    
    start_time = time.time()
    
    # 1. Load Data
    df_eval = pd.read_csv(out_dir / "synthetic_phase_b_dataset.csv", sep="|", dtype=str)
    df_gt = pd.read_csv(out_dir / "ground_truth.csv")
    
    # 2. Run Pipeline
    t_start_trans = time.time()
    transformer = HealthcareTransformer()
    transformed_batch = transformer.transform_claims(df_eval, source_file="synthetic.csv")
    t_end_trans = time.time()
    
    t_start_bre = time.time()
    rules = [
        ClaimChronologyRule(),
        AdmissionDischargeRule(),
        NegativeAmountRule(),
        PaymentChargeBalanceRule()
    ]
    engine = BusinessRuleEngine(rules)
    result = engine.execute(transformed_batch)
    t_end_bre = time.time()
    
    # 3. Process Results
    # Convert violations list into a lookup: clm_id -> rule_id -> status
    eval_lookup = defaultdict(dict)
    for v in result.violations:
        eval_lookup[v.clm_id][v.rule_id] = v.status
        
    rule_map = {
        "BR-DATE-001": "expected_BR_DATE_001",
        "BR-DATE-002": "expected_BR_DATE_002",
        "BR-AMT-001": "expected_BR_AMT_001",
        "BR-AMT-002": "expected_BR_AMT_002"
    }
    
    metrics = {
        "BR-DATE-001": {"TP": 0, "TN": 0, "FP": 0, "FN": 0},
        "BR-DATE-002": {"TP": 0, "TN": 0, "FP": 0, "FN": 0},
        "BR-AMT-001": {"TP": 0, "TN": 0, "FP": 0, "FN": 0},
        "BR-AMT-002": {"TP": 0, "TN": 0, "FP": 0, "FN": 0},
        "overall": {
            "total_records": len(df_eval),
            "expected_violations": 0,
            "detected_violations": 0,
            "missed_violations": 0,
            "false_positives": 0
        }
    }
    
    # 4. Compare with Ground Truth
    for _, row in df_gt.iterrows():
        clm_id = row['CLM_ID']
        actual_statuses = eval_lookup.get(clm_id, {})
        
        for rule_id, gt_col in rule_map.items():
            expected = row[gt_col]
            actual = actual_statuses.get(rule_id, "PASS") # default to PASS if no violation record
            
            # Map ACTUAL status. Our engine outputs FAIL, NOT_EVALUATED.
            if actual == "FAIL":
                is_actual_fail = True
            else:
                is_actual_fail = False
                
            is_expected_fail = (expected == "EXPECTED_FAIL")
            
            if is_expected_fail:
                metrics["overall"]["expected_violations"] += 1
                
            if is_expected_fail and is_actual_fail:
                metrics[rule_id]["TP"] += 1
                metrics["overall"]["detected_violations"] += 1
            elif not is_expected_fail and not is_actual_fail:
                metrics[rule_id]["TN"] += 1
            elif is_expected_fail and not is_actual_fail:
                metrics[rule_id]["FN"] += 1
                metrics["overall"]["missed_violations"] += 1
                print(f"FN for {clm_id} on {rule_id}")
            elif not is_expected_fail and is_actual_fail:
                metrics[rule_id]["FP"] += 1
                metrics["overall"]["false_positives"] += 1
                print(f"FP for {clm_id} on {rule_id}")

    # Compute Precision, Recall, F1
    for rule_id in rule_map.keys():
        tp = metrics[rule_id]["TP"]
        fp = metrics[rule_id]["FP"]
        fn = metrics[rule_id]["FN"]
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics[rule_id]["Precision"] = precision
        metrics[rule_id]["Recall"] = recall
        metrics[rule_id]["F1"] = f1

    # -------------------------------------------------------------------------
    # BOUNDARY DATASET
    # -------------------------------------------------------------------------
    df_bound = pd.read_csv(out_dir / "synthetic_boundary_dataset.csv", sep="|", dtype=str)
    df_gt_bound = pd.read_csv(out_dir / "ground_truth_boundary.csv")
    
    transformed_bound = transformer.transform_claims(df_bound, source_file="bound.csv")
    result_bound = engine.execute(transformed_bound)
    
    bound_lookup = defaultdict(dict)
    for v in result_bound.violations:
        bound_lookup[v.clm_id][v.rule_id] = v.status
        
    bound_metrics = {"total": len(df_bound), "correct": 0, "incorrect": 0}
    
    for _, row in df_gt_bound.iterrows():
        clm_id = row['CLM_ID']
        actual_statuses = bound_lookup.get(clm_id, {})
        is_correct = True
        for rule_id, gt_col in rule_map.items():
            expected = row[gt_col] # PASS or NOT_EVALUATED
            actual = actual_statuses.get(rule_id, "PASS")
            if actual != expected:
                is_correct = False
                print(f"Boundary mismatch {clm_id} on {rule_id}: Expected {expected}, Actual {actual}")
        if is_correct:
            bound_metrics["correct"] += 1
        else:
            bound_metrics["incorrect"] += 1

    end_time = time.time()
    
    report = {
        "execution_timestamp": datetime.utcnow().isoformat() + "Z",
        "performance": {
            "transformation_time_sec": round(t_end_trans - t_start_trans, 4),
            "engine_time_sec": round(t_end_bre - t_start_bre, 4),
            "total_time_sec": round(end_time - start_time, 4),
            "records_per_second": round(1000 / (end_time - start_time), 2)
        },
        "metrics": metrics,
        "boundary_metrics": bound_metrics
    }
    
    with open(out_dir / "evaluation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Evaluation Complete. Results saved.")

if __name__ == "__main__":
    evaluate()
