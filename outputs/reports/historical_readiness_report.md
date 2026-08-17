# Historical Readiness Report & Validation

## 1. Historical Data Readiness Gate
- **Pipeline Runs**: 56
- **Batches**: 46
- **Hospitals**: 11
- **Service Dates**: 5
- **Time Span**: 2026-08-17 10:04:11.358025 to 2026-08-17 12:45:48.465698
- **Metrics Observations**: 0
- **Observations per feature**: {}
- **Missing Features (Data Gaps)**: `pde_count`, `claim_pde_ratio`, `median_rx_cost`, `median_days_supply`, `backlog`
- **Minimum Observations Required for ML**: 1,000+ over 30+ days
- **Training Readiness Status**: INSUFFICIENT HISTORICAL DATA

## 2. ML Detector Status
- **VolumeDetector**: BLOCKED — INSUFFICIENT HISTORICAL DATA
- **DistributionDetector**: BLOCKED — INSUFFICIENT HISTORICAL DATA
- **OperationalDetector**: BLOCKED — INSUFFICIENT HISTORICAL DATA

## 3. Real Data Validation (DQ Detector)
- **Total rule_results evaluated**: 690
- **Violations detected (status != PASSED)**: 690
- **AnomalyEvents generated**: 690
- **AnomalyEvents persisted to DB**: 690
- **Reconciliation**: PASS

## 4. Source Immutability Check
- `master_data` SHA256 Before: f5a011d5dbb3da03c1d60864f91c1dc01f3d4641f29b13c481fb9d6977b961e6
- `master_data` SHA256 After: f5a011d5dbb3da03c1d60864f91c1dc01f3d4641f29b13c481fb9d6977b961e6
- `data/` SHA256 Before: 4085f4ee4519c9dcee8c124d127f9feb7062053a103a94f72d7a576a4b3031e6
- `data/` SHA256 After: 4085f4ee4519c9dcee8c124d127f9feb7062053a103a94f72d7a576a4b3031e6
- **Immutability Status**: PASS
