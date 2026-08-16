# Glossary

Define project-specific terminology consistently across the team.

- **System 1:** Representative Healthcare Pipeline. The operational data pipeline.
- **System 2:** DataSentinal Monitoring Layer. The AI-powered intelligence layer alongside the pipeline.
- **Master Data:** Validated simulation ecosystem used as pipeline input. Stored in `master_data/`.
- **Raw Data:** Original source datasets under `data/`. These are completely immutable.
- **Claim:** Healthcare claim entity, identified by `CLM_ID`.
- **Claim Line:** Individual line/revenue-center-level record. The grain at which claims are kept.
- **Authorization:** Healthcare service authorization, stored as a separate related dataset.
- **Telemetry:** Logs, metrics, and events describing pipeline execution.
- **Ground Truth:** Known injected scenario used to evaluate detection performance.
