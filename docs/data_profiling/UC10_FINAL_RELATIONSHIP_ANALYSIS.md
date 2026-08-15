# UC10 Final Relationship Analysis

## 1. Grain Constraints
- **Beneficiary:** Expected 1 row per BENE_ID. Verified: 5,975 rows = 5,975 unique BENE_IDs.
- **FFS Claims:** Expected 1 row per claim line. Verified: 1.12M rows map to 90k claims, averaging ~12 lines per claim.
- **PDE:** Expected 1 row per event. Verified: 515,520 rows = 515,520 unique PDE_IDs.

Why grain matters: Aggregating volume metrics without addressing grain causes massive distortion. A single inpatient claim creates dozens of lines; treating each line as an independent pipeline event artificially inflates throughput variance.

## 2. Cross-Dataset Beneficiary Relationships
- **Total Beneficiaries in Master Table:** 5,975
- **Beneficiaries in Claims Table:** 7,971
- **Beneficiaries in PDE Table:** 7,403
- **Intersection (Claims + PDE):** 6,850
- **Claims-only Beneficiaries:** 1,121
- **PDE-only Beneficiaries:** 553

## 3. Referential Integrity Violations (Orphans)
- **Orphan Claims:** 2,436 unique beneficiaries in the Claims data do NOT exist in the Beneficiary master table.
- **Orphan PDE:** 2,018 unique beneficiaries in the PDE data do NOT exist in the Beneficiary master table.

**Implication:** If the pipeline enforces strict referential integrity (dropping orphans), it will lose roughly 25-30% of its volume. This confirms that the data is a generated/synthetic sample without enforced referential constraints.

## 4. Activity Density
- **Claims per Beneficiary:** ~140 claim lines per beneficiary.
- **PDE Events per Beneficiary:** ~69 prescription events per beneficiary.

## 5. Conclusion
There is a strong relationship between Claims and PDE (6,850 intersecting beneficiaries), which justifies cross-dataset features like `claim_pde_ratio`. However, the high volume of orphan records must be explicitly handled by Data Quality (DQ) rules rather than silently dropped, to generate meaningful anomaly events.
