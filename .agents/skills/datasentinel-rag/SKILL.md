---
name: datasentinel-rag
description: RAG engineering architecture, rules, and best practices for the DataSentinel Root Cause Analysis (RCA) Engine.
---

# DataSentinel RAG Engineering Skill

This skill provides the comprehensive architecture, retrieval rules, grounding logic, and evaluation standards for building the DataSentinel RAG (Retrieval-Augmented Generation) / RCA Engine.

## 1. System Context
DataSentinel possesses structured operational stores (DuckDB):
- `pipeline_events` (Telemetry)
- `rule_results` (Deterministic DQ Engine)
- `metrics_repository` (ML Anomaly Detection)

**CRITICAL PRINCIPLE:** The RAG system is **NOT** a detector. It is an explanation engine. It consumes downstream telemetry and anomaly events, correlates the evidence, and generates human-readable incident explanations.

```text
PIPELINE -> TELEMETRY -> DQ ENGINE -> ML DETECTION -> ANOMALYEVENT
                                                             |
                                                       RAG EVIDENCE LAYER
                                                             |
                                                HYBRID & SQL RETRIEVAL
                                                             |
                                                         RERANKING
                                                             |
                                                           LLM
                                                             |
                                                    RCA / EXPLANATION
```

## 2. Retrieval Rules (Hybrid Search)

### Structured SQL Retrieval (First-Class)
Do NOT vectorize everything. Exact entity telemetry and metrics must be retrieved via structured SQL (e.g., DuckDB).
Use SQL exclusively for exact queries regarding:
- `run_id`, `hospital_id`, `batch_id`
- Metrics: durations, record counts, anomaly scores
- "Which business rules failed for batch X?"

### Semantic Retrieval (Contextual Hybrid)
Use Vector Embeddings + BM25 for unstructured knowledge, documentation, or matching abstract operator queries ("Why is there a latency spike?", "Have we seen this failure pattern before?").

**Contextual Retrieval Pattern:**
When chunking documents or historical RCA logs, apply Anthropic's Contextual Retrieval strategy: prepend a short LLM-generated summary to each chunk to preserve its global context (e.g., "This chunk is about the operational latency anomaly in hospital HOSP-001 during batch_004...").

## 3. Evidence Contract Rules
Every generated RCA statement must be backed by a Canonical Evidence object:
- `evidence_id`, `run_id`, `hospital_id`, `batch_id`, `stage`, `timestamp`
- `source`, `evidence_type`, `feature_name`, `value`, `baseline`, `deviation`, `severity`
- `rule_id` (if applicable), `model_name`, `anomaly_score`, `message`, `source_reference`

## 4. LLM Grounding & Hallucination Rules
- **No Invention**: The LLM must NEVER invent metrics, causes, rule violations, or timestamps.
- **Insufficient Evidence**: If retrieved context does not sufficiently explain the anomaly, the LLM MUST return exactly: *"Insufficient evidence to determine root cause."*

## 5. RCA Output Contract
The final LLM response must strictly adhere to this schema:
```json
{
  "incident_id": "uuid",
  "summary": "High-level summary of the issue.",
  "severity": "HIGH/MEDIUM/LOW",
  "affected_hospital": "ID",
  "affected_batch": "ID",
  "affected_stage": "Stage Name",
  "what_happened": "Detailed factual description based on evidence.",
  "evidence": [{"source_reference": "ref", "value": "..."}],
  "contributing_factors": ["list of strings"],
  "likely_root_causes": ["list of strings"],
  "confidence": 0.95,
  "recommended_investigation": ["Operator steps"],
  "source_references": ["List of evidence_ids"]
}
```

## 6. Security Boundaries
- **Immutable State**: `data/` and `master_data/` are strictly read-only.
- **SQL Execution**: The LLM cannot execute arbitrary SQL against live databases. SQL must be parameterized or strictly validated via a secure query engine integration.

## 7. RAG Evaluation Metrics
Evaluate performance using:
- **Retrieval**: Recall@K, MRR
- **Generation**: Faithfulness, Answer Correctness, Context Relevance
- **Adversarial**: Hallucination rate on empty/conflicting evidence datasets.
