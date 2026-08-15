# UC10 — Final RAG Scope

> **Purpose:** Define the intentionally narrow RAG role in the finalized UC10 architecture. This is a UC10 boundary specification, not a generic RAG tutorial.

## 1. Final Decision

UC10 uses RAG in **two primary places**:

### RAG Role 1 — Investigation Chatbot

Users can ask questions beyond dashboard visualization and retrieve grounded explanations from project knowledge.

### RAG Role 2 — Knowledge-Assisted Anomaly Investigation

After an anomaly has already been detected by rules/statistics/ML, RAG retrieves relevant documentation and historical knowledge to explain the event and support a documented remediation recommendation.

RAG does **not** detect anomalies, calculate SLA, perform deterministic entity matching, or replace structured queries.

## 2. Final RAG Principle

```text
Structured Systems
    = current facts / current state

Analytical Engines
    = calculations / detection results

RAG
    = knowledge / documentation / historical context

LLM
    = interpretation / synthesis / explanation
```

## 3. Role 1 — Investigation Chatbot

Example questions:

- What does this field mean?
- Why was this DQ rule triggered?
- What does this anomaly type mean?
- What procedure applies?
- Has a similar incident occurred?
- What does the dataset documentation say?
- What should an operator check next?

Project-specific answers should be grounded in retrieved sources.

## 4. Role 2 — Knowledge-Assisted Anomaly Investigation

Final workflow:

```text
Anomaly Detected
      ↓
Structured Evidence Retrieved
      ↓
Anomaly Event
      ↓
Retrieve Relevant Knowledge
      ↓
RAG
      ↓
Knowledge Context
      ↓
LLM
      ↓
Grounded Explanation
      ↓
Recommended Documented Action
```

Example structured evidence:

```text
Batch: B102
Volume: 620K
Expected baseline: ~1M
Missing rate: 7.2%
Duplicate rate: 3.1%
Isolation Forest: anomalous
SLA risk: High
```

RAG may retrieve:

- relevant DQ rule;
- dataset documentation;
- pipeline documentation;
- applicable runbook;
- historical similar incident/RCA.

The LLM then explains the current event using both structured evidence and retrieved knowledge.

## 5. Final Core Knowledge Domains

Only these are core for the MVP.

### 5.1 Pipeline Runbooks & Playbooks

Include:

- ingestion failure procedure;
- validation failure procedure;
- transformation failure procedure;
- retry/reprocessing procedure;
- quarantine/hold procedure;
- release procedure;
- escalation procedure;
- SLA-risk response;
- verification procedure.

Purpose:

> Tell the operator which documented procedure applies.

### 5.2 Data Quality & Governance Rules

Include:

- DQ definitions;
- field constraints;
- schema rules;
- completeness;
- validity;
- uniqueness;
- consistency;
- referential integrity;
- severity definitions;
- blocking/warning policy.

The structured DQ engine supplies the actual violation. RAG supplies the definition and governance context.

### 5.3 Dataset Documentation & Data Dictionaries

Include:

- CMS documentation;
- Healthcare.gov PUF documentation;
- data dictionaries;
- field definitions;
- identifiers;
- row grain;
- aggregation;
- methodology;
- limitations;
- suppression;
- top/bottom coding;
- terminology.

Purpose:

> Explain what the source data actually represents.

### 5.4 Engineering / Analytics / Incident Knowledge

Include:

- pipeline architecture;
- metric definitions;
- stage definitions;
- engineering documentation;
- historical anomaly reports;
- incident reports;
- RCA reports;
- previous fixes;
- postmortems.

Purpose:

> Provide operational context and historical similarity.

Historical similarity is supporting evidence, not proof of current causality.

## 6. Healthcare Domain Knowledge Boundary

Healthcare payer/PBM knowledge is supporting context, not a core UC10 RAG objective.

CMS Part D may provide useful prescription/provider terminology and context, but it should not be treated as a complete:

- PBM policy repository;
- formulary repository;
- prior-authorization rule base;
- coverage-policy engine.

UC10 should not become a generic healthcare policy chatbot.

## 7. RAG vs Structured Data

