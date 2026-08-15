# 00 Cleanup Manifest

This manifest documents the exact rationale for archiving or deleting files within the UC10 workspace.

### 1. `ChatGPT Image Aug 14, 2026, 01_23_24 PM.png`
- **Why it is unnecessary**: This is an extraneous screenshot that is not referenced by any project documentation, code, or datasets.
- **Is another copy available**: Unknown, but irrelevant to the pipeline.
- **Reproducible**: No.
- **Referenced by code**: No.
- **Required by documentation**: No.
- **Impact on finalized architecture**: None.
- **Action**: **PERMANENT DELETE**

### 2. `scratch/` Directory (and all contents)
- **Why it is unnecessary**: Contains previous python profile/generation scripts (`inventory_new.py`, `generate_markdowns.py`) and intermediate JSON profiles generated during the architecture comparison phase.
- **Is another copy available**: The outputs are already finalized and stored as markdown in `data analysis/`.
- **Reproducible**: Yes, the data is just profiled metadata.
- **Referenced by code**: No active pipeline code references this.
- **Required by documentation**: No.
- **Impact on finalized architecture**: None.
- **Action**: **ARCHIVE** (Move to `archive/scratch/`)

### 3. `data analysis/` Directory
- **Why it is unnecessary**: Not unnecessary, but misplaced. These are the finalized analytical documents justifying Architecture A.
- **Is another copy available**: No.
- **Reproducible**: Yes, but represents finalized decisions.
- **Referenced by code**: No.
- **Required by documentation**: Yes, critical for RAG and architectural justification.
- **Impact on finalized architecture**: Supports the design decisions.
- **Action**: **KEEP / REORGANIZE** (Move to `docs/architecture_analysis/`)

### 4. `DataBase/` Structure
- **Why it is unnecessary**: The folder name and flat structure do not support a production pipeline structure.
- **Action**: The actual source data will not be deleted, but the directory will be restructured into `data/raw/`, `data/supporting/`, and `data/optional/` respectively. No datasets will be permanently deleted.
