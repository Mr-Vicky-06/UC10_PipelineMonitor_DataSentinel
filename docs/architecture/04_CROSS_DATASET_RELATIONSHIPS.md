# 04 Cross-Dataset Relationships

This document identifies which datasets can actually be connected using structured joins and normalized keys. 

## SUPPORTED Relationships

### 1. Plan ID Crosswalk → Plan Attributes
- **Relationship:** `Plan_ID_Crosswalk_PUF.PlanID_2026` → `Plan_Attributes_PUF.StandardComponentId`
- **Datatype Compatibility:** String (14 characters).
- **Semantic Compatibility:** High. Both represent the CCIIO Standard Component ID for a QHP.
- **Cardinality:** Many-to-One. (Many crosswalk records map back to a single 2026 plan).
- **False-Match Risk:** Low. These are standardized federal identifiers.
- **Documentation Support:** Yes, intended by CMS/CCIIO for linking current plans to historical plans.

### 2. Plan Attributes → Service Area
- **Relationship:** `Plan_Attributes_PUF.ServiceAreaId` → `Service_Area_PUF.ServiceAreaId`
- **Datatype Compatibility:** String (e.g., `AKS001`).
- **Semantic Compatibility:** High. Plan attributes state which service area the plan covers.
- **Cardinality:** Many-to-Many. (Many plans share a service area; service areas map to multiple counties).
- **False-Match Risk:** Low. Standardized ID.
- **Documentation Support:** Yes.

## UNSUPPORTED Relationships

### 1. Medicare Part D → Healthcare.gov PUF
- **Relationship:** None
- **Reasoning:** Medicare Part D covers Medicare beneficiaries (typically >65 or disabled). Healthcare.gov (ACA) plans cover the commercial individual market. While some providers participate in both, there are no intersecting foreign keys (e.g., NPI does not exist in the ACA PUF plan-level data). Attempting to join these datasets would be methodologically invalid and unsupported by documentation.

### 2. CMS Synthetic Claims → Medicare Part D
- **Relationship:** Unverified (Dataset Missing)
- **Reasoning:** The CMS Synthetic Claims dataset is not present in the current environment. If it were, it could theoretically link to Part D via Provider NPI, but since DE-SynPUF is heavily suppressed and synthetic, match rates would be completely unrepresentative of real-world relationships.
