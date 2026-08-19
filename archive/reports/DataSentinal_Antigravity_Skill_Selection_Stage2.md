# DataSentinal — Antigravity Skill Selection (Stage 2: Filter → Compare → Verify → Rank → Select)

This builds directly on the prior research report (`DataSentinal_Antigravity_Skills_Research.md`). No new broad search was run; every citation below points back to a section of that report. Where evidence from stage 1 is thin, that's called out explicitly rather than papered over. Nothing has been installed — this is still a decision document.

---

## STEP 1 — Filter

Applying the ten filter questions to every stage-1 candidate collapsed the original ~30-skill list to the candidates that survive below. Cut for cause, not by default:

- **`python-pro`** — cut: redundant with `data-engineer`, which already covers the Python surface DataSentinal needs.
- **`data-scientist`** — cut: weaker and more generic than `ml-engineer`; provides nothing `ml-engineer` doesn't already cover.
- **`spark-optimization`, `airflow-dag-patterns`** — cut: no distributed-systems or DAG-scheduling problem exists yet at the project's current single-machine DuckDB/Pandas scale.
- **`dbt-transformation-patterns`** — cut: narrower subset of what `data-engineer` + `data-quality-frameworks` already cover together.
- **`observability-engineer`, `performance-engineer`** — cut for NOW: DataDog/New Relic/CloudWatch-heavy, paid-tool-oriented, and instrument a *live running service* that doesn't exist yet (your own telemetry is currently simulated, per the UC10 technical guide).
- **`kpi-dashboard-design`, `dashboard-designer`** — cut: redundant with / weaker than `developing-with-streamlit`, the one officially-maintained option.
- **`k8s-manifest-generator`, `kubernetes-architect`, `helm-chart-scaffolding`, CI/CD pipeline skills** — cut: wrong scale for a project that isn't deployed anywhere yet.
- **`analyze-project`** — cut: analyzes AI-pair-programming session logs, not data-pipeline incidents. Wrong entity entirely.
- **`graphify`** — cut: graphs source code (imports/calls/classes), not data lineage or pipeline dependencies. Wrong entity entirely.
- **`agent-orchestrator` / multi-agent skills** — cut: DataSentinal's architecture is a linear pipeline, not a multi-agent negotiation system. Nothing to orchestrate.
- **`langchain-architecture`** — cut: conceptual-only, no runnable scaffold; `rag-implementation` provides the same conceptual grounding plus actual code.
- **`postmortem-writing`** — cut: narrower subset of `incident-responder`.

What survives the filter: **`data-engineer`, `data-quality-frameworks`, `phase-gated-debugging`/`debugger`, `ml-engineer` (conditionally, see Component 5), `rag-implementation`, `developing-with-streamlit`, `grafana/skills`, `docker-expert`, `incident-responder`**, plus the QA/testing bundle entries (`systematic-debugging`, `test-driven-development`) surfaced incidentally in stage 1.

---

## STEP 2 & 3 — Best Skill Per Component, With Proof

### COMPONENT: Representative Healthcare / Insurance Pipeline
**BEST SKILL:** `data-engineer`
**ALTERNATIVES CONSIDERED:** `python-pro`, `airflow-dag-patterns`, `dbt-transformation-patterns`
**WHY THIS SKILL WINS:** It's the only candidate whose own content already enumerates the specific stage sequence your pipeline needs — custom Python/pandas/Polars processing, Great-Expectations-aware validation, cloud/local ETL — in one skill, without forcing in an orchestrator (Airflow) or transform framework (dbt) you don't yet run.
**EVIDENCE FROM PREVIOUS RESEARCH:** §3 — `data-engineer` bullet list: "Custom Python/Scala data processing with pandas, Polars, Ray... Data validation and quality monitoring with Great Expectations."
**MAIN TRADE-OFF:** Persona also carries Spark/Databricks/cloud-ETL content you won't use yet — context overhead, not a functional cost.
**CONFIDENCE:** Medium-High.

