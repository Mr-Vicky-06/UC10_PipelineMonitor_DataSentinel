# UC10 — Master Knowledge Base

> **Project:** Data Pipeline Reliability and Root-Cause Remediation Management System  
> **Purpose:** Authoritative conceptual knowledge for dataset analysis, technical research, architecture refinement, and prototype implementation planning.

## 1. Executive Summary

UC10 addresses healthcare data-pipeline reliability. Healthcare data can become invalid, inconsistent, duplicated, structurally incorrect, statistically unusual, or operationally delayed while moving through ingestion, preprocessing, transformation, validation, business processing, and loading.

The finalized architecture separates four concepts:

1. **Data-quality violations** — a valid expectation is violated.
2. **Statistical/behavioral anomalies** — a metric or distribution deviates from a baseline.
3. **Multivariate processing anomalies** — an unusual combination of operational metrics occurs.
4. **SLA risk** — current workload and throughput indicate a possible deadline miss.

The finalized detection layer is parallel:

- **A. Rule-based Data Quality Detection**
- **B. Statistical Detection**
- **C. Multivariate ML Detection — Isolation Forest as the primary prototype candidate**

Their outputs feed **Evidence Fusion & Anomaly Assessment**, followed by RCA, impact analysis, SLA risk, remediation guidance, verification, and feedback.

RAG is intentionally narrow. It provides knowledge and context after/around detection; it is not the anomaly detector, live metrics store, SLA calculator, or entity-matching engine.

## 2. Problem Statement

UC10 addresses failures in healthcare data pipelines, including:

- missing or invalid data;
- duplicates;
- inconsistent information;
- schema/conformance changes;
- broken reference relationships;
- unexpected volume;
- abnormal processing rate;
- processing failures;
- prolonged duration;
- backlog/retry growth;
- cross-dataset inconsistencies;
- potential SLA breaches.

The system should answer:

- What happened?
- Where did it happen?
- Why is it likely happening?
- What is affected?
- Is the SLA at risk?
- What documented action should be considered?
- Was the issue resolved?

## 3. Final Lifecycle

```text
Data Sources
→ Ingestion & Processing
→ Parallel Hybrid Detection
   ├─ A. Rule-Based Data Quality
   ├─ B. Statistical Detection
   └─ C. Multivariate ML Detection
→ Evidence Fusion & Anomaly Assessment
→ RCA + Impact + SLA Risk
→ RAG Knowledge Assistant + Recommended Actions
→ Optional Automation + Human-in-the-Loop
→ Remediation Execution
→ Verification
→ Event Closure
→ Feedback & Learning
```

## 4. Data Sources

Current project sources:

- CMS Synthetic Medicare Claims
- CMS Part D Prescriber / PDE-style data
- Healthcare.gov Public Use Files
- Supporting/reference data where available
- Pipeline/system logs and operational metrics for controlled prototype simulation

Important: public static datasets do not automatically provide real production telemetry. Throughput, duration, retries, backlog, stage failures, freshness, and SLA timing may require controlled simulation.

## 5. Ingestion & Processing

Responsibilities:

- ingest files;
- parse and standardize;
- handle data types;
- normalize where justified;
- profile datasets;
- aggregate records into batch/time-window representations;
- derive operational features.

## 6. Hybrid Detection

### A. Rule-Based Data Quality

Detect:

- schema/conformance;
- completeness;
- validity;
- uniqueness/duplicates;
- referential integrity;
- consistency/business constraints;
- supported cross-dataset consistency.

Output should preserve rule ID, field/entity, observed value, expected condition, affected count, severity, and evidence.

### B. Statistical Detection

Detect abnormal behavior of individual metrics/distributions.

Primary prototype candidate:

**Rolling Median + MAD**

Possible research candidates:

- robust z-score;
- EWMA/control charts;
- change-point detection;
- distribution-shift methods.

Selection must be validated experimentally.

### C. Multivariate ML Detection

Primary prototype candidate:

**Isolation Forest**

Operate on batch/window-level operational features rather than raw claims.

Possible features:

- record count;
- processing rate;
- processing duration;
- failure rate;
- retry rate;
- backlog;
- missing rate;
- duplicate rate;
- invalid rate;
- aggregate DQ metrics.

Isolation Forest indicates unusual operational behavior; it does not prove bad data or root cause.

## 7. Evidence Fusion & Anomaly Assessment

Detector outputs are correlated by batch/window/entity.

Example:

```text
DQ violation       = TRUE
Volume deviation   = HIGH
Throughput         = HIGH deviation
Isolation Forest   = ANOMALOUS
```

The fusion layer should:

1. collect signals;
2. correlate signals;
3. remove redundant evidence;
4. prioritize evidence;
5. create an anomaly assessment.

Preserve individual signals. Do not introduce arbitrary weighted scoring without experimental justification.

Assessment should contain:

- anomaly type;
- severity;
- confidence/evidence strength;
- affected batch/job/stage/dataset;
- contributing detector signals;
- timestamp;
- detector/rule versions.

## 8. Anomaly Taxonomy

### Data Quality Violation

Known expectation is violated.

Examples: missing required ID, invalid date/code, duplicate under a validated key, schema mismatch, broken reference, inconsistent fields.

### Statistical/Behavioral Anomaly

A valid metric/distribution is unusually different from its baseline.

Examples: unusual volume, slow processing, elevated failure rate, distribution shift.

### Multivariate Processing Anomaly

