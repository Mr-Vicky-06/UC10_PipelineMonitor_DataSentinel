from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd
import numpy as np

from .models import BusinessRuleViolation, RuleStatus, RuleSeverity

class BusinessRule(ABC):
    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        """Evaluates the rule against the dataframe and returns a list of violations."""
        pass

    def _create_violation(self, row: pd.Series, status: RuleStatus, message: str, field_values: Dict[str, Any], severity: RuleSeverity = RuleSeverity.ERROR) -> BusinessRuleViolation:
        return BusinessRuleViolation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            clm_id=str(row.get('CLM_ID', '')),
            clm_line_num=str(row.get('CLM_LINE_NUM', '')),
            severity=severity.value,
            status=status.value,
            message=message,
            field_values=field_values
        )

class ClaimChronologyRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-DATE-001"

    @property
    def rule_name(self) -> str:
        return "Claim Chronology Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        if 'CLM_FROM_DT' not in df.columns or 'CLM_THRU_DT' not in df.columns:
            # If completely missing, all rows are NOT_EVALUATED
            for _, row in df.iterrows():
                violations.append(self._create_violation(
                    row, RuleStatus.NOT_EVALUATED, "Required date columns missing from dataset", {}
                ))
            return violations

        # Vectorized check
        s_from = pd.to_datetime(df['CLM_FROM_DT'], errors='coerce')
        s_thru = pd.to_datetime(df['CLM_THRU_DT'], errors='coerce')

        missing_mask = s_from.isna() | s_thru.isna()
        fail_mask = (~missing_mask) & (s_from > s_thru)

        for idx in df[missing_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.NOT_EVALUATED, "Required date missing or unparseable",
                {"CLM_FROM_DT": row['CLM_FROM_DT'], "CLM_THRU_DT": row['CLM_THRU_DT']},
                RuleSeverity.INFO
            ))

        for idx in df[fail_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.FAIL, "CLM_FROM_DT occurs after CLM_THRU_DT",
                {"CLM_FROM_DT": row['CLM_FROM_DT'], "CLM_THRU_DT": row['CLM_THRU_DT']},
                RuleSeverity.ERROR
            ))
            
        return violations

class AdmissionDischargeRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-DATE-002"

    @property
    def rule_name(self) -> str:
        return "Admission Discharge Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        
        # Canonicalization
        admit_col = 'ADMTN_DT'
        if 'CLM_ADMSN_DT' in df.columns:
            admit_col = 'CLM_ADMSN_DT'
        
        discharge_col = 'NCH_BENE_DSCHRG_DT'
        
        if admit_col not in df.columns or discharge_col not in df.columns:
            # Not all claims have these (e.g. outpatient). 
            # If the columns don't exist, we can't evaluate.
            for _, row in df.iterrows():
                violations.append(self._create_violation(
                    row, RuleStatus.NOT_EVALUATED, f"Required date columns missing ({admit_col}, {discharge_col})", {}
                ))
            return violations

        s_admit = pd.to_datetime(df[admit_col], errors='coerce')
        s_disch = pd.to_datetime(df[discharge_col], errors='coerce')

        # For rows where both are present
        both_present = (~s_admit.isna()) & (~s_disch.isna())
        missing_mask = s_admit.isna() | s_disch.isna()
        fail_mask = both_present & (s_admit > s_disch)

        for idx in df[missing_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.NOT_EVALUATED, "Required date missing or unparseable for admission bounds",
                {"admission_date": row[admit_col], "discharge_date": row[discharge_col]},
                RuleSeverity.INFO
            ))

        for idx in df[fail_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.FAIL, "Admission date occurs after Discharge date",
                {"admission_date": row[admit_col], "discharge_date": row[discharge_col]},
                RuleSeverity.ERROR
            ))

        return violations

class NegativeAmountRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-AMT-001"

    @property
    def rule_name(self) -> str:
        return "Negative Amount Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        cols_to_check = []
        if 'CLM_PMT_AMT' in df.columns:
            cols_to_check.append('CLM_PMT_AMT')
        if 'CLM_TOT_CHRG_AMT' in df.columns:
            cols_to_check.append('CLM_TOT_CHRG_AMT')

        if not cols_to_check:
            for _, row in df.iterrows():
                violations.append(self._create_violation(
                    row, RuleStatus.NOT_EVALUATED, "No financial amount columns found", {}
                ))
            return violations

        for col in cols_to_check:
            s_val = pd.to_numeric(df[col], errors='coerce')
            missing_mask = s_val.isna()
            fail_mask = (~missing_mask) & (s_val < 0)

            for idx in df[missing_mask].index:
                row = df.loc[idx]
                violations.append(self._create_violation(
                    row, RuleStatus.NOT_EVALUATED, f"{col} missing or non-numeric",
                    {col: row[col]},
                    RuleSeverity.INFO
                ))

            for idx in df[fail_mask].index:
                row = df.loc[idx]
                violations.append(self._create_violation(
                    row, RuleStatus.FAIL, f"{col} cannot be negative",
                    {col: row[col]},
                    RuleSeverity.ERROR
                ))

        return violations

class PaymentChargeBalanceRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-AMT-002"

    @property
    def rule_name(self) -> str:
        return "Payment Charge Balance Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        if 'CLM_PMT_AMT' not in df.columns or 'CLM_TOT_CHRG_AMT' not in df.columns:
            for _, row in df.iterrows():
                violations.append(self._create_violation(
                    row, RuleStatus.NOT_EVALUATED, "Required amount columns missing", {}
                ))
            return violations

        s_pmt = pd.to_numeric(df['CLM_PMT_AMT'], errors='coerce')
        s_chrg = pd.to_numeric(df['CLM_TOT_CHRG_AMT'], errors='coerce')

        missing_mask = s_pmt.isna() | s_chrg.isna()
        fail_mask = (~missing_mask) & (s_pmt > s_chrg)

        for idx in df[missing_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.NOT_EVALUATED, "Payment or Charge amount missing",
                {"CLM_PMT_AMT": row['CLM_PMT_AMT'], "CLM_TOT_CHRG_AMT": row['CLM_TOT_CHRG_AMT']},
                RuleSeverity.INFO
            ))

        for idx in df[fail_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.FAIL, "Payment amount is strictly greater than Total Charge amount",
                {"CLM_PMT_AMT": row['CLM_PMT_AMT'], "CLM_TOT_CHRG_AMT": row['CLM_TOT_CHRG_AMT']},
                RuleSeverity.ERROR
            ))

        return violations
