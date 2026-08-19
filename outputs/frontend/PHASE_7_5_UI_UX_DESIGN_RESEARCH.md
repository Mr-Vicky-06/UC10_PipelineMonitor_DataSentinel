# PHASE 7.5 — UI/UX DESIGN RESEARCH AND VISUAL SYSTEM BLUEPRINT

## 1. CURRENT UI DIAGNOSIS

### A. Operations Center
**Diagnosis:** The current implementation (Checkpoint 4) successfully moved away from mock data, but still relies heavily on dense, generic metric cards (Card-based layout) and standard table views. The visual hierarchy places equal weight on active runs and incidents, causing cognitive load. The pipeline topology is functional but visually basic (color-coded nodes) and lacks depth regarding data flow or failure propagation.

### B. Pipeline Runs
**Diagnosis:** Tabular lists with basic status badges. While accurate, they fail to intuitively communicate *where* in the lifecycle a failure occurred or *why* without drilling down.

### C. Data Quality
**Diagnosis:** The "0 Violations" empty state is technically accurate (the `dq_results.parquet` is currently empty), but the visual representation is generic. A mature product should use empty states to reinforce system health (e.g., "All 452 rules passed") rather than just showing a void.

### D. ML Anomalies
**Diagnosis:** 
- **UNKNOWN / 0 observed / 0 expected issue:** This is **NOT** a UI rendering bug. It is an API adapter / schema mismatch. 
- The authoritative backend `anomaly_events.parquet` schema lacks `hospital_id`, `batch_id`, and `run_id` natively, resulting in hardcoded `"UNKNOWN"` mapping in `api/anomalies/route.ts`. 
- `expected` is hardcoded to `0` in the API adapter because the parquet only outputs `affected_records` (mapped to `observed`) and `evidence_score`.
- **Old timestamps:** The adapter maps `window_date` to `detected_at`. If the model was trained/executed on historical data (e.g., 2023), the UI calculates the distance from the current date (2026), resulting in "over 3 years ago".
- **Resolution:** The UI must stop trying to display fields that do not exist. We should display `Evidence Score` and `Affected Records` directly, rather than faking an `Expected` column.

### E. Incidents
**Diagnosis:** Integration with the FastAPI Alert Engine is sound. However, the UI lacks a coherent "Investigation Flow". Incidents are listed, but their relationship to Evidence, RCA, and SLA is not visually mapped. It requires manual traversal rather than guided root-cause analysis.

### F. Analytics
**Diagnosis:** The Analytics Workspace relies too heavily on live summary cards. It fails to differentiate between "Live Operational Telemetry" (which DataSentinel should own) and "Deep Historical Exploration" (which Grafana should own).

---

## 2. DESIGN GOALS
1. **Clinical & Precise:** The interface must feel like a mission-critical tool, not a generic SaaS dashboard.
2. **High-Trust:** 100% data provenance. No fake numbers, no hidden zeros.
3. **Calm by Default:** The normal state of the system should fade into the background. Color must be reserved exclusively for actionable states (Warning/Critical).
4. **Guided Investigation:** The architecture must enforce the operational flow: `Incident → Pipeline Stage → Anomaly Evidence → RCA`.

---

## 3. COMPETITIVE PATTERN RESEARCH
**Studied:** Datadog, Grafana, PagerDuty, Splunk, Cloudflare.
**Extracted Patterns:**
- **High Information Density:** Enterprise operators prefer dense tabular data over large, padded cards.
- **Sparklines over Bar Charts:** Inline time-series (sparklines) provide context without dominating screen real estate.
- **Split-Pane Architecture:** Master-detail views (list on left, details pane on right) prevent context-switching and page loads during active incident triage.
- **Semantic Badging:** Using distinct pill shapes for statuses and monospace fonts for IDs.

---

## 4. TYPOGRAPHY RECOMMENDATION

**Primary UI Font:** `Geist` (or `Inter` as fallback).
**Secondary / Monospace Font:** `Geist Mono` (or `JetBrains Mono`).

**Rationale:** `Geist` offers an extremely sharp, highly technical aesthetic tailored for modern development and data tools. It has excellent tabular numerals (critical for metrics and IDs) and its monospaced counterpart pairs perfectly, giving the application a precision-engineered feel.

---

## 5. COLOR SYSTEM RECOMMENDATION

**Theme Strategy:** Light-First. High contrast, low saturation.

