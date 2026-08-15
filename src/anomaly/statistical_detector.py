import pandas as pd
import numpy as np
import yaml
import os
import matplotlib.pyplot as plt

class StatisticalDetector:
    def __init__(self, config_path, feature_matrix_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['statistical']
        self.window = self.config['window']
        self.threshold = self.config['threshold']
        self.metrics = self.config['metrics']
        self.feature_matrix_path = feature_matrix_path
        
    def _rolling_mad(self, series):
        # Function to apply over the rolling window
        return np.median(np.abs(series - np.median(series)))

    def detect(self, output_path=None, test_df=None):
        print(f"Running Statistical MAD Detector (window={self.window}, threshold={self.threshold})")
        if test_df is not None:
            df = test_df.copy()
        else:
            df = pd.read_parquet(self.feature_matrix_path)
            
        # Ensure temporal ordering
        df['feature_date'] = pd.to_datetime(df['feature_date'])
        df = df.sort_values('feature_date').reset_index(drop=True)
        
        results = []
        
        for metric in self.metrics:
            if metric not in df.columns:
                continue
                
            series = df[metric]
            
            # Use shift(1) to prevent look-ahead leakage. The baseline for T uses [T-window : T-1]
            rolling_window = series.rolling(window=self.window, min_periods=self.window)
            
            # Baseline median (shifted)
            baseline_median = rolling_window.median().shift(1)
            
            # Baseline MAD (shifted)
            # pandas rolling doesn't have a direct mad(), so we apply a custom function
            # Since rolling apply is slow, we can compute it if needed or use an approximation.
            # A direct rolling apply:
            mad = rolling_window.apply(self._rolling_mad, raw=True).shift(1)
            
            # For cold starts (the first self.window days)
            cold_start_mask = baseline_median.isna()
            
            # Compute Robust Z-Score
            # 0.6745 is the constant to make MAD comparable to standard deviation for normal dist
            mad_adjusted = mad.replace(0, np.nan) # Temporarily replace 0 to avoid division by zero
            robust_z = 0.6745 * (series - baseline_median) / mad_adjusted
            
            # Handle MAD = 0 cases
            # If MAD=0 and current == median -> robust_z = 0
            # If MAD=0 and current != median -> robust_z = large number (e.g., threshold + 1 to force flag)
            is_zero_mad = (mad == 0)
            is_same_as_median = (series == baseline_median)
            
            robust_z.loc[is_zero_mad & is_same_as_median] = 0.0
            robust_z.loc[is_zero_mad & ~is_same_as_median] = self.threshold + 1.0 # Flag as distribution shift
            
            # Anomaly flag
            anomaly_flag = np.abs(robust_z) >= self.threshold
            anomaly_flag.loc[cold_start_mask] = False # Don't flag cold starts
            
            # Direction
            direction = np.where(series > baseline_median, 'INCREASE', np.where(series < baseline_median, 'DECREASE', 'NONE'))
            
            # Severity (Simple heuristic: Z >= 3.5 is LOW, Z >= 5 is MEDIUM, Z >= 7 is HIGH)
            severity = pd.Series('NORMAL', index=df.index)
            severity.loc[np.abs(robust_z) >= self.threshold] = 'LOW'
            severity.loc[np.abs(robust_z) >= self.threshold + 1.5] = 'MEDIUM'
            severity.loc[np.abs(robust_z) >= self.threshold + 3.5] = 'HIGH'
            severity.loc[cold_start_mask] = 'INSUFFICIENT_HISTORY'
            
            # Assemble results for this metric
            metric_df = pd.DataFrame({
                'window_date': df['feature_date'],
                'metric': metric,
                'observed_value': series,
                'baseline_median': baseline_median,
                'MAD': mad,
                'robust_z_score': robust_z,
                'threshold': self.threshold,
                'direction': direction,
                'anomaly_flag': anomaly_flag,
                'severity': severity
            })
            
            results.append(metric_df)
            
        final_results = pd.concat(results, ignore_index=True)
        
        if output_path:
            final_results.to_parquet(output_path)
            print(f"Saved {len(final_results)} statistical evaluations to {output_path}")
            
            # Generate visualizations
            self.generate_visualizations(df, final_results)
            
        return final_results
        
    def generate_visualizations(self, raw_df, results_df):
        out_dir = 'outputs/visualizations/statistical'
        os.makedirs(out_dir, exist_ok=True)
        
        # 1. Claim Volume + PDE Volume
        plt.figure(figsize=(12, 6))
        plt.plot(raw_df['feature_date'], raw_df['claim_count'], label='Claim Volume', alpha=0.7)
        plt.plot(raw_df['feature_date'], raw_df['pde_count'], label='PDE Volume', alpha=0.7)
        plt.title('Daily Event Volumes')
        plt.xlabel('Date')
        plt.ylabel('Count')
        plt.legend()
        plt.savefig(f'{out_dir}/volume_trends.png')
        plt.close()
        
        # 2. Selected metric with MAD
        pde_res = results_df[results_df['metric'] == 'pde_count']
        plt.figure(figsize=(12, 6))
        plt.plot(pde_res['window_date'], pde_res['observed_value'], label='Observed PDE Volume')
        plt.plot(pde_res['window_date'], pde_res['baseline_median'], label='Rolling Median (7-day)', linestyle='--')
        
        anomalies = pde_res[pde_res['anomaly_flag'] == True]
        plt.scatter(anomalies['window_date'], anomalies['observed_value'], color='red', label='Anomalies', zorder=5)
        
        plt.title('PDE Volume with Rolling Median & Anomalies')
        plt.legend()
        plt.savefig(f'{out_dir}/pde_mad_anomalies.png')
        plt.close()
        print("Visualizations generated.")

if __name__ == "__main__":
    detector = StatisticalDetector('configs/anomaly_config.yaml', 'data/features/uc10_feature_matrix.parquet')
    detector.detect('outputs/anomaly/statistical_results.parquet')