| Question | Primary Source |
|---|---|
| Did batch B102 pass? | Structured event store |
| How many records failed? | Structured query |
| What is current DQ rate? | Structured DQ metrics |
| What is current SLA status? | SLA engine |
| Which Provider IDs failed? | Structured DQ results |
| What does Provider_ID mean? | RAG |
| What does DQ-017 mean? | RAG |
| What procedure applies to a transformation failure? | RAG |
| Has a similar incident occurred? | RAG history + current structured event |
| Why was B102 flagged? | Structured evidence + RAG + LLM |
| What should be done next? | RAG runbook + evidence + human approval |
| Did remediation succeed? | Structured verification |

## 8. RAG vs Cross-Dataset Validation

Cross-dataset matching is not a RAG task.

```text
Claim.Provider_ID
       ↓
Provider Reference Index
       ↓
MATCH / NO MATCH
```

Likewise where supported:

```text
Claim.Drug_ID
       ↓
Drug Reference Index
       ↓
MATCH / NO MATCH
```

If an authorization dataset with compatible identifiers is later introduced:

```text
Claim
  ↓
Validated authorization relationship
  ↓
MATCH / NO MATCH
```

RAG can explain the meaning of a relationship, but should not perform the actual deterministic match.

## 9. Knowledge Base Structure

Recommended prototype:

```text
rag/
├── dataset_documentation/
│   ├── cms_claims.md
│   ├── cms_partd.md
│   └── healthcare_puf.md
│
├── dq_rules/
│   └── dq_rules.md
│
├── runbooks/
│   ├── ingestion_failure.md
│   ├── dq_failure.md
│   ├── transformation_failure.md
│   ├── batch_reprocessing.md
│   └── sla_risk.md
│
└── incidents/
    ├── incident_001.md
    ├── incident_002.md
    └── rca_examples.md
```

Synthetic operational documents must be explicitly labelled:

> **Prototype/Synthetic Operational Knowledge — Not an Official CMS Document**

## 10. Source Authority

Recommended priority:

1. Official CMS / Healthcare.gov documentation
2. Approved project DQ/governance definitions
3. Approved project runbooks
4. Approved project engineering documentation
5. Incident/RCA history
6. Research literature
7. Clearly labelled synthetic/prototype knowledge

Conflicts should be surfaced rather than silently merged.

## 11. Metadata

Recommended fields:

```text
document_id
title
source
source_type
authority_level
version
effective_date
expiry_date
dataset
pipeline_stage
anomaly_type
DQ_dimension
document_status
```

Metadata filtering should be used where useful before/alongside semantic retrieval.

## 12. Retrieval Strategy for MVP

Do not over-engineer the first prototype.

```text
User Question
      ↓
Intent / Query Classification
      ↓
Metadata Filter where useful
      ↓
Semantic / Keyword Retrieval
      ↓
Relevant Chunks
      ↓
LLM
      ↓
Grounded Answer
```

Hybrid retrieval can be introduced if testing shows semantic-only retrieval is insufficient.

Do not select a vector database or framework merely because it is popular.

## 13. Chunking

Use document-aware chunking.

- Data dictionaries → field/logical-section chunks.
- DQ rules → rule-level chunks.
- Runbooks → procedure-step/logical-section chunks.
- Incident reports → incident/section chunks.
- Architecture → component/section chunks.

Avoid one universal chunk size.

## 14. Grounding and Trust

Every response should preserve:

- source identity;
- source authority;
- version where relevant;
- retrieved evidence;
- uncertainty.

If authoritative evidence cannot be retrieved:

> **I could not find an authoritative source for this.**

Do not fill the gap with invented project policy.

## 15. Response Pattern

For investigation questions:

1. Direct answer
2. Current structured evidence, when relevant
3. Retrieved documentation
4. Explanation
5. Recommended documented action
6. Source/reference
7. Limitation/uncertainty

Not every response needs all sections.

## 16. RAG + RCA

RAG can retrieve:

- historical incidents;
- known failure patterns;
- stage documentation;
- configuration documentation;
- relevant runbooks.

Example:

