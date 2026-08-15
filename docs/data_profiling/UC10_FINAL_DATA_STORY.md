# UC10 Final Data Story

## The Foundation
We begin with three core datasets representing a sample of CMS operations: a **Beneficiary** master table (one row per member), **FFS Claims** (line-level medical billing), and **PDE** (event-level pharmacy transactions). These datasets contain hundreds of columns and millions of rows, establishing a realistic foundation of healthcare data complexity.

## The Grain and Relationships
To analyze these datasets, we must understand their grain. A single hospital stay generates dozens of claim lines, whereas a pharmacy visit generates a single PDE event. By mapping both activity streams to the central Beneficiary table, we discover a strong intersection (over 85% overlap), justifying our ability to track holistic patient journeys and detect when one stream silently fails while the other continues.

## Quality and Temporal Behaviour
Upon initial inspection, the data exhibits clean referential integrity for core fields within this specific synthesized sample. Longitudinally, the data fluctuates significantly—claim volumes drop on weekends, creating high volatility. Standard deviation thresholds would trigger constant false alarms. Therefore, we understand that "normal" is volatile, and we must measure deviation against a Rolling Median (MAD) rather than a static average.

## Features: Bridging Data to Algorithms
We condense millions of rows into a daily feature matrix. We count volumes (`claim_count`, `pde_count`), calculate financial medians (`median_rx_cost`), and establish cross-dataset ratios (`claim_pde_ratio`). To simulate a production pipeline, we append mathematically proxy telemetry (`throughput`, `backlog`). This feature matrix is the lifeblood of our anomaly detection.

## The Tri-Level Detection Engine
Because anomalies manifest differently, we apply three distinct lenses:
1. **Data Quality Engine:** Catches explicit deterministic errors (nulls, duplicates, invalid dates).
2. **Statistical Engine (MAD):** Catches massive univariate spikes or drops in volume.
3. **Machine Learning Engine (Isolation Forest):** Catches subtle, multivariate degradation where no single metric crosses a hard threshold, but the combination of metrics is historically anomalous.

## Fusion to Action
These three detectors operate independently. When they fire, their signals are passed to the **Evidence Fusion** layer, which combines them into a single coherent Anomaly Event. The **Anomaly Assessment** engine determines Severity based on the aggregated evidence score and calculates SLA Risk based on simulated throughput. Finally, the **RAG Engine** attaches human-readable documentation and runbooks to the event.

The data journey is complete: from raw billions of lines to a single, actionable, documented insight.
