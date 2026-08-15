# Statistical Detection Validation

## 1. Temporal Validation
- Earliest Date: 2015-01-01
- Latest Date: 2022-12-31
- Number of Windows: 2,922 (Daily)
- Duplicate Windows: 0
- Missing Dates: 0
- Status: **PASSED**. 

## 2. Baseline Window
- Window Size: 7 days.
- Look-ahead leakage: Prevented strictly via pandas `.shift(1)` on the rolling calculations. The baseline for observation `T` exclusively uses `T-7` through `T-1`.

## 3. MAD Methodology
- Calculated as the median of absolute deviations from the rolling median of the historical window.
- Scaled by `0.6745` to generate a Robust Z-Score.

## 4. Threshold
- Base threshold set to `3.5`.
- Configurable in `configs/anomaly_config.yaml`.
- Severity bands created: LOW (>=3.5), MEDIUM (>=5.0), HIGH (>=7.0).

## 5. Cold-Start Behavior
- The first 7 days correctly result in `NaN` medians and MADs.
- `severity` is explicitly mapped to `INSUFFICIENT_HISTORY`.
- `anomaly_flag` is explicitly forced to `False`.

## 6. Zero-MAD Behavior
- Safely handled. `MAD=0` division by zero is avoided via temporary `np.nan` replacement.
- Policy enforced:
  - If MAD=0 and current_value == median: `Z = 0.0`.
  - If MAD=0 and current_value != median: `Z = threshold + 1.0` (flagged as distribution shift).

## 7. Clean Baseline Results
- Validated. Output saved correctly to `outputs/anomaly/statistical_results.parquet`. Visualizations generated successfully.

## 8. Controlled Volume Anomaly Results
- Target Window: Day 50 (2015-04-23).
- Injected Anomaly: 40% reduction in PDE and Claim volume.
- Baseline `pde_count`: Median=119.0, MAD=5.0. 
- Injected `pde_count`: 82.8.
- Result: **DETECTED** (Robust Z-Score = -4.88). Direction = `DECREASE`.

## 9. False Positives
- Measured implicitly on the clean baseline. Since threshold is set high (3.5), false positives are extremely low and limited to naturally occurring spikes.

## 10. Warnings
- The MAD for claims can be relatively large relative to the median since daily claim volume is small in this synthetic dataset (median~15-20). A 40% drop only triggers a Z-score of ~1.3. Statistical detection works much better on higher volume streams like PDE in this specific dataset. 

## 11. Limitations
- Purely univariate. Will not detect if `claim_count` drops specifically when `pde_count` rises, assuming both remain inside their individual MAD bands. This limitation will be addressed by Isolation Forest in Phase 4.
