import pandas as pd
import time
import json
from pathlib import Path
from src.business_rules.models import RuleStatus
from src.business_rules.phase_c_rules import ICDValidityRule, HCPCSValidityRule, BeneficiaryIntegrityRule, ProviderIntegrityRule, AuthorizationMatchRule
# Also bring in Phase B rules to run them
from src.business_rules.rules import ClaimChronologyRule, AdmissionDischargeRule, NegativeAmountRule, PaymentChargeBalanceRule

def run_evaluation():
    dataset_path = "outputs/business_rules/evaluation/phase_c/synthetic_phase_c_dataset.csv"
    gt_path = "outputs/business_rules/evaluation/phase_c/ground_truth.csv"
    
    df = pd.read_csv(dataset_path, sep="|", dtype=str)
    df_gt = pd.read_csv(gt_path, dtype=str).set_index("CLM_ID")
    
    rules = [
        # Phase C
        ICDValidityRule(),
        HCPCSValidityRule(),
        BeneficiaryIntegrityRule(),
        ProviderIntegrityRule(),
        AuthorizationMatchRule(),
        # Phase B
        ClaimChronologyRule(),
        AdmissionDischargeRule(),
        NegativeAmountRule(),
        PaymentChargeBalanceRule()
    ]
    
    start = time.time()
    
    # Run all rules
    all_violations = []
    for r in rules:
        all_violations.extend(r.evaluate(df))
        
    duration = time.time() - start
    
    # Process results per rule per claim
    # Map rule_id -> claim_id -> status
    results_map = {r.rule_id: {} for r in rules}
    # Initialize all to PASS
    for r in rules:
        for clm in df['CLM_ID']:
            results_map[r.rule_id][clm] = RuleStatus.PASS.value
            
    # Then overwrite with actual violations
    for v in all_violations:
        # A rule might emit multiple violations for a claim, we keep the most severe/first.
        # But actually for Authorization, it might emit NO_AUTHORIZATION or AMBIGUOUS_AUTH.
        # For our GT, we just map it.
        # Ensure we don't overwrite a CRITICAL with an INFO for example, though usually only 1 is emitted.
        results_map[v.rule_id][v.clm_id] = v.status
        
    metrics = {}
    
    for r_id in ['BR-REF-001', 'BR-REF-002', 'BR-REF-003', 'BR-REF-004', 'BR-AUTH-001']:
        r_name = r_id.replace('-', '_')
        gt_col = f"expected_{r_name}"
        
        tp, tn, fp, fn = 0, 0, 0, 0
        scenario_counts = {}
        
        for clm_id, gt_row in df_gt.iterrows():
            expected = gt_row[gt_col]
            actual = results_map[r_id].get(clm_id, "PASS")
            scenario = gt_row["scenario"]
            
            if scenario not in scenario_counts:
                scenario_counts[scenario] = {"total": 0, "correct": 0}
            
            scenario_counts[scenario]["total"] += 1
            if actual == expected:
                scenario_counts[scenario]["correct"] += 1
                
            # Binary classification (Pass vs Any Violation/Non-Pass)
            # wait, AUTHORIZED and PASS are the "negative" class (clean).
            # FAIL, NO_AUTH, EXPIRED, AMBIGUOUS are the "positive" class (anomaly).
            def is_anomaly(s):
                return s not in ["PASS", "AUTHORIZED", "NOT_EVALUATED"]
                
            exp_anom = is_anomaly(expected)
            act_anom = is_anomaly(actual)
            
            if exp_anom and act_anom: tp += 1
            elif not exp_anom and not act_anom: tn += 1
            elif not exp_anom and act_anom: fp += 1
            elif exp_anom and not act_anom: fn += 1
            
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0
        
        metrics[r_id] = {
            "TP": tp, "TN": tn, "FP": fp, "FN": fn,
            "Precision": precision,
            "Recall": recall,
            "F1": f1,
            "Scenarios": scenario_counts
        }
        
    # Check Phase B rules regression: should all be PASS or NOT_EVALUATED
    phase_b_passed = True
    for r_id in ['BR-DATE-001', 'BR-DATE-002', 'BR-AMT-001', 'BR-AMT-002']:
        for clm_id in df['CLM_ID']:
            st = results_map[r_id].get(clm_id, "PASS")
            if st == "FAIL":
                phase_b_passed = False
                break
                
    report = {
        "execution_time_seconds": duration,
        "records_per_second": len(df) / duration if duration > 0 else 0,
        "phase_b_regression_passed": phase_b_passed,
        "metrics": metrics
    }
    
    with open("outputs/business_rules/evaluation/phase_c/evaluation_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print("Evaluation completed. Check outputs/business_rules/evaluation/phase_c/evaluation_report.json")
    
if __name__ == "__main__":
    run_evaluation()
