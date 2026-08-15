# 02 Key and Row-Grain Analysis

This document determines the fundamental grain and identifiers for each dataset, establishing what a "record" actually represents.

## 1. CMS Medicare Part D Prescribers (by Provider and Drug)

**What one row represents (Grain):**
One row represents the **aggregate prescribing activity** of one specific provider (NPI) for one specific drug (Brand Name / Generic Name) during the 2024 calendar year.
*IMPORTANT:* This is **NOT** an individual healthcare claim. It is an annual aggregate summary at the Provider + Drug level.

**Identifiers / Keys:**
- **Candidate Primary Key:** Composite of `Prscrbr_NPI` + `Brnd_Name` + `Gnrc_Name`.
- **Why `Prscrbr_NPI` alone is not unique:** A single provider prescribes multiple different drugs, resulting in multiple rows per NPI.
- **Why `Brnd_Name` alone is not unique:** The same drug is prescribed by multiple providers.

**Legitimate Repeated Entities:**
- Providers (`Prscrbr_NPI`) repeat legitimately for each drug they prescribe.
- Drugs (`Brnd_Name`) repeat legitimately for each provider prescribing them.

## 2. Healthcare.gov Plan Attributes PUF

**What one row represents (Grain):**
One row represents a **specific health plan variant** (e.g., a specific CSR tier of a Silver plan) offered by an issuer in a given state for the plan year.

**Identifiers / Keys:**
- **Candidate Primary Key:** `PlanId` (e.g., `21989AK0030001-00`).
- **Composite Key Context:** `StandardComponentId` (e.g., `21989AK0030001`) defines the base plan. The `PlanId` appends a variant suffix (`-00`, `-01`, `-04`, etc.) representing Cost-Sharing Reduction (CSR) variations (e.g., On-Exchange, Off-Exchange, Zero Cost-Sharing).
- **Why `StandardComponentId` alone is not unique:** A base plan typically has an Off-Exchange variant (`-00`) and at least one On-Exchange variant (`-01`), resulting in multiple rows per StandardComponentId.

## 3. Healthcare.gov Service Area PUF

**What one row represents (Grain):**
One row represents the **mapping of a Service Area to a specific geographic region** (County or Zip Code).

**Identifiers / Keys:**
- **Candidate Primary Key:** Composite of `ServiceAreaId` + `County` (or `ZipCodes` if a partial county).
- **Why `ServiceAreaId` alone is not unique:** A single service area (e.g., `AKS002`) often covers multiple counties. Therefore, `ServiceAreaId` is repeated for each county it covers.

## 4. Healthcare.gov Plan ID Crosswalk PUF

**What one row represents (Grain):**
One row represents the **mapping of a discontinued or renewed plan from 2025 to its 2026 counterpart**, at the county level.

**Identifiers / Keys:**
- **Candidate Primary Key:** Composite of `PlanID_2025` + `FIPSCode` (County).
- **Why `PlanID_2025` alone is not unique:** An issuer might map a 2025 plan to different 2026 plans depending on the county (e.g., if the issuer reduces its service area).
- **Candidate Foreign Keys:** `PlanID_2026` relates back to the `StandardComponentId` in the 2026 Plan Attributes PUF.

## 5. Critical Synthesis for Architecture

1. **No Individual Claims:** There are no datasets representing an individual beneficiary-to-provider encounter at a specific timestamp.
2. **Missing Synthetics:** The CMS Synthetic Medicare Claims dataset is absent from the directory, which limits the ability to test claim-level schema/conformance natively.
3. **No Native Timestamps:** The datasets are annual snapshots/aggregates. To demonstrate anomaly detection over "time" (e.g., batches, windows), the system will need to **simulate processing windows** (e.g., by chunking the Part D dataset into simulated daily ingestions based on geography or random partitioning).
