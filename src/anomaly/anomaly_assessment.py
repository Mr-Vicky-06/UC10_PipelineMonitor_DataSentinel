import pandas as pd
import numpy as np
import yaml
import os

class AnomalyAssessmentEngine:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Default SLA config for the MVP
        self.sla_config = self.config.get('sla', {
            'deadline_seconds': 120.0,
            'at_risk_margin_seconds': 30.0
        })

    def assess_anomalies(self, events_path, rca_path, feature_path, output_path=None):
        print("Running Anomaly Assessment & SLA Preparation...")
        
        try:
            events_df = pd.read_parquet(events_path)
            rca_df = pd.read_parquet(rca_path)
            features_df = pd.read_parquet(feature_path)
        except Exception as e:
            print(f"Error loading inputs: {e}")
            return pd.DataFrame()
            
        if events_df.empty:
            print("No anomaly events to assess.")
            return pd.DataFrame()

        # We need operational features for SLA
        features_df['window_date_str'] = pd.to_datetime(features_df['feature_date']).dt.strftime('%Y-%m-%d')
        
        # Merge events with RCA and features
        # Assuming events_df has window_date as timestamp
        events_df['window_date_str'] = pd.to_datetime(events_df['window_date']).dt.strftime('%Y-%m-%d')
        
        assessed_events = []
        
        for _, event in events_df.iterrows():
            w_date_str = event['window_date_str']
            
            # Severity mapping (Independent of Confidence and SLA)
            score = event['evidence_score']
            if score >= 7:
                severity = 'CRITICAL'
            elif score >= 5:
                severity = 'HIGH'
            elif score >= 3:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'
                
            # Fetch features for this window
            feat_row = features_df[features_df['window_date_str'] == w_date_str]
            if not feat_row.empty:
                f_row = feat_row.iloc[0]
                backlog = float(f_row.get('backlog', 0))
                throughput = float(f_row.get('throughput', 0))
                proc_dur = float(f_row.get('processing_duration', 0))
                claim_vol = float(f_row.get('claim_count', 0))
                pde_vol = float(f_row.get('pde_count', 0))
            else:
                backlog, throughput, proc_dur, claim_vol, pde_vol = 0.0, 0.0, 0.0, 0.0, 0.0
                
            # Impact Analysis
            # If DQ violation, we might have affected_records from event
            affected_records = event.get('affected_records')
            if pd.isna(affected_records) or affected_records is None:
                if event['anomaly_type'] == 'VOLUME_ANOMALY':
                    # Heuristic impact: The entire volume of the day might be affected or under-reported
                    affected_records = claim_vol + pde_vol
                else:
                    affected_records = 'NOT_AVAILABLE'
                    
            affected_beneficiaries = 'NOT_AVAILABLE' # We don't track exact bene IDs in aggregated features
            
            impact_summary = f"Affected Records: {affected_records}. Beneficiaries: {affected_beneficiaries}."
            
            # RCA Preparation (Evidence-based)
            rca_row = rca_df[rca_df['anomaly_id'] == event['anomaly_id']]
            observed = f"{event['anomaly_type']} with {event['primary_evidence']} as primary evidence."
            
            potential_factors = []
            if event['dq_flag']:
                potential_factors.append("Upstream data quality corruption or missing fields")
            if event['isolation_forest_flag']:
                potential_factors.append("Multivariate operational degradation or pipeline stall")
            if event['statistical_flag'] and 'VOLUME' in event['anomaly_type']:
                potential_factors.append("Upstream ingestion failure or missing batch delivery")
                
            factors_str = "; ".join(potential_factors) if potential_factors else "Requires deeper manual investigation"
            
            # SLA Risk Preparation (SIMULATED OPERATIONAL INPUTS)
            remaining_workload = backlog
            deadline = self.sla_config['deadline_seconds']
            
            if throughput <= 0:
                eta = float('inf')
                sla_margin = -1.0 # arbitrary negative to force breach
                sla_status = 'BREACH'
            else:
                eta = remaining_workload / throughput
                sla_margin = deadline - eta
                
                if sla_margin < 0:
                    sla_status = 'BREACH'
                elif sla_margin <= self.sla_config['at_risk_margin_seconds']:
                    sla_status = 'AT_RISK'
                else:
                    sla_status = 'MET'
            
            assessed_event = {
                'anomaly_id': event['anomaly_id'],
                'window_date': event['window_date'],
                'dataset': event['dataset'],
                'anomaly_type': event['anomaly_type'],
                'evidence_score': event['evidence_score'],
                'confidence': event['confidence'],
                'severity': severity,
                'affected_records': str(affected_records),
                'affected_beneficiaries': str(affected_beneficiaries),
                'impact_summary': impact_summary,
                'observed_evidence': observed,
                'potential_contributing_factors': factors_str,
                'remaining_workload': remaining_workload,
                'throughput': throughput,
                'ETA': eta,
                'SLA_margin': sla_margin,
                'SLA_status': sla_status
            }
            assessed_events.append(assessed_event)
            
        assessed_df = pd.DataFrame(assessed_events)
        
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            assessed_df.to_parquet(output_path)
            print(f"Saved {len(assessed_df)} assessed anomalies to {output_path}")
            
            import matplotlib.pyplot as plt
            out_dir = 'outputs/visualizations/anomaly_assessment'
            os.makedirs(out_dir, exist_ok=True)
            
            # 1. Severity Distribution
            plt.figure(figsize=(8, 5))
            assessed_df['severity'].value_counts().plot(kind='bar', color=['#d9534f', '#f0ad4e', '#5bc0de', '#5cb85c'])
            plt.title('Anomaly Severity Distribution')
            plt.ylabel('Count')
            plt.tight_layout()
            plt.savefig(f'{out_dir}/severity_distribution.png')
            plt.close()
            
            # 2. SLA Status
            plt.figure(figsize=(8, 5))
            assessed_df['SLA_status'].value_counts().plot(kind='pie', autopct='%1.1f%%', colors=['#5cb85c', '#d9534f', '#f0ad4e'])
            plt.title('SLA Risk Status for Anomalies')
            plt.ylabel('')
            plt.savefig(f'{out_dir}/sla_status.png')
            plt.close()
            
        return assessed_df

if __name__ == "__main__":
    assessor = AnomalyAssessmentEngine('configs/anomaly_config.yaml')
    assessor.assess_anomalies(
        events_path='outputs/anomaly/anomaly_events.parquet',
        rca_path='outputs/anomaly/rca_evidence.parquet',
        feature_path='data/features/uc10_feature_matrix.parquet',
        output_path='outputs/anomaly/anomaly_assessment.parquet'
    )
