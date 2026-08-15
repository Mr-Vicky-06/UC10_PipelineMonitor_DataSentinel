# Anomaly Injection Plan

Because the public datasets do not provide complete, labelled pipeline incidents, we must simulate them. This document outlines the controlled anomaly scenarios to be injected into the test pipeline.

## 1. Data Quality Injections

| Scenario ID | Injection Type | Target | Original Value | Modified Value | Expected Detector | Expected Severity |
|---|---|---|---|---|---|---|
| `DQ-INJ-001` | Missing Required | `Prscrbr_NPI` | Valid NPI | NULL | Rules (Completeness) | HIGH |
| `DQ-INJ-002` | Invalid Code | `StateCode` | "AK" | "XX" | Rules (Validity) | HIGH |
| `DQ-INJ-003` | Broken Reference | `PlanID_2026` | Valid ID | "99999XX9999999" | Rules (Ref. Integrity) | HIGH |
| `DQ-INJ-004` | Negative Value | `Tot_Drug_Cst`| 1500.00 | -1500.00 | Rules (Validity) | HIGH |

## 2. Statistical Injections

| Scenario ID | Injection Type | Target | Expected Detector | Expected Severity |
|---|---|---|---|---|
| `STAT-INJ-001` | Volume Drop | Drop 40% of records in simulated batch 5 | Median + MAD (Volume) | HIGH |
| `STAT-INJ-002` | Distribution Spike | Multiply `Tot_Clms` by 10x for 10% of rows | Median + MAD (Claims) | MEDIUM |

## 3. Multivariate (Isolation Forest) Injections

| Scenario ID | Injection Type | Target / Combination | Expected Detector | Expected Severity |
|---|---|---|---|---|
| `ML-INJ-001` | Operational Slowdown | `volume` +10%, `duration` +200%, `failures` +2% | Isolation Forest | MEDIUM |
| `ML-INJ-002` | API Degradation | `retry_rate` +15%, `backlog` +50% | Isolation Forest | MEDIUM |

## 4. SLA Risk Injections

| Scenario ID | Injection Type | Target | Expected Detector | Expected Severity |
|---|---|---|---|---|
| `SLA-INJ-001` | Throughput Collapse | Hardcode throughput to 10 rec/sec while 50K records remain | SLA Engine | BREACH_RISK |
| `SLA-INJ-002` | Late Arrival | Simulate batch arriving with only 10% of SLA window remaining | SLA Engine | HIGH_RISK |
