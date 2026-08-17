import pandas as pd
from typing import List, Dict, Any
from src.business_rules.models import BusinessRuleViolation, RuleStatus, RuleSeverity
from src.business_rules.rules import BusinessRule
from src.business_rules.reference import ReferenceDataManager

class ICDValidityRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-REF-001"

    @property
    def rule_name(self) -> str:
        return "ICD Validity Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        ref_manager = ReferenceDataManager()
        valid_icds = ref_manager.get_icds()

        icd_cols = [c for c in df.columns if c in ['PRNCPAL_DGNS_CD', 'ADMTG_DGNS_CD'] or c.startswith('ICD_DGNS_CD') or c.startswith('ICD_PRCDR_CD') or c.startswith('ICD_DGNS_E_CD')]
        
        if not icd_cols:
            return violations

        for idx, row in df.iterrows():
            diag_values = [str(row[c]) for c in icd_cols if pd.notna(row[c]) and str(row[c]).strip() != ""]
            
            if not diag_values:
                violations.append(self._create_violation(
                    row, RuleStatus.NOT_EVALUATED, "No diagnosis codes found on claim", {}, RuleSeverity.INFO
                ))
                continue
            
            invalid_codes = [code for code in diag_values if code not in valid_icds]
            if invalid_codes:
                violations.append(self._create_violation(
                    row, RuleStatus.FAIL, f"Invalid ICD codes found: {','.join(invalid_codes)}",
                    {"invalid_icds": invalid_codes}, RuleSeverity.ERROR
                ))
            
        return violations

class HCPCSValidityRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-REF-002"

    @property
    def rule_name(self) -> str:
        return "HCPCS Validity Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        if 'HCPCS_CD' not in df.columns:
            return violations
            
        ref_manager = ReferenceDataManager()
        valid_hcpcs = ref_manager.get_hcpcs()
        
        missing_mask = df['HCPCS_CD'].isna() | (df['HCPCS_CD'].astype(str).str.strip() == "")
        for idx in df[missing_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.NOT_EVALUATED, "HCPCS_CD missing", {}, RuleSeverity.INFO
            ))

        valid_mask = (~missing_mask)
        for idx in df[valid_mask].index:
            row = df.loc[idx]
            code = str(row['HCPCS_CD']).strip()
            if code not in valid_hcpcs:
                violations.append(self._create_violation(
                    row, RuleStatus.FAIL, f"Unknown HCPCS code: {code}", {"HCPCS_CD": code}, RuleSeverity.ERROR
                ))
                
        return violations

class BeneficiaryIntegrityRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-REF-003"

    @property
    def rule_name(self) -> str:
        return "Beneficiary Referential Integrity Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        if 'BENE_ID' not in df.columns:
            return violations
            
        ref_manager = ReferenceDataManager()
        valid_benes = ref_manager.get_benes()
        
        missing_mask = df['BENE_ID'].isna() | (df['BENE_ID'].astype(str).str.strip() == "")
        for idx in df[missing_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.NOT_EVALUATED, "BENE_ID missing", {}, RuleSeverity.INFO
            ))

        valid_mask = (~missing_mask)
        for idx in df[valid_mask].index:
            row = df.loc[idx]
            code = str(row['BENE_ID']).strip()
            if code not in valid_benes:
                violations.append(self._create_violation(
                    row, RuleStatus.FAIL, f"Unknown Beneficiary ID: {code}", {"BENE_ID": code}, RuleSeverity.ERROR
                ))
                
        return violations

class ProviderIntegrityRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-REF-004"

    @property
    def rule_name(self) -> str:
        return "Provider Referential Integrity Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        if 'PRVDR_NUM' not in df.columns:
            return violations
            
        ref_manager = ReferenceDataManager()
        valid_providers = ref_manager.get_providers()
        
        missing_mask = df['PRVDR_NUM'].isna() | (df['PRVDR_NUM'].astype(str).str.strip() == "")
        for idx in df[missing_mask].index:
            row = df.loc[idx]
            violations.append(self._create_violation(
                row, RuleStatus.NOT_EVALUATED, "PRVDR_NUM missing", {}, RuleSeverity.INFO
            ))

        valid_mask = (~missing_mask)
        for idx in df[valid_mask].index:
            row = df.loc[idx]
            code = str(row['PRVDR_NUM']).strip()
            if code not in valid_providers:
                violations.append(self._create_violation(
                    row, RuleStatus.FAIL, f"Unknown Provider Number: {code}", {"PRVDR_NUM": code}, RuleSeverity.ERROR
                ))
                
        return violations

