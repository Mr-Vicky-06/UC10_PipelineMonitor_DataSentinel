# 02 Relationship & Grain Validation

## Grain Verification
- **Beneficiary**: 9660 rows, 9660 unique beneficiaries. (Grain: 1 row per beneficiary)
- **Inpatient Claims**: 58066 rows, 20867 unique claims. (Grain: 1 row per claim)
- **PDE Events**: 515520 rows, 515520 unique events. (Grain: 1 row per event)

## Relationship Verification (BENE_ID)
### Inpatient to Beneficiary
- MATCH RATE: 100.00%
- NON-MATCH / ORPHAN RATE: 0.00%
- DUPLICATE RELATIONSHIP RATE: 0.00% (Many-to-One relationship validated)

### PDE to Beneficiary
- MATCH RATE: 100.00%
- NON-MATCH / ORPHAN RATE: 0.00%
- DUPLICATE RELATIONSHIP RATE: 0.00% (Many-to-One relationship validated)

### Cross-Dataset (Inpatient <-> PDE)
- OVERLAP: 5098 beneficiaries have both inpatient claims and PDE events.
