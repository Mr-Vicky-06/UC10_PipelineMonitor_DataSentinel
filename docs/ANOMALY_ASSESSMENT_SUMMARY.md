# Anomaly Assessment Summary

## 1. Objective
Implement the Anomaly Assessment and SLA Risk Preparation layers to consume the raw `anomaly_events.parquet` and convert them into business-actionable, structured impact assessments.

## 2. Assessment Methodology
The Anomaly Assessment Engine ingests the fused anomaly events, cross-references them with the operational feature matrix, and independently evaluates three distinct dimensions of the anomaly:
- **Severity**: Driven by the cumulative evidence score.
- **Confidence**: Inherited from the fusion engine based on signal convergence.
- **SLA Status**: Driven strictly by simulated operational metrics (throughput, backlog).

## 3. Severity Methodology
Severity is completely decoupled from SLA Status and Confidence. It is determined by the `evidence_score`:
- **LOW**: Score < 3 (e.g., single ML/Stat deviation)
- **MEDIUM**: 3 <= Score < 5 (e.g., single DQ violation)
- **HIGH**: 5 <= Score < 7 (e.g., DQ + MAD deviation)
- **CRITICAL**: Score >= 7 (e.g., DQ + MAD + IF combined failure)

## 4. Confidence Methodology
Confidence remains unchanged from the Evidence Fusion layer, categorizing how strongly independent signals align (`LOW`, `MEDIUM`, `HIGH`).

## 5. Impact Methodology
Impact analysis is strictly evidence-based. If a metric cannot be directly measured or confidently estimated, it is flagged as `NOT_AVAILABLE` (e.g., exact affected beneficiary IDs in aggregated volume metrics).
- **DQ Impact**: Uses `affected_records` from the DQ rule violation.
- **Volume Impact**: Heuristically captures the total claim/PDE volume for that day.

## 6. RCA Preparation
A `potential_contributing_factors` string is generated based on the active flags.
- **Rule-based**: Explicitly avoids definitive causal statements (e.g., "Root cause = X"). 
- **Phrasing**: Uses phrasing like "Upstream ingestion failure or missing batch delivery" or "Multivariate operational degradation".

## 7. SLA Methodology
SLA risk is assessed dynamically based on the current operational state:
- **ETA**: `remaining_workload` (backlog) / `throughput`
- **SLA Margin**: `deadline` - `ETA`
- **Zero Throughput**: Handled safely without `ZeroDivisionError`; forces an immediate `BREACH` status.

Status mapping:
- Margin < 0: `BREACH`
- Margin <= 30s: `AT_RISK`
- Margin > 30s: `MET`

## 8. Simulated Operational Assumptions
**Important**: The `throughput`, `backlog`, and `processing_duration` features used to calculate SLA Risk are SIMULATED operational inputs constructed during feature engineering for the purpose of this prototype. They do not represent actual CMS telemetry.

## 9. Controlled Test Results
The engine was validated against the 6 controlled mock scenarios. The decoupling was successfully proven:
- **Scenario 1-4 (DQ Errors)**: Severity=`MEDIUM`, Confidence=`MEDIUM`, SLA=`MET`.
- **Scenario 5 (Volume Drop)**: Severity=`LOW`, Confidence=`LOW`, SLA=`AT_RISK` (due to low throughput injection).
- **Scenario 6 (Multivariate Stall)**: Severity=`LOW`, Confidence=`LOW`, SLA=`BREACH` (due to 0 throughput injection).

## 10. Limitations
- Downstream impact on actual financial or SLA downstream deliverables is not calculable from the current dataset.
- Exact Affected Beneficiary identification requires mapping aggregate anomalies back to record-level timestamps, which is beyond the current pipeline state.

## 11. Next Phase
The Assessment Engine outputs `outputs/anomaly/anomaly_assessment.parquet`, preparing the pipeline for Phase 8: Autonomous Remediation / LLM RAG interface.
