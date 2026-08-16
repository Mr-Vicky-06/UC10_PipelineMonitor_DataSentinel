# Master Data Source of Truth

## IMMUTABILITY RULE
**IMPORTANT: The entire directory `D:\UC10_Data_Quality_Pipeline\data\` is IMMUTABLE.**

- Antigravity may READ from it.
- Antigravity MUST NOT WRITE to it.
- Never modify, delete, rename, move, overwrite, append, clean, inject, or transform in place anything under `data\`.

## Master Data Ecosystem
The current completed master-data ecosystem is located at:
`D:\UC10_Data_Quality_Pipeline\master_data\`

### Ecosystem Statistics
The ecosystem was successfully generated and contains approximately:
- 100,000 claim lines
- 30,193 claims
- 29,085 beneficiaries
- 5 providers
- 5 hospitals
- 1,137 daily batches
- 21,801 linked authorization records
- Authorization ground-truth scenarios

### Known Limitations
**Synthetic Beneficiary Continuity:** Synthetic beneficiary continuity is limited compared with real longitudinal healthcare populations. 
*Do not silently "fix" this limitation.*
