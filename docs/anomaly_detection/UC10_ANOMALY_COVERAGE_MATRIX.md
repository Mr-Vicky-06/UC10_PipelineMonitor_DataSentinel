# UC10 Anomaly Coverage Matrix

## 1. Objective
To map the 6 controlled mock scenarios to the exact analytical detectors and expected behaviours, ensuring no gaps in anomaly coverage.

## 2. Coverage Matrix

| Scenario | Required Evidence | Source Dataset | Primary Feature | Primary Detector | Expected Signal | Severity | Expected SLA Behaviour |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Missing Identifier** | Nulls in BENE_ID | Claims / PDE | `null_rate` | DQ Rule Engine | Violation Triggered | MEDIUM | MET |
| **2. Duplicate Records** | Duplicate PKs | Claims / PDE | `duplicate_rate` | DQ Rule Engine | Violation Triggered | MEDIUM | MET |
| **3. Invalid Date** | Future dates | Claims / PDE | `dq_violation_rate` | DQ Rule Engine | Violation Triggered | MEDIUM | MET |
| **4. Referential Integrity** | Orphan Claims/PDE | Claims / PDE | `cross_dataset_mismatch_rate` | DQ Rule / Stat MAD | Violation Triggered | MEDIUM | MET |
| **5. Volume Drop** | 40% Volume Loss | FFS Claims | `claim_count` | Statistical MAD | > 3.5 MAD Deviation | LOW / MEDIUM | AT_RISK (if throughput drops) |
| **6. Multivariate Degradation** | Latency + Small volume shift | Pipeline Meta | `processing_duration`, `throughput` | Isolation Forest | Anomaly Score > Threshold | LOW | BREACH (if throughput approaches 0) |

## 3. Gap Analysis
- **Current Real Dataset:** Cannot natively trigger SLA breaches or processing degradation without injection. 
- **Controlled Injection:** Successfully demonstrates the boundaries of each detector.
- **Missed Detections:** If the DQ Engine fails to catch referential integrity, the Statistical MAD engine serves as a fallback by detecting a sudden shift in the `claim_pde_ratio` or `cross_dataset_mismatch_rate`, ensuring redundant coverage.

**Conclusion:** The current mapping provides comprehensive, overlapping coverage for the target use case. No additional ML algorithms are required.