```text
Current evidence:
Transformation stage failed.

Historical RAG result:
A previous incident had similar symptoms.

Correct wording:
"Previous incident X showed similar symptoms and was associated
with a transformation configuration problem. This is supporting
historical evidence, not proof of the current root cause."
```

## 17. RAG + Remediation

Final workflow:

```text
Anomaly
   ↓
Evidence
   ↓
RCA / Impact / SLA
   ↓
Retrieve applicable runbook
   ↓
Recommended Action
   ↓
Human Approval where required
   ↓
Remediation
   ↓
Verification
```

RAG recommends documented procedures. It does not independently execute arbitrary actions.

## 18. Human-in-the-Loop

For the MVP:

- show evidence;
- show retrieved documentation;
- show recommended action;
- require approval for consequential remediation.

Optional low-risk automation can be demonstrated for controlled actions such as retry, reprocess, quarantine, or notification.

## 19. Security and Governance

Consider:

- document access control;
- provenance;
- versioning;
- stale documents;
- conflicting policies;
- audit logging;
- prompt injection in retrieved content;
- unauthorized tool execution.

Retrieved documents should be treated as untrusted content from a security perspective.

## 20. RAG Evaluation

### Retrieval

- precision;
- recall;
- context relevance.

### Generation

- groundedness;
- faithfulness;
- citation correctness;
- completeness;
- hallucination rate;
- no-answer correctness.

### Operational

- latency;
- source-authority compliance.

Benchmark:

```text
Question
   ↓
Expected Source
   ↓
Retrieved Source
   ↓
Expected Answer
   ↓
Generated Answer
   ↓
Grounding / Correctness Score
```

## 21. Minimum Viable RAG

For the 2-day prototype:

### Documents

- official dataset documentation;
- DQ rules;
- 2–5 representative runbooks;
- 2–3 clearly synthetic historical incidents/RCA examples.

### Capabilities

- document ingestion;
- chunking;
- retrieval;
- source metadata;
- grounded LLM response;
- structured evidence injection;
- chatbot interface.

Do not spend the MVP window building:

- multi-agent RAG;
- graph RAG;
- autonomous remediation;
- huge vector infrastructure;
- hundreds of documents.

## 22. Example End-to-End Interaction

Dashboard:

```text
Batch B102
-------------------------
Volume deviation: -38%
Missing rate: 7.2%
Duplicate rate: 3.1%
ML anomaly: TRUE
SLA risk: HIGH
```

User:

> Why was B102 flagged?

Structured evidence:

```text
volume
DQ metrics
ML result
SLA result
stage status
```

RAG retrieves:

```text
DQ rule
dataset definition
relevant runbook
historical incident
```

The LLM produces a grounded explanation that distinguishes current facts from historical similarity and gives the applicable documented next step.

## 23. Final RAG Architecture

```text
                     USER
                       |
                       v
                QUERY / INTENT
                    ROUTER
                       |
          +------------+------------+
          |            |            |
          v            v            v
      STRUCTURED    ANALYTICS      RAG
         DATA        / EVENTS    KNOWLEDGE
          |            |            |
          +------------+------------+
                       |
                       v
                EVIDENCE CONTEXT
                       |
                       v
                      LLM
                       |
                       v
              GROUNDED RESPONSE
                       |
                       v
               HUMAN APPROVAL
                       |
                       v
              OPTIONAL TOOL ACTION
                       |
                       v
                  VERIFICATION
```

## 24. Final Boundary

### RAG IS responsible for

- knowledge retrieval;
- dataset explanation;
- DQ-rule explanation;
- runbook retrieval;
- historical incident retrieval;
- contextual explanation;
- documented remediation guidance.

### RAG IS NOT responsible for

- DQ detection;
- duplicate detection;
- entity matching;
- anomaly scoring;
- Isolation Forest;
- statistical calculations;
- live pipeline metrics;
- SLA calculation;
- causal proof;
- autonomous remediation.

## 25. Final Decision

The MVP RAG remains intentionally small.

The correct UC10 story is:

> **After the detection and evidence layers establish what is happening, RAG gives the operator the project-specific knowledge needed to understand the event, investigate it, and follow the appropriate documented remediation procedure.**

This keeps RAG useful without making it responsible for tasks better handled by deterministic systems and analytical models.
