# DataSentinal / UC10 Project Rules

## Non-Negotiable Project Constraints

1. **IMMUTABLE RAW DATA:** The directory `D:\UC10_Data_Quality_Pipeline\data\` is COMPLETELY IMMUTABLE. 
   - Antigravity may READ from it.
   - Antigravity MUST NOT WRITE to it.
   - Never modify, delete, rename, move, overwrite, append, clean, inject, or transform anything under `data\`.
2. **Master Data Repository:** The master data source of truth is located exclusively in `D:\UC10_Data_Quality_Pipeline\master_data\`.
3. **Architecture Respect:** Do not silently perform large architectural changes. Agents must consult `DECISIONS.md` before proposing changes that affect existing architecture.
4. **Phase Boundaries:** Stop at requested phase boundaries. Do not silently move to another phase or claim future phases are completed. The current authoritative phase is listed in `CURRENT_STATE.md`.
5. **No Blind Tech Adoption:** A technology must have a demonstrated architectural purpose (refer to `TECHNOLOGY_STACK.md`). Do NOT introduce Kubernetes, Firebase, or another technology merely because it is available.
6. **Protocol:** Every agent must follow: WHAT, WHY, INPUT, DESIGN, COMMAND, EXPECTED RESULT, EXECUTE, RESULT, INTERPRETATION, NEXT STEP. Explain planned work before implementation so developers can understand and learn.
7. **Verification:** Validate your changes. Report exactly what changed, what tests were performed, and any known limitations. Avoid modifying unrelated components.
