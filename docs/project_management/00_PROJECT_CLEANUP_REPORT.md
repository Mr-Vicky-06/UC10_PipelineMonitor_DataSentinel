# 00 Project Cleanup Report

| File/Folder | Type | Size | Purpose | Required? | Action |
|---|---|---:|---|---|---|
| `DataBase/Beneficiary/` | Directory | 46.5 MB | CMS Synthetic Beneficiary Files (2015-2025) | YES (Core) | MOVE to `data/raw/beneficiary/` |
| `DataBase/Claims/` | Directory | 871 MB | CMS Synthetic Claims (Inpatient, Outpatient, etc.) | YES (Core) | MOVE to `data/raw/claims/` |
| `DataBase/pde.csv` | File | 90.9 MB | CMS Synthetic PDE | YES (Core) | MOVE to `data/raw/pde/` |
| `DataBase/Medicare Part D Prescribers.../` | Directory | 4.05 GB | Real Provider/Drug Aggregate (Arch B) | OPTIONAL | MOVE to `data/optional/provider_drug/` |
| `DataBase/puf/` | Directory | 53.9 MB | Real Healthcare.gov PUFs | OPTIONAL | MOVE to `data/supporting/puf/` |
| `data analysis/` | Directory | ~40 KB | Previous Dataset Architecture Analysis Outputs | YES (Docs) | MOVE to `docs/architecture_analysis/` |
| `scratch/` | Directory | ~250 KB | Intermediate python scripts & JSON profiles | NO | ARCHIVE to `archive/scratch/` |
| `02_UC10_ANOMALY_FRAMEWORK.md` | Doc | 10.4 KB | Project Knowledge Base | YES (RAG) | MOVE to `docs/` |
| `03_UC10_RAG_SCOPE.md` | Doc | 13.0 KB | Project Knowledge Base | YES (RAG) | MOVE to `docs/` |
| `UC10_Literature_Review_1.md` | Doc | 44.9 KB | Project Knowledge Base | YES (RAG) | MOVE to `docs/` |
| `UC10_Literature_Review_Matrix.xlsx` | Doc | 24.0 KB | Project Knowledge Base | YES (RAG) | MOVE to `docs/` |
| `ChatGPT Image Aug 14, 2026...png` | Image | 1.6 MB | Extraneous Image | NO | SAFE TO REMOVE |
