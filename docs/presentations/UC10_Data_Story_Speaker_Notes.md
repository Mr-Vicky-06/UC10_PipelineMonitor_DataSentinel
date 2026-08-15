# UC10 Data Story Speaker Notes

## Slide 1: Title
- Welcome everyone to the UC10 Healthcare Data Pipeline Reliability presentation.
- Today, I'll walk you through our data journey—how we transform raw Medicare claims and pharmacy records into structured features.
- We'll then look at how our hybrid anomaly detection system uses these features to automatically identify pipeline failures and data quality issues.

## Slide 2: What Data Are We Actually Using?
- For our core pipeline, we are using three primary synthetic CMS datasets.
- First, the Beneficiary dataset acts as our backbone, giving us the identity (BENE_ID) of the patients.
- Second, the FFS Inpatient Claims dataset gives us medical activity at the claim-line level, and third, the PDE dataset gives us prescription drug events.
- Notice we focus strictly on core fields—IDs, service dates, provider info, and cost.

## Slide 3: How the Data Connects
- It's crucial to understand how we map this data. We do *not* force a direct connection between medical claims and pharmacy events.
- Instead, both datasets map upwards to the common Beneficiary. 
- We have verified a 100% match rate from both Claims and PDE up to the Beneficiary table, giving us 5,098 patients with overlapping activity in both streams.

## Slide 4: Why Each Dataset Matters
- This slide simplifies what each dataset brings to the table.
- The Beneficiary data tells us "WHO" the activity belongs to.
- The Inpatient Claims tell us "WHAT MEDICAL ACTIVITY" occurred, and PDE tells us "WHAT PHARMACY ACTIVITY" occurred.
- By combining these, we monitor the entire patient journey for pipeline drops.

## Slide 5: Turning Healthcare Records into Monitoring Signals
- We don't feed raw records directly into our machine learning models. 
- Instead, we aggregate the data into daily time windows and engineer 18 specific behavioral features.
- These range from simple volume counts (like `pde_count`) and Data Quality checks (like `duplicate_rate`), to simulated operational pipeline metrics like `backlog` and `processing_duration`.

## Slide 6: Features by Detection Purpose
- We segment our 18 features into three detection paths.
- Data Quality features like `null_rate` are evaluated by explicit Rules. They ask: "Is the data invalid?"
- Behavioral volume features like `claim_count` are evaluated by our Statistical MAD detector. It asks: "Is today's behavior unusual?"
- Cross-dataset relationships and operational metrics are fed into the Isolation Forest to ask: "Is the combination of these metrics unusual?"

## Slide 7: Why a Hybrid Detection Approach?
- We use three distinct detectors because anomalies take different forms.
- The Rule-Based DQ engine instantly catches explicit technical violations like missing keys or invalid dates.
- The Statistical MAD detector catches single-metric temporal shifts like a sudden 40% drop in volume.
- Isolation Forest catches subtle multivariate issues—like volume spiking while throughput drops and backlog increases. Together, they provide incredibly strong evidence.

## Slide 8: Example: How One Anomaly Travels Through the System
- Let's look at a realistic scenario: PDE volume drops 40% today.
- First, the Statistical MAD detector catches the drop against the historical rolling baseline.
- Next, cross-dataset metrics evaluate if claims also dropped, adding context.
- The Evidence Fusion layer combines these signals into a HIGH-SEVERITY EVENT, kicking off RCA and SLA risk assessment.

## Slide 9: Complete UC10 Data Journey
- This diagram summarizes the entire end-to-end architecture.
- Data flows from raw CMS records, through preprocessing and feature engineering, into the three parallel Hybrid Detectors.
- The findings are fused, assessed, and passed downstream to Root Cause Analysis, SLA risk evaluation, and eventually to a Human-In-The-Loop for verification.

## Slide 10: Current Status & Next Step
- So far, we've successfully completed dataset selection, empirical relationship validation, feature engineering, and the first two anomaly detectors (DQ Rules and Statistical MAD).
- The Statistical MAD detector successfully caught a controlled 40% volume anomaly in our testing.
- Our immediate next step is to implement the Isolation Forest, followed by Evidence Fusion and the RCA/SLA integrations.