### COMPONENT: Data Quality Monitoring (Aspect A — Rule-Based)
**BEST SKILL:** `data-quality-frameworks`
**ALTERNATIVES CONSIDERED:** Folding DQ into `data-engineer` alone (that skill only namechecks Great Expectations as one bullet, no depth); no Soda-specific skill exists to alternatively consider.
**WHY THIS SKILL WINS:** Only candidate whose entire purpose is DQ-rule implementation rather than a bullet inside a broader persona.
**EVIDENCE FROM PREVIOUS RESEARCH:** §4 — direct 1:1 match to the "Data Quality Validation" architecture box.
**MAIN TRADE-OFF:** Adds Great Expectations dependency/expectation-suite scaffolding for a rule set (currently ~5 features: null_rate, duplicate_rate, claims_null_rate, cross_dataset_mismatch_rate, dq_violation_rate) small enough that a hand-rolled rule function is arguably still simpler right now.
**CONFIDENCE:** High on content quality; Medium on timing (see Step 5).

### COMPONENT: Pipeline Observability / Telemetry
**BEST SKILL:** NONE for NOW — `grafana/skills` (official) selected for LATER
**ALTERNATIVES CONSIDERED:** `observability-engineer`, `performance-engineer`
**WHY NONE WINS NOW:** Your own technical guide already classifies operational telemetry (processing_duration, throughput, failure_rate, backlog) as **simulated**, not scraped from a live system. There is nothing running yet for an OTel/Prometheus instrumentation skill to attach to — installing one now would push the agent toward instrumenting infrastructure that doesn't exist.
**WHY `grafana/skills` OVER `observability-engineer` WHEN THE TIME COMES:** `grafana/skills` is the one **officially maintained** entry in the whole stage-1 catalog (published by Grafana Labs itself); `observability-engineer` is a community persona weighted toward paid enterprise tools (DataDog, New Relic, CloudWatch) that add cost without matching your local/free requirement.
**EVIDENCE FROM PREVIOUS RESEARCH:** §5 + UC10 technical guide §13 ("Real vs Derived vs Simulated Data," Category C).
**MAIN TRADE-OFF:** Deferring means the telemetry schema design work happens without skill support in the meantime — acceptable since that schema is already defined in your technical guide.
**CONFIDENCE:** High that NOW is wrong; Medium-High that `grafana/skills` wins once the phase arrives.

### COMPONENT: Statistical Anomaly Detection (Behaviour/Volume: MAD; Distribution: KS/Wasserstein)
**BEST SKILL:** NONE
**ALTERNATIVES CONSIDERED:** `ml-engineer` (one generic "drift detection" bullet, no MAD/KS/Wasserstein content), `data-scientist` (fully generic, no anomaly-specific content)
**WHY NONE WINS:** This was an explicit stage-1 finding, not a fresh conclusion — no catalog entry anywhere packages median/MAD, KS-test, or Wasserstein-distance workflows as its own skill.
**EVIDENCE FROM PREVIOUS RESEARCH:** §6, flagged "RESEARCH FINDING (important)."
**MAIN TRADE-OFF:** None avoided by not installing; a CUSTOM skill is the only path (see Step 9).
**CONFIDENCE:** High that no existing skill is adequate.

### COMPONENT: ML / Isolation Forest Detection
**BEST SKILL:** NONE installed — `ml-engineer` noted only as inadequate background reference, not selected
**ALTERNATIVES CONSIDERED:** `ml-engineer` vs `data-scientist`
**WHY NEITHER WINS:** Between the two, `ml-engineer` is nominally stronger (names feature monitoring, drift detection, standard scikit-learn vocabulary) but both are calibrated for MLflow/Kubeflow/multi-GPU production-ML teams — none of that applies to a single scikit-learn `IsolationForest` on an 18-feature tabular daily matrix. Installing either risks nudging the agent toward infrastructure (experiment tracking, hyperparameter search) this component doesn't need.
**EVIDENCE FROM PREVIOUS RESEARCH:** §6.
**MAIN TRADE-OFF:** Losing `ml-engineer`'s broader ML-ops vocabulary in exchange for avoiding scope creep.
**CONFIDENCE:** Medium — reasonable people could keep `ml-engineer` as a loose reference; it is excluded here to keep the stack small (Step 4).

