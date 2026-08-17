import pandas as pd
from src.business_rules.rules import (
    ClaimChronologyRule, 
    AdmissionDischargeRule, 
    NegativeAmountRule, 
    PaymentChargeBalanceRule
)

class BusinessRuleComparator:
    def __init__(self):
        self.rules = [
            ClaimChronologyRule(), 
            AdmissionDischargeRule(), 
            NegativeAmountRule(), 
            PaymentChargeBalanceRule()
        ]
        
    def evaluate(self, df_adv: pd.DataFrame, df_gt: pd.DataFrame, df_pred: pd.DataFrame) -> dict:
        """
        Runs existing business rules and compares with ML.
        """
        # Run business rules
        all_violations = []
        for rule in self.rules:
            violations = rule.evaluate(df_adv)
            all_violations.extend(violations)
            
        # Find which records failed BRs
        # Violation clm_id and clm_line_num mapped to record_id or index
        # We assume df_adv index matches df_gt and df_pred
        br_failed_indices = set()
        for v in all_violations:
            if v.status == "FAIL":
                # Find matching record in df_adv
                mask = (df_adv['CLM_ID'].astype(str) == v.clm_id) & (df_adv['CLM_LINE_NUM'].astype(str) == v.clm_line_num)
                br_failed_indices.update(df_adv[mask].index.tolist())
                
        # Compare
        results = []
        for idx in df_gt.index:
            gt_is_anomaly = df_gt.loc[idx, 'ground_truth_anomaly'] == 1
            ml_is_anomaly = df_pred.loc[idx, 'prediction'] == 1
            br_is_anomaly = idx in br_failed_indices
            
            cat = df_gt.loc[idx, 'anomaly_category']
            
            if ml_is_anomaly and br_is_anomaly:
                outcome = "BOTH_DETECTED"
            elif ml_is_anomaly and not br_is_anomaly:
                if gt_is_anomaly:
                    outcome = "ML_ONLY_TRUE"
                else:
                    outcome = "ML_ONLY_FALSE"
            elif not ml_is_anomaly and br_is_anomaly:
                outcome = "BR_ONLY"
            elif not ml_is_anomaly and not br_is_anomaly:
                if gt_is_anomaly:
                    outcome = "BOTH_MISSED"
                else:
                    outcome = "BOTH_CORRECTLY_NORMAL"
            else:
                outcome = "UNKNOWN"
                
            results.append({
                'record_id': df_gt.loc[idx, 'record_id'],
                'category': cat,
                'ground_truth': int(gt_is_anomaly),
                'ml_prediction': int(ml_is_anomaly),
                'br_prediction': int(br_is_anomaly),
                'outcome': outcome
            })
            
        df_results = pd.DataFrame(results)
        
        comparison_stats = df_results['outcome'].value_counts().to_dict()
        
        return {
            'comparison_stats': comparison_stats,
            'detailed_results': df_results
        }
