# Statistical Detection Audit

## Temporal Validation
- Earliest Window: 2015-01-01
- Latest Window: 2022-12-31
- Total Windows: 2,922
- Frequency: Daily. No duplicates. No gaps.

## Zero-MAD Policy
If a historical baseline is perfectly flat (`MAD = 0`):
- Non-deviations (`current_value == median`) are safely scored as `robust_z = 0.0`.
- Deviations (`current_value != median`) are forced to trigger the threshold as an explicit "distribution shift".

## Cold Start Policy
The first `window` observations (default: 7) are tagged with `severity = 'INSUFFICIENT_HISTORY'` and excluded from anomaly flags.
