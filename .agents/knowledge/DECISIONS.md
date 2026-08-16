# Project Decisions Log

This document records important architectural decisions. Agents must consult `DECISIONS.md` before proposing changes that affect existing architecture.

- **Decision:** RAG is knowledge assistance, not cross-dataset validation.
- **Decision:** Raw data is immutable. The `data/` directory must never be modified.
- **Decision:** Master data lives outside `data/` in `master_data/`.
- **Decision:** Claims remain at claim-line grain.
- **Decision:** Authorization remains a separate related dataset.
- **Decision:** Pipeline and DataSentinal are separate system responsibilities.
- **Decision:** Hybrid detection is used (Rules + Statistics + ML).
- **Decision:** Docker is used for reproducibility.
- **Decision:** Cloud-native technologies are introduced only when justified.
