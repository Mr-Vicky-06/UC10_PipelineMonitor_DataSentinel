import pandas as pd
import numpy as np
import yaml
import os
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt

class IsolationForestDetector:
    def __init__(self, config_path, feature_matrix_path):
        # We assume the config path now includes Isolation Forest settings
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)
            # Use defaults if not in config yet
            self.config = full_config.get('isolation_forest', {
                'contamination': 0.02,
                'train_split': 0.70,
                'random_state': 42
            })
            self.metrics = full_config['statistical']['metrics'] # The 18 numerical features
            
        self.contamination = self.config['contamination']
        self.train_split = self.config['train_split']
        self.random_state = self.config['random_state']
        self.feature_matrix_path = feature_matrix_path
        
    def detect(self, output_path=None, test_df=None):
        print(f"Running Isolation Forest (contamination={self.contamination}, train_split={self.train_split})")
        if test_df is not None:
            df = test_df.copy()
        else:
            df = pd.read_parquet(self.feature_matrix_path)
            
        df['feature_date'] = pd.to_datetime(df['feature_date'])
        df = df.sort_values('feature_date').reset_index(drop=True)
        
        # Select only the approved numerical behavioral features
        X = df[self.metrics].copy()
        
        # Temporal Split (70/30 rule as requested)
        train_size = int(len(X) * self.train_split)
        X_train = X.iloc[:train_size]
        
        print(f"Total Windows: {len(X)}")
        print(f"Training Period: {df['feature_date'].iloc[0].date()} to {df['feature_date'].iloc[train_size-1].date()} ({len(X_train)} windows)")
        print(f"Testing Period: {df['feature_date'].iloc[train_size].date()} to {df['feature_date'].iloc[-1].date()} ({len(X) - train_size} windows)")
        
        # Initialize and Train Isolation Forest
        model = IsolationForest(
            contamination=self.contamination, 
            random_state=self.random_state,
            n_jobs=-1
        )
        
        print("Training Isolation Forest on clean baseline...")
        model.fit(X_train)
        
        # Predict on entire dataset (Scores: negative = anomaly, positive = normal)
        print("Predicting anomalies...")
        anomaly_scores = model.decision_function(X)
        predictions = model.predict(X) # -1 for anomaly, 1 for normal
        
        # Determine Severity based on the score distribution
        # Lower score = more anomalous
        score_threshold = np.percentile(anomaly_scores, self.contamination * 100)
        deep_anomaly_threshold = np.percentile(anomaly_scores, (self.contamination / 2) * 100)
        
        severity = pd.Series('NORMAL', index=df.index)
        anomaly_flag = predictions == -1
        
        severity.loc[anomaly_scores < score_threshold] = 'MEDIUM'
        severity.loc[anomaly_scores < deep_anomaly_threshold] = 'HIGH'
        
        results_df = pd.DataFrame({
            'window_date': df['feature_date'],
            'anomaly_score': anomaly_scores,
            'prediction': predictions,
            'anomaly_flag': anomaly_flag,
            'severity': severity
        })
        
        if output_path:
            results_df.to_parquet(output_path)
            print(f"Saved IF results to {output_path}")
            self.generate_visualizations(results_df)
            
        return results_df
        
    def generate_visualizations(self, results_df):
        out_dir = 'outputs/visualizations/isolation_forest'
        os.makedirs(out_dir, exist_ok=True)
        
        plt.figure(figsize=(12, 6))
        plt.plot(results_df['window_date'], results_df['anomaly_score'], label='IF Anomaly Score', color='blue', alpha=0.6)
        
        anomalies = results_df[results_df['anomaly_flag'] == True]
        plt.scatter(anomalies['window_date'], anomalies['anomaly_score'], color='red', label='Detected Anomalies', zorder=5)
        
        plt.axhline(y=0, color='black', linestyle='--', alpha=0.5, label='Decision Boundary')
        plt.title('Isolation Forest Multivariate Anomaly Scores over Time')
        plt.xlabel('Date')
        plt.ylabel('Anomaly Score (Lower = More Anomalous)')
        plt.legend()
        plt.savefig(f'{out_dir}/if_anomaly_scores.png')
        plt.close()
        print("Visualizations generated.")

if __name__ == "__main__":
    detector = IsolationForestDetector('configs/anomaly_config.yaml', 'data/features/uc10_feature_matrix.parquet')
    detector.detect('outputs/anomaly/isolation_forest_results.parquet')
