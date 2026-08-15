# 04 Information Loss Analysis

When comparing Architecture B (using Aggregated Part D Prescribers) to Architecture A (using Transactional PDE), the following information is permanently lost:

| Information Element | Present in PDE (Arch A) | Present in Part D Presc. (Arch B) | Consequence of Loss |
|---|---|---|---|
| `BENE_ID` | YES | NO | Cannot trace a drug to a specific patient. |
| Event Timestamp | YES (`SRVC_DT`) | NO (Annual Aggregate) | Cannot detect temporal anomalies (e.g., sudden spikes on a Tuesday). |
| Transaction Sequence | YES | NO | Cannot detect claims-splitting or refill-too-soon anomalies. |
| Individual Quantity | YES | NO (Summed) | Cannot detect dosage outliers for a specific prescription. |
| Cross-dataset link | YES (100% match) | NO (0% match) | Destroys RCA capability bridging medical vs. pharmacy. |

**Conclusion:** Architecture B results in fatal information loss for the UC10 requirement of tracing anomalies back to specific entities and timeframes.
