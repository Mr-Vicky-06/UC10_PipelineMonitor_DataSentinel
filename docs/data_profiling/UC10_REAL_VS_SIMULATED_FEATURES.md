# UC10 Real vs. Simulated Features

## 1. Mandatory Separation

This pipeline explicitly combines actual data-derived metrics with simulated operational telemetry to demonstrate SLA integration. This document provides a strict separation to avoid misrepresenting simulated features as real CMS operational telemetry.

### A. Directly Data-Derived Features
These features are aggregated purely from the underlying CSV datasets.
- `claim_count`
- `pde_count`
- `unique_beneficiary_count`
- `unique_provider_count`
- `median_days_supply`
- `median_rx_cost`
- `median_claim_amount`

### B. Derived from Real Data
These are computed relationships or quality checks on the real data.
- `volume_change_pct`
- `claim_pde_ratio`
- `cross_dataset_mismatch_rate`
- `null_rate`
- `duplicate_rate`
- `dq_violation_rate`

### C. Simulated Operational Telemetry
These features are heavily simulated or injected mathematically. They **do not** reflect the actual performance of CMS infrastructure.

1. **`processing_duration`**
   - *How it is generated:* Injected noise based on volume using standard distributions.
   - *Production Metric Equivalent:* Airflow task duration or Spark job execution time.
   - *Limitation:* Does not account for true algorithmic complexity or shuffle read/write bottlenecks.

2. **`throughput`**
   - *How it is generated:* `volume / processing_duration`.
   - *Production Metric Equivalent:* Records processed per second.
   - *Limitation:* Assumes a perfectly linear relationship.

3. **`failure_rate`**
   - *How it is generated:* Simulated random errors.
   - *Production Metric Equivalent:* Percentage of retried tasks or dropped packets.
   - *Limitation:* Does not tie to specific bad records.

4. **`backlog`** (and subsequently `remaining_workload`, `ETA`, `SLA_margin`)
   - *How it is generated:* Rolling accumulation of processed vs expected volume.
   - *Production Metric Equivalent:* Kafka lag or pending queue depth.
   - *Limitation:* Purely mathematical proxy for a real queueing system.

## 2. Conclusion
The pipeline successfully uses proxy simulated metrics to build the Anomaly Assessment and SLA Risk engines. In production, Category C features must be replaced with direct API calls to Dataproc/Airflow/Kafka telemetry.
