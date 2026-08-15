# UC10 Final Data Inventory

## 1. Beneficiary Dataset
- **Location:** `data/raw/beneficiary/*.csv`
- **File Format:** Pipe-separated (`|`) CSV
- **Row Count:** 5,975
- **Column Count:** 123
- **Dataset Grain:** One row per unique beneficiary.
- **Primary Key:** `BENE_ID`
- **Missingness:** High missingness in conditional fields (e.g., `BENE_DEATH_DT` is 100% null as expected for living population in sample; `STATE_CNTY_FIPS_CD` fields vary).
- **Duplicate Characteristics:** 0 duplicates on `BENE_ID`.

## 2. FFS Claims Dataset
- **Location:** `data/raw/claims/*.csv` (carrier, dme, hha, hospice, inpatient, outpatient, snf)
- **File Format:** Comma-separated CSV
- **Row Count:** 1,121,004
- **Column Count:** 96
- **Dataset Grain:** Claim-line level.
- **Business Key:** `CLM_ID` + `CLM_LINE_NUM` (for carrier/outpatient lines).
- **Foreign Keys:** `BENE_ID`
- **Unique Entities:** 90,705 unique claims (`CLM_ID`); 7,971 unique beneficiaries.
- **Missingness:** `CLM_FROM_DT` is 100% null across the combined read. Secondary date fields or `NCH_WKLY_PROC_DT` must be relied upon. High missingness in secondary diagnostic codes (e.g., `ICD_DGNS_CD10`).
- **Duplicate Characteristics:** The dataset contains 1.1M rows mapping to 90k claims, heavily multiplexed by line number.

## 3. PDE (Prescription Drug Events) Dataset
- **Location:** `data/raw/pde/pde.csv`
- **File Format:** Comma-separated CSV
- **Row Count:** 515,520
- **Column Count:** 36
- **Dataset Grain:** Prescription-event level.
- **Primary Key:** `PDE_ID`
- **Foreign Keys:** `BENE_ID`
- **Unique Entities:** 515,520 unique PDE events; 7,403 unique beneficiaries.
- **Missingness:** `SRVC_DT` is complete (0 nulls). Minimal missingness overall.
- **Duplicate Characteristics:** 0 duplicates on `PDE_ID`.

## Conclusion
The data inventory confirms that the provided files support a multi-domain view of beneficiary activity, requiring explicit aggregation from line-level (Claims) and event-level (PDE) to daily pipeline windows.
