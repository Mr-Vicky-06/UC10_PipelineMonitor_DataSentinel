# MODEL ARTIFACT AUDIT

## VOLUME (EWMA)
- **Artifact Path**: `outputs/ml/models/v2/volume_ewma_v2.joblib`
- **Python Type**: `EWMAVolumeModel`
- **Domain Name**: `VOLUME`
- **Algorithm Name**: `EWMA`
- **State Tracks**: `11` hospitals
- **Threshold**: `3.0`
- **Status**: LOADED SUCCESSFULLY

## OPERATIONAL (Isolation Forest)
- **Artifact Path**: `outputs/ml/models/v2/operational_isolationforest_v2.joblib`
- **Python Type**: `SklearnOperationalModel`
- **Domain Name**: `OPERATIONAL`
- **Algorithm Name**: `IsolationForest`
- **Features**: `['processing_duration', 'throughput', 'failure_rate']`
- **Hyperparameters**: `{'bootstrap': False, 'contamination': 0.01, 'max_features': 1.0, 'max_samples': 'auto', 'n_estimators': 100, 'n_jobs': None, 'random_state': 42, 'verbose': 0, 'warm_start': False}`
- **Threshold**: `auto`
- **Status**: LOADED SUCCESSFULLY

## DISTRIBUTION (KS)
- **Artifact Path**: `outputs/ml/models/v2/distribution_ks_v2.joblib`
- **Python Type**: `KSDistributionModel`
- **Domain Name**: `DISTRIBUTION`
- **Algorithm Name**: `KS`
- **Threshold**: `0.5`
- **Status**: LOADED SUCCESSFULLY
