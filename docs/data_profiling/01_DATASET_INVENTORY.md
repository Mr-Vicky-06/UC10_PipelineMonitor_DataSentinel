# 01 Dataset Inventory

This inventory was constructed by scanning the `DataBase` directory, inspecting schemas, and profiling column overlaps.

## Datasets

| Filename | Dataset Family | Rows | Grain / One Row Represents | Identifiers |
|---|---|---|---|---|
| `beneficiary_20*.csv` | CMS Synthetic | ~9,660+ | One Beneficiary | `BENE_ID` |
| `inpatient.csv` | CMS Synthetic FFS | 58,066 | One Inpatient Claim | `CLM_ID`, `BENE_ID` |
| `outpatient.csv` | CMS Synthetic FFS | ~200,000 | One Outpatient Claim | `CLM_ID`, `BENE_ID` |
| `carrier.csv` | CMS Synthetic FFS | ~1,121,000| One Carrier Claim | `CLM_ID`, `BENE_ID` |
| `pde.csv` | CMS Synthetic PDE | ~1,000,000| One Prescription Event (PDE) | `PDE_ID`, `BENE_ID` |
| `MUP_DPR_RY26...csv` | CMS Part D | 28M+ | One Provider + Drug Aggregate | `Prscrbr_NPI`, `Brnd_Name` |

**Note on Synthetic vs Public Use Data:**
The Beneficiary, Claims, and PDE files belong to the CMS Synthetic dataset. The `MUP_DPR` file is a real CMS Public Use File (PUF). 
