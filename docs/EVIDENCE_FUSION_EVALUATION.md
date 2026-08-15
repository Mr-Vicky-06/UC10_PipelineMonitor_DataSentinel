# Evidence Fusion Evaluation

## Controlled Testing Results
The fusion engine was evaluated against the 6 controlled anomaly scenarios. The outputs successfully align with the architectural design, keeping the evidence score explainable and distinct from both confidence and severity.

| Scenario | DQ | MAD | IF | Fusion Result | Confidence | Evidence Score |
|---|---:|---:|---:|---|---|---|
| Missing ID | ✓ | | | `DATA_QUALITY` | `MEDIUM` | 3 |
| Duplicate | ✓ | | | `DATA_QUALITY` | `MEDIUM` | 3 |
| Invalid Date | ✓ | | | `DATA_QUALITY` | `MEDIUM` | 3 |
| Referential Failure | ✓ | | | `DATA_QUALITY` | `MEDIUM` | 3 |
| Volume Drop | | ✓ | | `VOLUME_ANOMALY` | `LOW` | 2 |
| Multivariate Anomaly| | | ✓ | `MULTIVARIATE_ANOMALY` | `LOW` | 2 |
| Combined Failure | ✓ | ✓ | ✓ | `COMBINED_ANOMALY` | `HIGH` | 7 |

## Interpretation
- The detectors remain entirely independent. There is no forced agreement.
- Single-signal ML or Statistical deviations yield `LOW` confidence because they represent behavioral shifts that might be natural (e.g. holidays).
- Single-signal DQ violations yield `MEDIUM` confidence because they are explicit logical errors.
- Any combination of multiple signals (e.g., DQ + MAD) elevates the confidence to `HIGH`.
- The `Evidence Score` is an explainable integer sum, explicitly avoiding the term "probability".