### COMPONENT: Evidence Fusion / Anomaly Assessment
**BEST SKILL:** NONE
No stage-1 candidate addresses fusing DQ + MAD + KS + Isolation-Forest outputs into one assessment. This is bespoke logic specific to DataSentinal's four-aspect design.
**EVIDENCE:** Absence — no skill in stage 1 references multi-detector evidence fusion.
**CONFIDENCE:** High that this must be CUSTOM.

### COMPONENT: RCA
**BEST SKILL:** NONE for the RCA computation itself — `incident-responder` selected for LATER, workflow-language only
**ALTERNATIVES CONSIDERED:** `phase-gated-debugging`/`debugger` (root-cause discipline for source code, not data), `analyze-project` (AI session logs, not pipeline incidents), `graphify` (codebase graphs, not data lineage)
**WHY THE THREE "RCA-SHAPED" CANDIDATES ALL LOSE:** All three operate on the wrong entity. Your RCA box needs reasoning over data/pipeline lineage (which hospital, which batch, which schema field, which detector fired) — none of the three graph/debug the *data*, all three graph/debug *code or AI sessions*.
**WHY `incident-responder` IS KEPT AT ALL:** Not for RCA computation — only for the human-facing runbook/alert-triage *language* in your Action layer (fix/re-run/re-upload → verification → closure).
**EVIDENCE FROM PREVIOUS RESEARCH:** §7, explicit rejections of `graphify` and `analyze-project` carried forward unchanged.
**MAIN TRADE-OFF:** The actual RCA logic (dependency graph over pipeline stages, à la your own technical guide §11 "Feature → Aspect → Detector" table) has to be built, not installed.
**CONFIDENCE:** High that core RCA is CUSTOM; Medium that `incident-responder` earns its LATER slot for workflow language alone.

### COMPONENT: RAG Knowledge Assistant
**BEST SKILL:** `rag-implementation`
**ALTERNATIVES CONSIDERED:** `langchain-architecture`, `prompt-engineering`
**WHY THIS SKILL WINS:** Only candidate with a concrete runnable scaffold (loaders → chunking → embeddings → Chroma → RetrievalQA → hybrid BM25+dense retrieval) rather than conceptual guidance alone. `langchain-architecture` covers the same concepts with no code; `prompt-engineering` covers explanation-formatting only, not retrieval.
**EVIDENCE FROM PREVIOUS RESEARCH:** §8 — sample code shown directly; `langchain-architecture` confirmed conceptual-only in the same section.
**MAIN TRADE-OFF:** Default sample code calls OpenAI embeddings/LLM (external key + cost); swapping to local embeddings (`sentence-transformers`) + a local LLM is on you, not the skill.
**CONFIDENCE:** High that it beats the alternatives; genuinely LATER since RAG needs Evidence Fusion/RCA output to retrieve against, which doesn't exist yet.

### COMPONENT: Recommended Actions
**BEST SKILL:** NONE separate — this is RAG's output stage per your own architecture, not an independent component. No dedicated "recommendation engine" skill was found in stage 1, and none would be appropriate to bolt on separately.
**CONFIDENCE:** High.

### COMPONENT: Dashboard / UI
**BEST SKILL:** `developing-with-streamlit`
**ALTERNATIVES CONSIDERED:** `kpi-dashboard-design`, `dashboard-designer`
**WHY THIS SKILL WINS:** The only officially-maintained skill found in the entire stage-1 research (ships inside the Streamlit pip package, auto-version-matched). `kpi-dashboard-design` provides overlapping Streamlit/Plotly code from an unofficial fork — strictly redundant once the official skill is in. `dashboard-designer` is design-guidance-only, no code.
**EVIDENCE FROM PREVIOUS RESEARCH:** §10, explicitly flagged as "officially maintained rather than a community fork."
**MAIN TRADE-OFF:** Streamlit-specific — locks the UI framework choice; revisit if the team later wants React/Grafana instead.
**CONFIDENCE:** High.

