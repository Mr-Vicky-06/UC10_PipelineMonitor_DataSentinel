# Evidence Fusion Summary

## 1. Objective
Build an explainable Evidence Fusion layer that aggregates the independent outputs of the Rule-Based DQ Detector, Rolling Median (MAD), and Isolation Forest into structured anomaly events.

## 2. Alignment Methodology
- **Temporal Backbone**: Outputs from all three detectors are aligned based on their window execution date (`window_date`).
- **Clean Baseline**: The original clean baseline outputs are untouched. Because the clean baseline contains 0 DQ violations, DQ evidence is correctly excluded from the clean baseline fusion runs.

## 3. Evidence Model
The fusion layer applies a simple, explainable additive scoring model (configured in `configs/anomaly_config.yaml`). We explicitly do not average probabilities.
- DQ Violation: `+3`
- Statistical Anomaly: `+2`
- Isolation Forest Anomaly: `+2`
- Threshold for event generation: `>= 2`

## 4. Confidence & Severity Policy
- **Evidence Score**: Represents the raw sum of independent signals.
- **Confidence**: Categorical interpretation of the evidence. 
  - `LOW` = 1 ML/Stat signal (Score 2)
  - `MEDIUM` = 1 DQ signal (Score 3) or 2 ML/Stat signals (Score 4)
  - `HIGH` = Combined DQ + ML/Stat signals (Score 5+)
- **Severity**: Kept entirely separate. Anomaly events currently hold a `PENDING_SLA` severity flag because true severity depends on downstream impact (SLA Risk).

## 5. Controlled Test Results
A mock testing framework verified that missing IDs, duplicate rows, referential failures, volume drops, and multivariate performance degradation generate the exact expected Anomaly Types (`DATA_QUALITY`, `VOLUME_ANOMALY`, `MULTIVARIATE_ANOMALY`) and primary evidence pointers.

## 6. RCA Preparation & SLA Handoff
- A human-readable `explanation` string is generated for each event, explicitly stating "Potential contributing factors require RCA" to avoid premature causal claims.
- Structured RCA evidence is separated into `outputs/anomaly/rca_evidence.parquet` for downstream consumption by an LLM or analyst.
- SLA risk assessment remains decoupled and will occur in the next phase.

## 7. Next Phase
Proceed to **Phase 7: Anomaly Assessment & SLA Risk** to evaluate the impact of these structured anomaly events on pipeline deliverables.
