# 08 Anomaly Demonstration Plan

This plan details controlled synthetic anomaly injections to demonstrate the UC10 hybrid architecture.

| Scenario | Target | Injected Modification | Expected Detector | Expected RCA |
|---|---|---|---|---|
| Null Keys | `pde_events` | Set `BENE_ID` to NULL for 50 records | DQ Rules (Completeness) | Ingestion script stripped IDs. |
| Ref. Integrity | `pde_events` | Mutate `BENE_ID` to non-existent 'XXXX' | DQ Rules (Ref. Integrity) | System mismatch. |
| Volume Drop | Pipeline | Only ingest 10% of standard batch volume | Statistical (Median+MAD) | Upstream system outage. |
| Multivariate Ops | Pipeline | Inflate `duration_ms` + drop `volume` | Isolation Forest | API throttling / DB locks. |
| Cross-Dataset | `claims_ffs` / `pde_events` | Generate PDE events for deceased BENE_ID | IF / Complex Rules | Data sync delay across silos. |
