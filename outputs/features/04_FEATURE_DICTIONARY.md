# 04 Feature Dictionary

| Feature | Source | Formula | Grain | Type | Purpose | Detector |
|---|---|---|---|---|---|---|
| pde_count | PDE | COUNT(*) | Daily | Numeric | Volume monitoring | Statistical / IF |
| claim_count | Claims | COUNT(*) | Daily | Numeric | Volume monitoring | Statistical / IF |
| unique_beneficiary_count | PDE | COUNT(DISTINCT BENE_ID) | Daily | Numeric | Beneficiary coverage | Statistical |
| duplicate_rate | PDE | 1 - (Distinct IDs / Total) | Daily | Numeric | Data Quality | DQ Rules |
| claim_pde_ratio | Claims+PDE | claim / pde | Daily | Numeric | Relationship drift | IF |
| processing_duration | Simulated | Derived from volume | Daily | Numeric | Pipeline health | SLA |
