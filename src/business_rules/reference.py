import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Set, Dict, List, Tuple

class ReferenceDataManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if not self._initialized:
            self._load_data()
            self._initialized = True
            
    def _load_data(self):
        ref_dir = Path("outputs/reference_data")
        auth_path = Path("master_data/authorization/authorization_linked.csv")
        
        # 1. ICD Reference
        if (ref_dir / "synthetic_icd_reference.csv").exists():
            df_icd = pd.read_csv(ref_dir / "synthetic_icd_reference.csv", dtype=str)
            self.icds = set(df_icd['ICD_CODE'].dropna())
        else:
            self.icds = set()
            
        # 2. HCPCS Reference
        if (ref_dir / "synthetic_hcpcs_reference.csv").exists():
            df_hcpcs = pd.read_csv(ref_dir / "synthetic_hcpcs_reference.csv", dtype=str)
            self.hcpcs = set(df_hcpcs['HCPCS_CD'].dropna())
        else:
            self.hcpcs = set()
            
        # 3. Beneficiary Reference
        if (ref_dir / "synthetic_beneficiary_reference.csv").exists():
            df_bene = pd.read_csv(ref_dir / "synthetic_beneficiary_reference.csv", dtype=str)
            self.benes = set(df_bene['BENE_ID'].dropna())
        else:
            self.benes = set()
            
        # 4. Provider Reference
        if (ref_dir / "synthetic_provider_reference.csv").exists():
            df_prov = pd.read_csv(ref_dir / "synthetic_provider_reference.csv", dtype=str)
            self.providers = set(df_prov['PRVDR_NUM'].dropna())
        else:
            self.providers = set()
            
        # 5. Authorization Reference
        self.auth_dict = defaultdict(list)
        if auth_path.exists():
            df_auth = pd.read_csv(auth_path, dtype=str)
            # Map BENE_ID + HCPCS_CD -> List of auth records
            for _, row in df_auth.iterrows():
                key = (row['BENE_ID'], row['HCPCS_CD'])
                self.auth_dict[key].append(row.to_dict())
                
    def get_icds(self) -> Set[str]:
        return self.icds
        
    def get_hcpcs(self) -> Set[str]:
        return self.hcpcs
        
    def get_benes(self) -> Set[str]:
        return self.benes
        
    def get_providers(self) -> Set[str]:
        return self.providers
        
    def get_auth_candidates(self, bene_id: str, hcpcs_cd: str) -> List[Dict]:
        return self.auth_dict.get((bene_id, hcpcs_cd), [])

