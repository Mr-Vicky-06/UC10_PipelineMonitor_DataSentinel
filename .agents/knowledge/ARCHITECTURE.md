# Authoritative Architecture

## Conceptual Flow

```mermaid
flowchart TD
    DS[DATA SOURCES] --> IP[INGESTION & PROCESSING]
    IP --> PHD[PARALLEL HYBRID DETECTION]
    
    subgraph PHD[PARALLEL HYBRID DETECTION]
        RBDQ[Rule-Based Data Quality]
        SD[Statistical Detection]
        MML[Multivariate ML]
    </PHD>
    
    PHD --> EF[EVIDENCE FUSION]
    EF --> RCA[ROOT CAUSE ANALYSIS]
    RCA --> IA[IMPACT ASSESSMENT + SLA RISK]
    IA --> RAG[RAG KNOWLEDGE ASSISTANT]
    
    subgraph RAG[RAG KNOWLEDGE ASSISTANT]
        RB[Runbooks]
        DQR[Data Quality / Governance Rules]
        DD[Dataset Documentation]
        ED[Engineering Documentation]
        HI[Historical Incidents / RCA]
    </RAG>
    
    RAG --> RA[RECOMMENDED ACTIONS]
    RA --> OA[OPTIONAL AUTOMATION + HUMAN-IN-THE-LOOP]
    OA --> REM[REMEDIATION]
    REM --> VER[VERIFICATION]
    VER --> EC[EVENT CLOSURE]
    EC --> FL[FEEDBACK & LEARNING]
```

## Critical Architectural Constraints

1. **RAG Usage:** RAG is primarily a knowledge assistant. RAG is NOT the mechanism for deterministic cross-dataset validation. Cross-dataset validation must use structured/deterministic logic.
2. **Detection Methodology:** Detection is hybrid (Rules + Statistics + ML).
3. **Graph Analysis:** NetworkX may be used where lightweight graph analysis is sufficient.
