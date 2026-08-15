import pandas as pd
import numpy as np
import yaml
import os
import uuid
import matplotlib.pyplot as plt

class EvidenceFusionEngine:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['evidence_fusion']
        self.weights = self.config['weights']
        self.threshold = self.config['threshold']
        
    def fuse_evidence(self, dq_path, stat_path, if_path, output_path=None, rca_path=None):
        print("Running Evidence Fusion...")
        
        # Load independent detector outputs
        try:
            dq_df = pd.read_parquet(dq_path)
            # Ensure batch_id can be matched to window_date strings
            if not dq_df.empty:
                dq_df['window_date_str'] = dq_df['batch_id'].astype(str)
        except Exception:
            dq_df = pd.DataFrame()
            
        stat_df = pd.read_parquet(stat_path)
        stat_df['window_date_str'] = stat_df['window_date'].dt.strftime('%Y-%m-%d')
        
        if_df = pd.read_parquet(if_path)
        if_df['window_date_str'] = if_df['window_date'].dt.strftime('%Y-%m-%d')
        
        # We align on the temporal backbone from the statistical results (which has all windows)
        unique_dates = stat_df[['window_date', 'window_date_str']].drop_duplicates().sort_values('window_date')
        
        anomaly_events = []
        rca_evidence = []
        
        for _, row in unique_dates.iterrows():
            w_date = row['window_date']
            w_date_str = row['window_date_str']
            
            # 1. Collect DQ Evidence
            dq_violations = []
            if not dq_df.empty:
                dq_violations = dq_df[dq_df['window_date_str'] == w_date_str].to_dict('records')
            
            dq_flag = len(dq_violations) > 0
            
            # 2. Collect Statistical Evidence
            stat_metrics = stat_df[(stat_df['window_date'] == w_date) & (stat_df['anomaly_flag'] == True)]
            stat_flag = len(stat_metrics) > 0
            
            # 3. Collect Isolation Forest Evidence
            if_metrics = if_df[(if_df['window_date'] == w_date) & (if_df['anomaly_flag'] == True)]
            if_flag = len(if_metrics) > 0
            
            # 4. Calculate Evidence Score
            score = 0
            if dq_flag: score += self.weights.get('dq_violation', 3)
            if stat_flag: score += self.weights.get('statistical_anomaly', 2)
            if if_flag: score += self.weights.get('isolation_forest_anomaly', 2)
            
            # If threshold is reached, generate event
            if score >= self.threshold:
                # Determine Confidence
                # Low = 1 signal (e.g. IF only = 2)
                # Medium = Multiple weak signals or 1 strong signal (e.g. DQ only = 3, stat+IF = 4)
                # High = Multiple strong signals (e.g. DQ + stat = 5+)
                if score >= 5:
                    confidence = 'HIGH'
                elif score >= 3:
                    confidence = 'MEDIUM'
                else:
                    confidence = 'LOW'
                    
                # Determine Anomaly Type
                types = []
                if dq_flag: types.append('DATA_QUALITY')
                if stat_flag: 
                    # Heuristic check for volume vs distribution
                    types.append('VOLUME_ANOMALY' if 'count' in stat_metrics['metric'].values[0] else 'DISTRIBUTION_ANOMALY')
                if if_flag: types.append('MULTIVARIATE_ANOMALY')
                
                anomaly_type = 'COMBINED_ANOMALY' if len(types) > 1 else types[0]
                
                # Determine Primary Evidence
                primary = 'DQ' if dq_flag else ('Isolation Forest' if if_flag else 'Statistical MAD')
                
                # Generate human readable explanation
                explanation = f"{confidence}-confidence {anomaly_type.replace('_', ' ').lower()} detected on {w_date_str}. "
                if dq_flag:
                    explanation += f"Found {len(dq_violations)} explicit rule violations. "
                if if_flag:
                    explanation += "Isolation Forest identified an abnormal multivariate profile. "
                if stat_flag:
                    explanation += f"Statistical deviation found in {len(stat_metrics)} metrics. "
                explanation += "Potential contributing factors require RCA."
                
                anomaly_id = str(uuid.uuid4())
                
                # Save Event
                event = {
                    'anomaly_id': anomaly_id,
                    'window_date': w_date,
                    'dataset': 'CORE_PIPELINE',
                    'anomaly_type': anomaly_type,
                    'severity': 'PENDING_SLA', # SLA runs later
                    'confidence': confidence,
                    'evidence_score': score,
                    'dq_flag': dq_flag,
                    'statistical_flag': stat_flag,
                    'isolation_forest_flag': if_flag,
                    'cross_dataset_flag': False, # MVP placeholder
                    'operational_flag': False, # MVP placeholder
                    'affected_records': sum(d.get('affected_records', 0) for d in dq_violations) if dq_flag else None,
                    'primary_evidence': primary,
                    'supporting_evidence': 'Multiple' if len(types) > 1 else 'None',
                    'explanation': explanation,
                    'status': 'OPEN'
                }
                anomaly_events.append(event)
                
                # Save RCA structure
                rca = {
                    'anomaly_id': anomaly_id,
                    'window_date': w_date,
                    'dq_violations': str([d['rule_id'] for d in dq_violations]) if dq_flag else 'None',
                    'abnormal_metrics': str(stat_metrics['metric'].tolist()) if stat_flag else 'None',
                    'if_score': if_metrics['anomaly_score'].values[0] if if_flag else None,
                    'rca_status': 'PENDING'
                }
                rca_evidence.append(rca)
                
        # Persist
        events_df = pd.DataFrame(anomaly_events) if anomaly_events else pd.DataFrame(columns=[
            'anomaly_id', 'window_date', 'dataset', 'anomaly_type', 'severity', 'confidence', 
            'evidence_score', 'dq_flag', 'statistical_flag', 'isolation_forest_flag', 
            'cross_dataset_flag', 'operational_flag', 'affected_records', 'primary_evidence', 
            'supporting_evidence', 'explanation', 'status'
        ])
        
        rca_df = pd.DataFrame(rca_evidence) if rca_evidence else pd.DataFrame(columns=[
            'anomaly_id', 'window_date', 'dq_violations', 'abnormal_metrics', 'if_score', 'rca_status'
        ])
        
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            events_df.to_parquet(output_path)
            print(f"Saved {len(events_df)} anomaly events to {output_path}")
        
        if rca_path:
            os.makedirs(os.path.dirname(rca_path), exist_ok=True)
            rca_df.to_parquet(rca_path)
            print(f"Saved RCA evidence to {rca_path}")
            
        # Visualization
        self.generate_visualizations(events_df, stat_df, if_df)
        
        return events_df
        
    def generate_visualizations(self, events_df, stat_df, if_df):
        out_dir = 'outputs/visualizations/evidence_fusion'
        os.makedirs(out_dir, exist_ok=True)
        
        # 1. Timeline of events
        if not events_df.empty:
            plt.figure(figsize=(10, 5))
            colors = {'LOW': 'yellow', 'MEDIUM': 'orange', 'HIGH': 'red'}
            for conf in ['LOW', 'MEDIUM', 'HIGH']:
                subset = events_df[events_df['confidence'] == conf]
                if not subset.empty:
                    plt.scatter(subset['window_date'], subset['evidence_score'], c=colors[conf], label=conf, s=100)
            
            plt.title('Anomaly Events Timeline')
            plt.xlabel('Date')
            plt.ylabel('Evidence Score')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(f'{out_dir}/anomaly_timeline.png')
            plt.close()
        
        print("Evidence Fusion visualizations generated.")

if __name__ == "__main__":
    fusion = EvidenceFusionEngine('configs/anomaly_config.yaml')
    fusion.fuse_evidence(
        dq_path='outputs/anomaly/dq_results.parquet',
        stat_path='outputs/anomaly/statistical_results.parquet',
        if_path='outputs/anomaly/isolation_forest_results.parquet',
        output_path='outputs/anomaly/anomaly_events.parquet',
        rca_path='outputs/anomaly/rca_evidence.parquet'
    )
