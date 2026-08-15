# PROJECT PROTOTYPE OPERATIONAL RUNBOOKS

## VOLUME ANOMALY RUNBOOK

**Target Anomaly Types:** VOLUME_ANOMALY
**Owner:** Data Engineering / Operations Team

### Overview
This runbook applies when statistical deviations (e.g., Rolling Median + MAD) detect a significant drop or spike in record volume. 

### Expected Impact
Volume drops usually indicate upstream processing delays, missing files, or truncated extracts. This often translates to an SLA Risk if the pipeline throughput drops to zero or near-zero, increasing ETA.

### Recommended Remediation Steps
1. **Source Verification:** Check if the upstream provider has completed their daily delivery. 
2. **Infrastructure Health:** Verify that cluster resources are scaling correctly. A volume stall may be caused by out-of-memory errors on Spark workers.
3. **Threshold Review:** If the volume change is expected (e.g., a holiday), mark the anomaly as 'EXPECTED' and adjust the statistical baseline.
4. **Trigger Retry:** If the issue was an infrastructure glitch, trigger a re-run of the ingestion task.