### COMPONENT: Alerts / Notifications
**BEST SKILL:** NONE
No stage-1 candidate covers Email/Teams/Slack alert delivery or routing logic specifically. `incident-responder` (assigned to RCA above) covers response *process*, not delivery integration.
**EVIDENCE:** Absence — no alerting-integration skill named anywhere in stage 1.
**CONFIDENCE:** High that this is CUSTOM, and likely small (webhook POST + SMTP, not skill-scale work).

### COMPONENT: Testing / Verification
**BEST SKILL:** `phase-gated-debugging` (same skill as the dev-discipline recommendation below — serves double duty)
**ALTERNATIVES CONSIDERED:** `test-driven-development`, `playwright-skill`/`webapp-testing`, `systematic-debugging`
**WHY THIS SKILL WINS, WITH AN HONEST CAVEAT:** Your architecture's "Verification" step (DataOps engineer confirms a fix actually resolved the flagged anomaly) is a root-cause-confirmation workflow, which is exactly what `phase-gated-debugging`'s "do not close until root cause is confirmed" protocol encodes. `playwright-skill`/`webapp-testing` are browser E2E tools — irrelevant; there's no browser surface being tested beyond a not-yet-built dashboard. `test-driven-development` is a reasonable alternative specifically for unit-testing the detector functions during build, and is worth keeping in mind for that narrower purpose.
**EVIDENCE FROM PREVIOUS RESEARCH:** §7 (bundle listing) — this is the thinnest evidence base in the whole selection. Testing was never given its own dedicated section in stage 1; these names surfaced incidentally while researching RCA/debugging skills. Filter questions #3 ("sufficiently mature") and #4 ("maintained") were **not independently verified** for the testing-specific candidates the way they were for other rows.
**MAIN TRADE-OFF:** Selection confidence here is genuinely lower than the rest of this report; treat this row as provisional.
**CONFIDENCE:** Low-Medium — flagged for follow-up verification, not a firm recommendation.

### COMPONENT: Cloud-Native / DevOps
**BEST SKILL:** `docker-expert` — selected for LATER, not NOW
**ALTERNATIVES CONSIDERED:** `k8s-manifest-generator`/`kubernetes-architect`, CI/CD pipeline skills
**WHY THIS SKILL WINS:** Right-sized for eventual demo packaging (pipeline + DataSentinal + dashboard as 2–3 Docker Compose services); the skill's own routing logic explicitly refuses to over-reach into Kubernetes scope, which matches the project's actual scale better than the K8s-tier alternatives.
**EVIDENCE FROM PREVIOUS RESEARCH:** §11.
**MAIN TRADE-OFF:** None now — nothing is deployed yet, so this stays LATER regardless of which DevOps skill eventually wins.
**CONFIDENCE:** Medium-High for eventual use; High that NOW is wrong.

---

## STEP 4 — Duplication Removed

- `python-pro` → absorbed by `data-engineer`.
- `data-scientist` → absorbed by (rejected) `ml-engineer`; net effect, neither installed.
- `kpi-dashboard-design`, `dashboard-designer` → absorbed by `developing-with-streamlit`.
- `observability-engineer`/`performance-engineer` → superseded by `grafana/skills` for the LATER slot (official > community, free-by-default > paid-tool-weighted).
- `langchain-architecture` → absorbed by `rag-implementation`.
- `postmortem-writing` → absorbed by `incident-responder`.
- `phase-gated-debugging` covers **two** components (dev discipline + testing/verification) rather than installing a separate skill for each.

---

## STEP 5 — Phase Classification