- **Neutral Base:** `Slate` (Gray 50-900). Backgrounds are `Slate 50`, borders are `Slate 200`.
- **Primary Brand:** `Deep Clinical Blue` (#0f172a - Slate 900 for text, #2563eb - Blue 600 for interactive elements).
- **Semantic Statuses:**
  - **HEALTHY (Success):** Calm Emerald (#10b981) - Used sparingly. Normal is neutral.
  - **RUNNING (Active):** Indigo/Blue (#3b82f6) - Indicates activity, not necessarily health.
  - **WARNING (Degraded):** Amber (#f59e0b) - Requires attention, non-blocking.
  - **CRITICAL (Error):** Rose/Red (#e11d48) - High-contrast, blocking failure.
  - **STALE/UNKNOWN:** Slate (#64748b) with dashed borders.

*Accessibility:* All text-to-background contrast ratios must exceed 4.5:1 (WCAG AA).

---

## 6. LAYOUT & NAVIGATION RECOMMENDATION
Move away from a top-heavy layout. Adopt a **Left Sidebar** navigation model with a **Collapsible Secondary Pane** for deep dives.
- **Global Command Bar:** Provide a `Cmd+K` interface for jumping directly to Run IDs or Incident IDs.
- **Master-Detail View:** Clicking an incident opens a right-side drawer (the RCA / Evidence view) without leaving the Operations Center.

---

## 7. 2D vs 3D / THREE.JS RECOMMENDATION
**Recommendation:** Proceed with a highly optimized **2D SVG/Canvas approach** for standard topology, utilizing **React Flow** instead of Three.js.
**Rationale:** Three.js / React Three Fiber introduces significant overhead, accessibility challenges, and SSR complexities. While visually impressive, it rarely adds *operational* value in a data pipeline context unless modeling physical network geography. A high-performance, interactive 2D graph (React Flow) with animated SVG edges (particle flow for throughput) achieves the required "Live" feel while maintaining clinical precision, DOM accessibility, and enterprise maturity.

---

## 8. PIPELINE VISUALIZATION RECOMMENDATION
Implement a **Hybrid DAG Topology + Timeline**.
- **Macro View (Topology):** A Directed Acyclic Graph showing the dependencies (`INGEST → CLEAN → VALIDATE`, etc.). Edges animate based on throughput. Nodes change color based on status.
- **Micro View (Timeline):** Clicking a node opens a vertical execution timeline (e.g., standard GitHub Actions or Datadog trace view) showing exact millisecond durations and failure logs for that specific run stage.

---

## 9. LIVE EXPERIENCE DESIGN
- **Architecture:** Maintain **Short-Polling (5s)** for immediate implementation, with a planned upgrade to **WebSocket** for instant incident alerting.
- **UX Indicators:** 
  - `LIVE`: Green pulsing dot, "Last synced: 2s ago".
  - `STALE`: Amber dot, "Sync delayed (fetching...)".
  - `OFFLINE`: Red dot, dashed borders on metrics, explicit "System Disconnected" banner.
- Do not falsely market polling as "True WebSockets". Use precise terminology: "Aggressive Polling (5s)".

---

## 10. GRAFANA ARCHITECTURE STRATEGY
**DataSentinel Owns:** Live state, active incidents, current pipeline execution, guided RCA workflows.
**Grafana Owns:** Long-term trends, 30-day aggregations, deep time-series analysis.

**Integration:**
- Use **Embedded Grafana Panels** (`<iframe>` with Grafana's `&embed=true&theme=light`) within the DataSentinel Analytics Workspace for key historical sparklines.
- Provide contextual **"Deep Dive" Launchers** that open the full Grafana workspace in a new tab, synchronizing the time range via URL parameters (e.g., `&from=now-24h&to=now`).

---

## 11. ANALYTICS BLUEPRINT
The Analytics Workspace will be split:
1. **Pipeline Health:** Embedded Grafana panel showing throughput over the last 7 days.
2. **Data Quality Trends:** Embedded panel showing rule violation frequency.
3. **ML Anomalies:** Histogram of anomaly scores over time.
4. **SLA Adherence:** Burndown chart of SLA breaches.
*All tiles feature a clear "Launch in Grafana" button for unrestricted slice-and-dice.*

---

## 12. DESIGN TOKENS
```css
:root {
  --font-sans: 'Geist', 'Inter', sans-serif;
  --font-mono: 'Geist Mono', 'JetBrains Mono', monospace;
  
  --surface-canvas: #f8fafc;
  --surface-base: #ffffff;
  --surface-hover: #f1f5f9;
  
  --border-default: #e2e8f0;
  --border-focus: #94a3b8;
  
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-tertiary: #94a3b8;
  
  --status-healthy: #10b981;
  --status-running: #3b82f6;
  --status-warning: #f59e0b;
  --status-critical: #e11d48;
}
```

---

## 13. COMPONENT ARCHITECTURE
- `<AppShell>`: Main layout with left sidebar.
- `<TopologyGraph>`: React Flow-based DAG representation.
- `<IncidentDrawer>`: Sliding right pane for Master-Detail RCA investigation.
- `<GrafanaEmbed>`: Wrapper for secure Grafana iframe embedding.
- `<TelemetryBadge>`: Universal badge showing freshness and live state.

---

## 14. INTERACTION & MOTION STRATEGY
- **Hover:** Subtle background shifts (`bg-surface-hover`).
- **Drill-down:** Master-detail drawers. Clicking an incident *slides in* the Evidence/RCA pane, maintaining the surrounding context.
- **Motion:** Edges in the pipeline topology utilize subtle SVG stroke-dasharray animations to indicate data flow. No flashing elements for critical alerts; use persistent solid colors and stark contrast.

---

## 15. HALLMARK ANTI-PATTERN CHECKLIST (DO-NOT-DO LIST)
- [ ] No purple/pink "AI" gradients.
- [ ] No arbitrary 3D models of servers or data cubes.
- [ ] No giant, padded cards containing a single small number.
- [ ] No dark mode forced as default just to look "hacker-like".
- [ ] No mock/demo data generators.
- [ ] No hiding empty states behind fake 100% metrics.

---

## 16. INSTALLED SKILLS UTILIZATION
- `frontend-design`: Will guide the exact CSS token implementation.
- `hallmark`: Will audit the final PR for AI-dashboard clichés.
- `shadcn-ui`: Will provide the primitives (Tables, Drawers, Badges) styled cleanly.
- `accessibility-auditor`: Will run against the new semantic color palette.

---

## 17. IMPLEMENTATION SEQUENCE
1. **PHASE 7.6:** Design System & Token Implementation (`globals.css`, fonts, layout shell).
2. **PHASE 7.7:** Operations Center Rebuild (Move from cards to dense tables/split panes).
3. **PHASE 7.8:** Live Pipeline Topology (Integrate React Flow).
4. **PHASE 7.9:** Incident / RCA Master-Detail Drawer.
5. **PHASE 7.10:** Grafana Analytics Embedding.
