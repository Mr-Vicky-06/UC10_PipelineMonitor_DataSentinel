# 03 UC10 DQ Rule Catalog

This catalog outlines the Data Quality rules that can be actively implemented using the available datasets.

## Documented Rules (Supported by source definitions)

**DQ-001**
- **Dataset:** Healthcare.gov Plan Attributes
- **Dimension:** Completeness
- **Field(s):** `PlanId`
- **Description:** Plan ID must be present.
- **Expected Condition:** NOT NULL
- **Detection Logic:** `PlanId IS NULL`
- **Severity:** High
- **Blocking/Warning:** Blocking
- **Evidence:** 22,060/22,060 expected to have PlanId.
- **Source/Documentation:** CCIIO PUF Dictionary.

**DQ-002**
- **Dataset:** CMS Part D Prescribers
- **Dimension:** Completeness
- **Field(s):** `Prscrbr_NPI`
- **Description:** Provider NPI must be populated.
- **Expected Condition:** NOT NULL
- **Detection Logic:** `Prscrbr_NPI IS NULL`
- **Severity:** High
- **Blocking/Warning:** Blocking
- **Source/Documentation:** Part D Methodology (NPI is the foundational entity).

**DQ-003**
- **Dataset:** Healthcare.gov Plan Attributes
- **Dimension:** Uniqueness
- **Field(s):** `PlanId`
- **Description:** A specific Plan variant (PlanId) should not be repeated exactly across the dataset unless partitioned by state/county (but Plan Attributes is plan-level, not county-level).
- **Expected Condition:** Unique
- **Detection Logic:** `COUNT(PlanId) > 1`
- **Severity:** High
- **Blocking/Warning:** Warning

**DQ-004**
- **Dataset:** CMS Part D Prescribers
- **Dimension:** Validity
- **Field(s):** `Tot_Clms`, `Tot_30day_Fills`, `Tot_Drug_Cst`
- **Description:** Aggregate counts and costs cannot be negative.
- **Expected Condition:** `>= 0`
- **Detection Logic:** `Tot_Clms < 0 OR Tot_Drug_Cst < 0`
- **Severity:** High
- **Blocking/Warning:** Blocking

## Project-Derived Rules (Logical assertions for testing)

**DQ-005**
- **Dataset:** CMS Part D Prescribers
- **Dimension:** Consistency
- **Field(s):** `Tot_Clms`, `Tot_30day_Fills`
- **Description:** The number of 30-day fills should generally be equal to or greater than the total number of claims.
- **Expected Condition:** `Tot_30day_Fills >= Tot_Clms`
- **Detection Logic:** `Tot_30day_Fills < Tot_Clms`
- **Severity:** Medium
- **Blocking/Warning:** Warning
- **Limitations:** There may be edge cases where reversing claims affects the ratio.

**DQ-006**
- **Dataset:** Healthcare.gov Plan ID Crosswalk
- **Dimension:** Referential Integrity
- **Field(s):** `PlanID_2026`
- **Description:** A mapped 2026 PlanID in the Crosswalk should exist in the 2026 Plan Attributes PUF.
- **Expected Condition:** Exists in Reference
- **Detection Logic:** `Crosswalk.PlanID_2026 NOT IN (Plan_Attributes.StandardComponentId)`
- **Severity:** High
- **Blocking/Warning:** Warning

## Experimental Rules (For Anomaly Injection)

**DQ-007**
- **Dataset:** Healthcare.gov Service Area
- **Dimension:** Validity
- **Field(s):** `StateCode`
- **Description:** StateCode must be a valid 2-letter US abbreviation.
- **Expected Condition:** In list of 50 states + DC
- **Detection Logic:** `LENGTH(StateCode) != 2 OR StateCode NOT IN ('AK', 'AL', ...)`
- **Severity:** High
