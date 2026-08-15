# UC10 — Anomaly Detection Framework

> **Purpose:** Define exactly what UC10 considers an anomaly, how each class is detected, what evidence is produced, and how the parallel hybrid detection layer feeds RCA, impact, SLA assessment, remediation, and verification.

## 1. Core Principle

UC10 must not treat every unusual observation as bad data.

| Class | Meaning | Primary Mechanism |
|---|---|---|
| Data Quality Violation | Known expectation is violated | Deterministic rules |
| Statistical/Behavioral Anomaly | Metric/distribution is unusually different from baseline | Robust statistics |
| Multivariate Processing Anomaly | Combination of operational metrics is unusual | Isolation Forest |
| SLA Risk | Current operational state may miss deadline | ETA / throughput analysis |

The hybrid design is **parallel specialization**, not a chain where every record must pass through every algorithm.

## 2. Final Detection Architecture

```text
                 DATA / PIPELINE STATE
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
    DATA QUALITY     STATISTICAL    MULTIVARIATE
      SIGNAL           SIGNAL          SIGNAL
          |              |              |
          v              v              v
       RULES        MEDIAN + MAD    ISOLATION FOREST
          |              |              |
          +--------------+--------------+
                         |
                  EVIDENCE FUSION
                         |
                  ANOMALY ASSESSMENT
                         |
              +----------+----------+
              |                     |
              v                     v
             RCA                  IMPACT
              |                     |
              +----------+----------+
                         |
                      SLA RISK
```

## 3. Class A — Data Quality Detection

### Question

> Does the data violate a known expectation?

### Scope

- schema/conformance;
- completeness;
- validity;
- uniqueness;
- referential integrity;
- consistency;
- supported cross-dataset consistency.

Examples:

- Provider_ID is NULL;
- invalid date;
- invalid code/value;
- duplicate under a validated key;
- broken reference;
- required column absent.

Use deterministic rules when a valid explicit expectation exists.

Output:

```text
event_id
dataset
batch
rule_id
dimension
field
observed_value
expected_condition
affected_count
severity
timestamp
```

## 4. Class B — Statistical / Behavioral Detection

### Question

> Is a measurable metric behaving unusually compared with its historical baseline?

Candidate metrics:

- record volume;
- processing rate;
- duration;
- failure rate;
- retry rate;
- backlog;
- missing rate;
- duplicate rate;
- invalid rate;
- aggregate DQ score.

### Primary prototype candidate

**Rolling Median + MAD**

Concept:

```text
Historical observations
→ Rolling median
→ MAD
→ Robust deviation
→ Threshold
→ Statistical anomaly
```

Possible research alternatives:

- robust z-score;
- EWMA/control charts;
- change-point detection;
- distribution-shift methods.

The final method must be validated experimentally.

## 5. Class C — Multivariate Processing Anomaly

### Question

> Is the combination of operational metrics unusual even when individual metrics are only mildly abnormal?

Example:

```text
Volume           +12%
Throughput       -18%
Failure rate      +6%
Retry rate        +9%
Backlog          +25%
Duration         +20%
```

### Primary prototype candidate

**Isolation Forest**

Use batch/window-level operational features, not raw claims.

Example vector:

```text
[
 record_count,
 missing_rate,
 duplicate_rate,
 invalid_rate,
 processing_rate,
 failure_rate,
 retry_rate,
 backlog,
 duration
]
```

Isolation Forest indicates an unusual operational state. It does not prove that the underlying healthcare data is wrong and does not independently establish root cause.

## 6. Feature Engineering

Possible batch/window features:

### Volume

- records received;
- records processed;
- records rejected.

### Quality

- missing rate;
- duplicate rate;
- invalid rate;
- DQ violation count.

### Processing

- throughput;
- duration;
- failure rate;
- retry rate.

### Queue

- backlog;
- remaining workload.

### Distribution

- meaningful category proportions;
- appropriate distribution-shift statistics.

Only use features actually supported by the dataset or controlled simulation.

## 7. Evidence Fusion

The detectors produce independent signals.

Example:

```text
DQ rule            → violation
Statistical signal → high volume deviation
ML signal          → anomalous
```

Fusion should:

1. collect signals;
2. correlate by batch/window/entity;
3. remove redundant evidence;
4. prioritize evidence;
5. produce an anomaly assessment.

Do not introduce arbitrary weights such as:

```text
0.4 Rule + 0.3 MAD + 0.3 ML
```

unless the weights are experimentally justified.

Assessment:

- anomaly type;
- severity;
- confidence/evidence strength;
- affected entity;
- affected stage;
- contributing signals;
- timestamp;
- detector/rule versions.