class AuthorizationMatchRule(BusinessRule):
    @property
    def rule_id(self) -> str:
        return "BR-AUTH-001"

    @property
    def rule_name(self) -> str:
        return "Authorization Match Rule"

    def evaluate(self, df: pd.DataFrame) -> List[BusinessRuleViolation]:
        violations = []
        if 'BENE_ID' not in df.columns or 'HCPCS_CD' not in df.columns or 'CLM_FROM_DT' not in df.columns:
            for _, row in df.iterrows():
                violations.append(self._create_violation(
                    row, RuleStatus.NOT_EVALUATED, "Required columns missing for auth match", {}, RuleSeverity.INFO
                ))
            return violations
            
        ref_manager = ReferenceDataManager()
        
        s_date = pd.to_datetime(df['CLM_FROM_DT'], errors='coerce')
        
        for idx, row in df.iterrows():
            bene_id = str(row['BENE_ID']).strip()
            hcpcs_cd = str(row['HCPCS_CD']).strip()
            clm_dt = s_date[idx]
            
            if pd.isna(clm_dt) or not bene_id or not hcpcs_cd or bene_id == "nan" or hcpcs_cd == "nan":
                violations.append(self._create_violation(
                    row, RuleStatus.NOT_EVALUATED, "BENE_ID, HCPCS_CD or CLM_FROM_DT is missing", {}, RuleSeverity.INFO
                ))
                continue
                
            candidates = ref_manager.get_auth_candidates(bene_id, hcpcs_cd)
            
            if not candidates:
                violations.append(self._create_violation(
                    row, RuleStatus.NO_AUTHORIZATION, "No authorization candidates found", {"BENE_ID": bene_id, "HCPCS_CD": hcpcs_cd}, RuleSeverity.ERROR
                ))
                continue
                
            valid_by_date = []
            for c in candidates:
                eff = pd.to_datetime(c.get('AUTH_EFF_DT'), format='%Y%m%d', errors='coerce')
                exp = pd.to_datetime(c.get('AUTH_EXP_DT'), format='%Y%m%d', errors='coerce')
                
                if pd.notna(eff) and pd.notna(exp) and (eff <= clm_dt <= exp):
                    valid_by_date.append(c)
                    
            if not valid_by_date:
                # If there are candidates but none cover the date, return EXPIRED_AUTHORIZATION
                violations.append(self._create_violation(
                    row, RuleStatus.EXPIRED_AUTHORIZATION, "Authorization candidates exist but none cover the service date", {"BENE_ID": bene_id, "HCPCS_CD": hcpcs_cd}, RuleSeverity.ERROR
                ))
                continue
                
            valid_by_status = [c for c in valid_by_date if c.get('AUTH_STATUS_CD') == 'APPROVED']
            
            if not valid_by_status:
                violations.append(self._create_violation(
                    row, RuleStatus.INVALID_STATUS, "Date-valid candidates exist but none are APPROVED", {}, RuleSeverity.ERROR
                ))
                continue
                
            if len(valid_by_status) == 1:
                violations.append(self._create_violation(
                    row, RuleStatus.AUTHORIZED, "Successfully matched valid authorization", 
                    {"AUTH_ID": valid_by_status[0].get('AUTH_ID')}, RuleSeverity.INFO
                ))
            else:
                auth_ids = [c.get('AUTH_ID') for c in valid_by_status]
                violations.append(self._create_violation(
                    row, RuleStatus.AMBIGUOUS_AUTH, "Multiple date-valid APPROVED authorizations found", 
                    {"candidate_auth_ids": auth_ids}, RuleSeverity.CRITICAL
                ))

        return violations