| Component | Skill | Phase |
|---|---|---|
| Pipeline | `data-engineer` | **NOW** |
| Data Quality | `data-quality-frameworks` | **NOW** |
| Dev discipline + Testing/Verification | `phase-gated-debugging` | **NOW** |
| Telemetry | `grafana/skills` | LATER (needs a real running pipeline first) |
| Statistical Detection | — | **CUSTOM** |
| ML Detection | — | **CUSTOM** (background only, no install) |
| Evidence Fusion | — | **CUSTOM** |
| RCA computation | — | **CUSTOM** |
| RCA workflow language | `incident-responder` | LATER |
| RAG | `rag-implementation` | LATER (needs Evidence Fusion/RCA output to retrieve against) |
| Recommendation | — | covered by RAG, no separate item |
| UI | `developing-with-streamlit` | LATER (needs something real to display) |
| Alerts | — | **CUSTOM** (small glue code) |
| DevOps | `docker-expert` | LATER (nothing deployed yet) |

---

## STEP 6 — Minimum Viable Skill Stack

**8 skills total** (within the 6–10 target):

1. `data-engineer`
2. `data-quality-frameworks`
3. `phase-gated-debugging` (covers both dev-discipline and testing/verification — one skill, two jobs)
4. `grafana/skills`
5. `incident-responder`
6. `rag-implementation`
7. `developing-with-streamlit`
8. `docker-expert`

Notably **not** in this stack, and deliberately so: separate Python, ML, observability, and generic-testing skills — each was either redundant with one of the eight above or too weak/misaligned to justify its own slot (see Step 4).

---

## STEP 7 — Final Ranking

| # | Skill | Component | Phase | Why It Matters | Evidence | Confidence |
|---|---|---|---|---|---|---|
| 1 | `data-quality-frameworks` | Data Quality Monitoring | NOW | Direct 1:1 architecture match, no weaker competitor exists | §4 | High |
| 2 | `data-engineer` | Representative Pipeline | NOW | Broadest single-skill match to your 6-stage pipeline without adding an unneeded orchestrator | §3 | Medium-High |
| 3 | `phase-gated-debugging` | Dev discipline + Testing/Verification | NOW | Root-cause-confirmation protocol maps directly to your Verification step; doubles as build-time discipline | §7 (thin for testing use) | Medium (High for dev-discipline use, Low-Medium for testing use) |
| 4 | `developing-with-streamlit` | Dashboard/UI | LATER | Only officially-maintained skill in the whole catalog; direct content match | §10 | High |
| 5 | `rag-implementation` | RAG | LATER | Only runnable (not just conceptual) RAG scaffold found | §8 | High |
| 6 | `grafana/skills` | Telemetry | LATER | Only officially-maintained observability option; free/local by default | §5 | Medium-High |
| 7 | `docker-expert` | DevOps | LATER | Right-sized for demo-scale deployment, explicitly avoids K8s over-reach | §11 | Medium-High |
| 8 | `incident-responder` | RCA (workflow language only) | LATER | Best available source for runbook/alert-triage language, despite not computing RCA itself | §7 | Medium |

---

## STEP 8 — Final Installation Recommendation

### MUST INSTALL
- `data-quality-frameworks`
- `data-engineer`
- `phase-gated-debugging`

