# UC10 CANONICAL DATA KNOWLEDGE GUIDE VALIDATION

## 1. Source Documents Used
This canonical guide was generated using strictly the following authoritative audit documents:
1. `UC10_FINAL_DATA_INVENTORY.md`
2. `UC10_FINAL_RELATIONSHIP_ANALYSIS.md`
3. `UC10_FINAL_DATA_STORY.md`
4. `UC10_FINAL_FEATURE_CONTRACT.md`
5. `FINAL_ML_FEATURE_SET.md`
6. `feature_engineering_summary.md`
7. `UC10_REAL_VS_SIMULATED_FEATURES.md`
8. `UC10_TEMPORAL_BEHAVIOUR_AUDIT.md`
9. `UC10_ANOMALY_COVERAGE_MATRIX.md`

No external healthcare assumptions or unverified metrics were introduced into the final guide.

## 2. Final Dataset Facts Verified
- **Beneficiary:** 5,975 rows, 123 columns. Grain: 1 row per beneficiary.
- **FFS Claims:** 1,121,004 rows, 96 columns. 90,705 unique claims across 7,971 unique beneficiaries. Grain: claim-line.
- **PDE:** 515,520 rows, 36 columns. 515,520 unique events across 7,403 unique beneficiaries. Grain: event.

*All values match the `UC10_FINAL_DATA_INVENTORY.md` strictly.*

## 3. Final Feature Count
Exactly **18 features** have been documented in Section 6.
These match the 4 Data Aspects: Data Quality, Healthcare Volume/Behaviour, Distribution, and Operational Telemetry.

## 4. Detector Mapping Validation
The feature-to-detector mappings strictly reflect the `UC10_FINAL_FEATURE_CONTRACT.md` and `UC10_ANOMALY_COVERAGE_MATRIX.md`.
- **DQ Rules:** Handled by DQ metrics (`null_rate`, `duplicate_rate`, etc.).
- **Rolling MAD:** Handled by single-metric shifts (`claim_count`, `volume_change_pct`, `median_rx_cost`, etc.).
- **Isolation Forest:** Handled by multivariate relationships (operational metrics, `claim_pde_ratio`, unique provider/beneficiary counts).

## 5. Real vs Simulated Validation
The document explicitly splits real data (claim/PDE behavior) from simulated data (processing_duration, throughput, backlog, failure_rate) in Section 9. No simulated SLA telemetry is misrepresented as actual raw CMS data.

## 6. Discrepancies Found & Handled
- **Discrepancy:** The previous guide claimed "perfect referential integrity" and "hundreds of millions of records."
- **Resolution:** These claims were completely removed. The canonical guide explicitly acknowledges the orphan records (2,436 unique beneficiaries in Claims and 2,018 in PDE not in the master list) and explains how they are actively used as DQ evidence via the `cross_dataset_mismatch_rate` feature, rather than treating them as pipeline errors to be dropped.

## 7. Diagram and Rendering Confirmation
- All diagrams use correct `mermaid` syntax with `graph TD`.
- Quotes were explicitly added around node texts containing spaces or HTML breaks to prevent Mermaid version 11.16+ syntax errors.
- Visual inspection confirms all graphics, feature cards, tables, and workflow architectures render successfully in both Markdown and PDF formats.

## 8. PDF Visual Inspection
- **Output:** `outputs/docs/UC10_CANONICAL_DATA_KNOWLEDGE_GUIDE.pdf`
- **Pages:** 10 pages
- **Format:** Clean A4 layout, continuous flow, no raw ASCII text, no floating orphan headers, high-quality vector diagrams.

**STATUS:** The Canonical Data Knowledge Guide is visually and factually sound and is **READY FOR TEAM USE**.