A combination of individually borderline operational metrics is unusual.

### SLA Risk

A downstream operational assessment based on remaining workload, throughput, remaining time, deadline, and recovery/reprocessing considerations.

Initial prototype:

```text
ETA ≈ Remaining Workload / Current Throughput
```

## 9. Dataset Reality

### Directly observable

- source values;
- documented structure;
- field definitions;
- supported relationships;
- distributions and counts.

### Derivable

- DQ rates;
- duplicate candidates;
- aggregate volumes;
- distributions;
- supported cross-dataset match rates;
- batch/window features.

### Requires simulation

- processing duration;
- throughput;
- retries;
- backlog;
- stage failures;
- freshness;
- SLA deadlines;
- historical incidents.

Never present simulated telemetry as real CMS production telemetry.

## 10. Data Grain and Cross-Dataset Matching

Before matching datasets, establish:

- row grain;
- candidate keys;
- composite keys;
- legitimate repeated entities;
- aggregation;
- suppression/top/bottom coding;
- identifier compatibility.

A repeated identifier is not automatically a duplicate.

Cross-dataset validation uses structured joins/indexes:

```text
Claim.Provider_ID
→ Provider Reference Index
→ MATCH / NO MATCH
```

RAG should not perform deterministic entity matching.

Do not claim Claim↔Authorization relationships unless an appropriate authorization dataset and compatible identifiers are actually available.

## 11. RCA and Impact

RCA evidence can include:

- detector outputs;
- pipeline stage status;
- logs;
- batch metadata;
- historical behavior;
- cross-dataset evidence;
- historical incidents.

Prefer **probable cause** unless causal evidence supports a stronger claim.

Impact may include:

- affected records/entities;
- downstream impact;
- affected consumers;
- data-quality impact;
- SLA impact.

Historical similarity is supporting evidence, not proof.

## 12. Remediation and Verification

Possible actions:

- retry;
- reprocess;
- re-ingest;
- configuration correction;
- quarantine/hold;
- escalation;
- human approval;
- controlled automation where safe.

Lifecycle:

```text
Detection
→ RCA
→ Recommended Action
→ Approval if required
→ Remediation
→ Re-run Checks
→ Verification
→ Release / Block
```

## 13. RAG and AI Assistant

### Core principle

- Structured systems provide current facts/current state.
- Analytical engines provide calculations/detection results.
- RAG provides knowledge/context.
- LLM provides explanation/natural-language interaction.

### Final RAG roles

**Role 1 — Investigation Chatbot**

Questions beyond dashboard visualization:

- What does this field mean?
- What does this anomaly type mean?
- Why was this DQ rule triggered?
- What procedure applies?
- Has a similar incident occurred?

**Role 2 — Knowledge-Assisted Anomaly Investigation**

After detection, retrieve:

- relevant DQ rules;
- dataset documentation;
- pipeline documentation;
- runbooks;
- historical incident/RCA knowledge.

RAG explains and contextualizes the event; it does not make the anomaly decision.

## 14. Final RAG Knowledge Scope

Core MVP domains:

1. Pipeline Runbooks / Playbooks
2. Data Quality / Governance Rules
3. Dataset Documentation / Data Dictionaries
4. Engineering / Analytics Documentation and Incident/RCA History

Healthcare payer/PBM information is supporting domain context, not a core objective. UC10 should not become a generic healthcare policy chatbot.

## 15. RAG Boundaries

Use structured query for:

- current batch status;
- counts;
- current DQ metrics;
- current anomaly results;
- current SLA state;
- flagged entity lists.

Use analytical engines for:

- statistical anomalies;
- multivariate anomalies;
- ETA/SLA calculations.

Use RAG for:

- field definitions;
- rule explanations;
- runbooks;
- dataset semantics;
- historical incidents;
- documented remediation procedures.

Use structured evidence + RAG + LLM for questions such as:

> Why was batch B102 flagged and what should we do?

## 16. Evaluation

Detection:

- precision;
- recall;
- false positives/negatives;
- latency.

ML:

- anomaly ranking;
- stability;
- sensitivity to controlled anomalies.

RCA:

- stage localization;
- probable-cause accuracy;
- evidence completeness.

SLA:

- ETA error;
- risk classification.

RAG:

- retrieval precision/recall;
- groundedness;
- citation correctness;
- faithfulness;
- no-answer correctness;
- latency.

Controlled anomaly injection is important because public static datasets do not provide complete ground-truth incident labels.

## 17. Current Technical Position

| Component | Current Position |
|---|---|
| DQ rules | Core |
| Rolling Median + MAD | Primary statistical prototype candidate |
| Isolation Forest | Primary multivariate prototype candidate |
| Evidence fusion | Core |
| RCA | Evidence-based prototype |
| SLA ETA | Deterministic initial prototype |
| RAG | Core knowledge/context layer |
| LLM | Explanation/interface |
| Autonomous agent | Optional, not required for MVP |
| Graph database | Not required unless relationships justify it |
| Supervised anomaly classifier | Future candidate after validated labels |

## 18. Final Design Principle

UC10 is a hybrid reliability and remediation system, not an Isolation Forest project or a RAG chatbot.

```text
Known Data Problems
+
Unusual Statistical Behavior
+
Unusual Multivariate Processing Behavior
↓
Evidence Fusion
↓
Probable Cause + Impact + SLA Risk
↓
Grounded Guidance
↓
Remediation
↓
Verification
```

Use the simplest reliable mechanism for each problem class.