### RECOMMENDED
*(strongly useful, not yet necessary — install when Step 5's phase condition is met)*
- `developing-with-streamlit`
- `rag-implementation`
- `grafana/skills`
- `docker-expert`
- `incident-responder`

### INSTALL LATER
*(same list as RECOMMENDED above — in this project, "recommended-but-not-now" and "install later" are the same five skills; there is no third tier of skills that are useful-later-but-not-yet-recommended)*

### DO NOT INSTALL
- `python-pro` — redundant with `data-engineer`.
- `data-scientist` — weaker and more generic than `ml-engineer`, itself not selected either.
- `ml-engineer` — MLOps content (MLflow, Kubeflow, multi-GPU) doesn't match a single-model tabular Isolation Forest use case; superseded by a planned CUSTOM skill.
- `spark-optimization`, `airflow-dag-patterns`, `dbt-transformation-patterns` — no distributed/orchestration problem exists yet at current scale.
- `observability-engineer`, `performance-engineer` — superseded by `grafana/skills`; paid-tool-weighted and premature.
- `kpi-dashboard-design`, `dashboard-designer` — redundant with `developing-with-streamlit`.
- `k8s-manifest-generator`, `kubernetes-architect`, `helm-chart-scaffolding`, CI/CD pipeline skills — wrong scale, nothing deployed yet.
- `analyze-project` — analyzes AI coding sessions, not data-pipeline incidents. Wrong entity.
- `graphify` — graphs source code, not data lineage. Wrong entity.
- `agent-orchestrator`/multi-agent skills — architecture is a linear pipeline, not multi-agent.
- `langchain-architecture` — redundant with, and weaker than, `rag-implementation`.
- `postmortem-writing` — redundant with `incident-responder`.

---

## STEP 9 — DataSentinal-Specific Gap Analysis

No existing skill (installed or rejected) adequately covers the following. Each is a genuine candidate for a **future DataSentinal-specific skill**, to be authored in-house — not a generic skill stretched to fit:

- **Four monitoring aspects (rule-based DQ + MAD + KS/Wasserstein + Isolation Forest) as a unified detection layer** — no skill covers this combination; `data-quality-frameworks` covers only the first of four.
- **Pipeline telemetry schema specific to your 18-feature matrix** — `grafana/skills` teaches dashboard/alerting mechanics generically, not your specific feature schema.
- **Healthcare claims/CMS domain context** — confirmed absent in stage 1 (§9): no FHIR/HL7/CMS/Medicare skill exists anywhere. Your `UC10_DATA_FOUNDATION_FEATURE_ENGINEERING_GUIDE.pdf` is currently the only place this knowledge lives.
- **Evidence fusion logic** (combining DQ + MAD + KS + Isolation Forest scores into one assessment) — no skill addresses multi-detector fusion at all.
- **SLA-risk assessment** — not covered by any stage-1 candidate; this is bespoke ETA/deadline logic specific to your claims-processing SLA definition.
- **Healthcare-pipeline RCA** (dependency reasoning over hospital → batch → schema field → detector, not source code) — confirmed gap; the two nearest candidates (`graphify`, `analyze-project`) were explicitly rejected for operating on the wrong entity.
- **DataSentinal-specific RAG knowledge base** (your own DQ rules, past incidents, remediation playbooks) — `rag-implementation` provides the retrieval *mechanism*; the *content* to retrieve is 100% yours to build and doesn't exist as a skill.
- **Historical incident reasoning** — no skill stores or reasons over your own incident history; this would need to be a CUSTOM data store plus retrieval logic, likely layered on top of the `rag-implementation` mechanism once you have incidents to log.
- **Controlled remediation** (re-run/re-upload/schema-fix actions, gated by human approval) — no skill addresses controlled, approval-gated remediation actions; this is workflow logic specific to your DataOps engineer's role.
- **Verification/feedback loop** (confirming a remediation actually fixed the flagged anomaly) — `phase-gated-debugging`'s protocol is the closest analogy found, but it was designed for source-code debugging, not for closing the loop on a data-quality incident; treat it as inspiration for a CUSTOM verification skill, not a literal fit.

**Recommendation:** once the CUSTOM detection/fusion/RCA logic exists as working code, use the `skill-creator` meta-skill (noted in stage 1 §12, not separately scored here since it's tooling for future use, not a component-mapped skill) to package that logic into 1–2 in-house DataSentinal skills — likely one for "detection + fusion" and one for "healthcare/CMS data dictionary" — rather than one skill per micro-capability.

---

## STEP 10 — Final Decision Table

| Rank | Skill | Component | Phase | Why Selected | Evidence Strength | Confidence |
|------|-------|-----------|-------|--------------|------------------|------------|
| 1 | `data-quality-frameworks` | Data Quality Monitoring | NOW | Direct architecture match, no competitor | Strong | High |
| 2 | `data-engineer` | Representative Pipeline | NOW | Broadest single fit without adding an orchestrator | Strong | Medium-High |
| 3 | `phase-gated-debugging` | Dev discipline / Testing / Verification | NOW | Root-cause-confirmation protocol maps to Verification step | Strong (dev) / Thin (testing) | Medium |
| 4 | `developing-with-streamlit` | Dashboard/UI | LATER | Only officially-maintained skill found | Strong | High |
| 5 | `rag-implementation` | RAG | LATER | Only runnable RAG scaffold found | Strong | High |
| 6 | `grafana/skills` | Telemetry | LATER | Only officially-maintained observability option | Strong | Medium-High |
| 7 | `docker-expert` | DevOps | LATER | Right-sized, avoids K8s over-reach | Strong | Medium-High |
| 8 | `incident-responder` | RCA (workflow language) | LATER | Best available runbook-language source | Moderate | Medium |

### MUST INSTALL NOW
`data-quality-frameworks`, `data-engineer`, `phase-gated-debugging`

### INSTALL LATER
`developing-with-streamlit`, `rag-implementation`, `grafana/skills`, `docker-expert`, `incident-responder`

### CUSTOM DATASENTINAL SKILLS
Four-aspect detection layer (MAD/KS/Wasserstein/Isolation Forest) · Evidence fusion · Healthcare-pipeline RCA (data/lineage graph) · SLA-risk assessment · Healthcare/CMS data dictionary · Alerts/notification integration · DataSentinal-specific RAG knowledge base · Historical incident store · Controlled remediation workflow · Verification/feedback loop

### DO NOT INSTALL
`python-pro`, `data-scientist`, `ml-engineer`, `spark-optimization`, `airflow-dag-patterns`, `dbt-transformation-patterns`, `observability-engineer`, `performance-engineer`, `kpi-dashboard-design`, `dashboard-designer`, `k8s-manifest-generator`, `kubernetes-architect`, `helm-chart-scaffolding`, CI/CD pipeline skills, `analyze-project`, `graphify`, `agent-orchestrator`/multi-agent skills, `langchain-architecture`, `postmortem-writing` — reasons given per-item in Step 8.

---

## Final Architectural Check

Walking the full chain — **Pipeline → Telemetry → Data Quality → Statistical Detection → ML Detection → Evidence Fusion → RCA → RAG → Recommendation → UI → Alerts → Testing**:

- **Pipeline** — covered (`data-engineer`).
- **Telemetry** — covered LATER (`grafana/skills`); **no skill covers it for the current phase**, and none should be installed for it yet.
- **Data Quality** — covered (`data-quality-frameworks`).
- **Statistical Detection** — **no suitable skill exists**; CUSTOM required.
- **ML Detection** — **no suitable skill exists**; CUSTOM required (generic ML-ops skills rejected as mismatched).
- **Evidence Fusion** — **no suitable skill exists**; CUSTOM required.
- **RCA** — **no suitable skill exists for the computation**; `incident-responder` covers only the surrounding human workflow language, LATER.
- **RAG** — covered LATER (`rag-implementation`).
- **Recommendation** — covered as part of RAG's output; no separate skill needed.
- **UI** — covered LATER (`developing-with-streamlit`).
- **Alerts** — **no suitable skill exists**; CUSTOM required, expected to be small.
- **Testing/Verification** — weakly covered (`phase-gated-debugging`), confidence explicitly flagged as lower than the rest of this report.

Six of twelve chain links (Statistical Detection, ML Detection, Evidence Fusion, RCA computation, Alerts, and — partially — Testing) have **no adequate existing skill** and are confirmed CUSTOM work, matching the Step 9 gap analysis above.

---

Stopping here per instructions — nothing installed. Let me know if you want me to proceed with any of the MUST INSTALL items, or start scoping the CUSTOM DataSentinal skills list.
