# 06 Evidence Fusion Design

Independent signals from Rules, Statistics, and ML must be combined without collapsing everything into an unexplained, arbitrary score.

## 1. Fusion Keys (Correlation)
All evidence must be joined on the following composite key:
- `dataset_id` (e.g., "PART_D_PRESCRIBER")
- `batch_id` (e.g., "2024_08_14_BATCH_01")
- `window_timestamp`

## 2. Event Payload Structure
An aggregated Anomaly Event preserves all independent signals:

```json
{
  "event_id": "EV-20260814-001",
  "dataset": "CMS_PART_D_PRESCRIBER",
  "batch_id": "BATCH_042",
  "timestamp": "2026-08-14T10:00:00Z",
  "severity_assessment": "HIGH",
  "confidence_assessment": "HIGH",
  "signals": {
    "data_quality": [
      {
        "rule_id": "DQ-002",
        "dimension": "Completeness",
        "field": "Prscrbr_NPI",
        "violation_count": 4500,
        "violation_rate": 0.08,
        "severity": "HIGH"
      }
    ],
    "statistical": [
      {
        "metric": "record_count",
        "observed_value": 45000,
        "expected_baseline": 62000,
        "deviation_pct": -27.4,
        "detector": "Rolling Median + MAD",
        "severity": "MEDIUM"
      }
    ],
    "multivariate_ml": {
      "detector": "Isolation Forest",
      "is_anomalous": true,
      "anomaly_score": -0.72,
      "contributing_features": ["processing_duration", "missing_rate_npi"]
    }
  },
  "sla_risk": "HIGH_RISK"
}
```

## 3. Severity & Confidence Logic

**Severity:** Driven by the HIGHEST severity of any active signal. (e.g., a fatal schema mismatch is always High Severity, even if ML doesn't flag it).
**Confidence:** Driven by signal AGREEMENT.
- High Confidence: DQ Rules trigger AND ML triggers AND Statistical deviation is present.
- Medium Confidence: Only ML triggers (operational anomaly) but DQ rules pass.
- Low Confidence: Borderline statistical deviation with no DQ violations and normal ML score.
