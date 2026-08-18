# BASELINE V2 SNAPSHOT
*Created at Phase 4.3 Initiation*

## 1. Current Model Registry
**Registry File**: `outputs/ml/registry/model_registry.json`

| Domain | Model Name | Version | Path | Status |
| :--- | :--- | :--- | :--- | :--- |
| **VOLUME** | CUSUM | 20260817135502 | `outputs\ml\models\volume_cusum_v20260817135502.joblib` | PROMOTED_FOR_INFERENCE |
| **DISTRIBUTION** | KS_Proxy | 20260817135502 | `outputs\ml\models\distribution_ks_proxy_v20260817135502.joblib` | PROMOTED_FOR_INFERENCE |
| **OPERATIONAL** | LOF | 20260817135502 | `outputs\ml\models\operational_lof_v20260817135502.joblib` | PROMOTED_FOR_INFERENCE |

## 2. V2 Features
- **VOLUME**: `claim_volume`, `beneficiary_volume`, `provider_volume`
- **DISTRIBUTION**: `claim_amount_mean`, `claim_amount_median`, `claim_amount_total`
- **OPERATIONAL**: `processing_duration`, `throughput`, `failure_rate`

## 3. Contracts & Integrations
- **MLDetectionEngine (`src/ml/inference/engine.py`)**: Responsible for predicting anomalies based on the promoted models and outputting `AnomalyEvent` instances.
- **AnomalyEvent**: Canonical contract emitted by `MLDetectionEngine`.
- **EvidencePack & RCA Integration**: `AnomalyEvent` feeds into `metrics_repository.duckdb`, which is queried via RAG to synthesize `RCAResponse`.
- **Status**: Completely frozen and untouched for Phase 4.3.

## 4. Current Test Suite
- Test suite located in `tests/ml/test_ml_layer.py`, `tests/monitoring/test_metrics_integration.py`, and integration tests. All 236 global tests are passing as of the start of Phase 4.3.