## 8. Severity vs Confidence

**Severity** describes potential impact.

**Confidence** describes strength of evidence.

These are separate.

Example:

```text
High severity + Low confidence
```

can be valid when potential impact is large but evidence is incomplete.

## 9. Cross-Dataset Validation

Use structured joins/indexes.

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

If an authorization dataset is actually introduced and compatible keys are verified:

```text
Claim
  ↓
Validated authorization relationship
  ↓
MATCH / NO MATCH
```

Do not use RAG to replace deterministic entity matching.

Do not claim relationships that the datasets do not support.

## 10. Bad Data vs Unusual Data

### Bad Data

A valid rule is violated.

### Unusual Data

The value is valid but statistically unusual.

### Pipeline Anomaly

Operational processing behavior is unusual.

### SLA Risk

Current operational state projects a timing problem.

These should remain distinct event categories.

## 11. SLA Risk

SLA risk is downstream of anomaly assessment.

Inputs:

- remaining workload;
- current throughput;
- remaining time;
- deadline;
- estimated recovery/reprocessing time;
- severity.

Initial prototype:

```text
ETA = Remaining Workload / Current Throughput
```

Compare ETA with remaining SLA time.

Possible states:

```text
SAFE
AT_RISK
HIGH_RISK
BREACH_RISK
```

Real-time SLA behavior must be simulated if actual telemetry is unavailable.

## 12. Controlled Anomaly Injection

Because public static datasets do not provide a complete ground-truth incident history, use controlled test scenarios.

### DQ injections

- remove required values;
- invalid dates;
- controlled duplicates;
- invalid values;
- broken references;
- schema changes.

### Statistical injections

- reduce volume;
- increase duration;
- increase failures;
- increase retries.

### Multivariate injections

```text
moderately higher volume
+
lower throughput
+
higher failures
+
higher backlog
+
longer duration
```

### SLA injections

- reduce throughput;
- increase remaining workload;
- reduce available processing time.

Every injected anomaly must be labelled as simulated.

## 13. Evaluation

### Detection

- precision;
- recall;
- false-positive rate;
- false-negative rate;
- latency.

### Statistical

- baseline stability;
- sensitivity;
- robustness to legitimate outliers.

### Isolation Forest

- anomaly ranking;
- stability;
- contamination sensitivity;
- performance on controlled scenarios.

### Evidence Fusion

- false-positive reduction;
- signal agreement/disagreement;
- explanation quality.

### RCA

- stage localization;
- probable-cause accuracy;
- evidence completeness.

### SLA

- ETA error;
- risk classification accuracy.

## 14. Candidate Comparison

| Method | Purpose | Labels | Explainability | Prototype Position |
|---|---|---:|---:|---|
| Rule validation | Known DQ violations | No | Very High | Core |
| Median + MAD | Univariate behavior | No | High | Primary |
| EWMA/control chart | Persistent change | No | High | Research candidate |
| Change-point detection | Regime shifts | No | Medium–High | Research candidate |
| Isolation Forest | Multivariate anomaly | No | Medium | Primary ML candidate |
| LOF | Local-density anomaly | No | Medium–Low | Optional comparison |
| One-Class SVM | Novelty detection | No | Medium–Low | Optional comparison |
| Supervised classifier | Labelled anomaly classes | Yes | Depends | Future |

## 15. What ML Must Not Do

Isolation Forest must not:

- replace explicit DQ rules;
- decide semantic validity;
- calculate SLA status;
- claim root cause;
- directly trigger destructive remediation;
- use RAG as a substitute for feature data.

## 16. Final Detector Contract

**Detection:** What is abnormal?

**RCA:** Where and why is it probably happening?

**Impact:** What is affected?

**SLA:** Will timing be affected?

**RAG:** What does documented knowledge say and what procedure applies?

**Remediation:** What action should be considered?

**Verification:** Did the action resolve the issue?

## 17. Final Boundary

```text
                 HYBRID DETECTION
                       |
       +---------------+---------------+
       |               |               |
       v               v               v
   DQ RULES        ROBUST STATS    ISOLATION FOREST
       |               |               |
       +---------------+---------------+
                       |
                EVIDENCE FUSION
                       |
               ANOMALY ASSESSMENT
                       |
             +---------+---------+
             |                   |
             v                   v
            RCA                IMPACT
             |                   |
             +---------+---------+
                       |
                    SLA RISK
```

**Final principle:** use the simplest reliable detector for each anomaly class. Known violation → rule. Abnormal metric → robust statistics. Unusual combination → multivariate ML. Combined evidence → fusion. Timing consequence → SLA calculation. Explanation/context → RAG.
