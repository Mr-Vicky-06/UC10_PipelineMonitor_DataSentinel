# 09 Dataset Analysis Executive Summary

**1. What datasets do we actually have?**
We have CMS Medicare Part D Prescribers (Provider+Drug grain, ~3.78GB) and Healthcare.gov PUF files (Plan Attributes, Crosswalk, Service Area). *The CMS Synthetic Medicare Claims dataset is absent.*

**2. What does each row represent?**
- Part D: Annual aggregate of one provider prescribing one drug.
- Plan Attributes: One health plan variant in a specific state.
- Crosswalk: County-level mapping of a 2025 plan to a 2026 plan.
There are NO individual patient/claim records.

**3. What are the strongest fields?**
Provider NPI, Drug names, Plan IDs, Service Area IDs, and numeric aggregates (Claims, Cost, Days Supply).

**4. What are the valid identifiers?**
Composite keys are required. (e.g., NPI + Brand Name + Generic Name for Part D).

**5. What DQ anomalies can we detect?**
Completeness (nulls), Schema validity (data types), Uniqueness (duplicates on composite keys), and Referential Integrity (Crosswalk to Plan Attributes).

**6. What statistical anomalies can we detect?**
By simulating batches, we can detect volume shifts, missing rate spikes, and numeric distribution shifts (e.g., median total claims).

**7. What Isolation Forest features can we build?**
We can build batch-level features combining DQ metrics (missing rate) with simulated pipeline metrics (throughput, backlog, processing duration).

**8. What cross-dataset validations are valid?**
Only within the PUF family (Crosswalk -> Plan Attributes -> Service Area).

**9. What cannot be validated?**
We cannot validate Part D against PUF data (they cover different populations/domains and share no keys). We cannot validate claim-level schema (as synthetic claims are missing).

**10. What telemetry must be simulated?**
All operational pipeline telemetry (duration, throughput, retries, failures, SLA deadlines) must be simulated, as these are static public files.

**11. What can support RCA?**
Deterministic DQ rule outputs can localize errors to a specific column and stage (e.g., Schema validation stage).

**12. What can support impact analysis?**
We can quantify the number of affected rows and flag downstream tables (e.g., broken Crosswalk limits enrollment in 2026 plans).

**13. What can support SLA prediction?**
Simulated processing rates vs remaining workload. 

**14. What can RAG explain?**
RAG can retrieve official dataset definitions (e.g., "What does Tot_30day_Fills mean?"), DQ rule definitions, and documented remediation playbooks.

**15. What are the dataset limitations?**
They are static, annual aggregates. They lack real pipeline timestamps. The Part D data contains suppressed values (`*`, `#`) for privacy, which must be handled explicitly rather than treated as simple nulls.

**16. Is the current dataset collection sufficient for MVP?**
**YELLOW (Supported with simulation).** The datasets are sufficient to prove the *architecture* (Rules + Stats + ML + RAG), provided we chunk the data into simulated batches and generate our own pipeline telemetry. 

**17. What additional data, if any, is genuinely necessary?**
If the project explicitly requires demonstrating *individual claim-level* validation (rather than aggregated provider metrics or plan attributes), the **CMS Synthetic Medicare Claims (DE-SynPUF)** dataset MUST be acquired. 

**18. What should we implement first?**
1. A pipeline harness to stream/chunk the Part D data to simulate time-series batches.
2. Deterministic DQ Rules (Completeness, Validity) using Great Expectations/Soda equivalents.
3. The baseline statistical calculation (Rolling Median + MAD) on record volumes.
