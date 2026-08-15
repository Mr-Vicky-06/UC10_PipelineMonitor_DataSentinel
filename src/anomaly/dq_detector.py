import duckdb
import yaml
import pandas as pd
from datetime import datetime

class DQDetector:
    def __init__(self, config_path, datasets):
        self.config_path = config_path
        self.datasets = datasets
        self.con = duckdb.connect(':memory:')
        self.load_data()
        self.load_rules()

    def load_data(self):
        print("Loading datasets into DuckDB for DQ Engine...")
        for name, path in self.datasets.items():
            self.con.execute(f"CREATE TABLE {name} AS SELECT * FROM read_csv_auto('{path}', sample_size=-1)")

    def load_rules(self):
        with open(self.config_path, 'r') as f:
            self.rules = yaml.safe_load(f)['rules']

    def run_rules(self):
        results = []
        print(f"Running {len(self.rules)} DQ rules...")
        
        for rule in self.rules:
            rule_id = rule['rule_id']
            dataset = rule['dataset']
            field = rule['field']
            condition = rule['condition']
            
            # Base query structure for finding violations
            query = ""
            if rule['dimension'] == 'completeness':
                query = f"SELECT * FROM {dataset} WHERE {field} {condition}"
                
            elif rule['dimension'] == 'uniqueness':
                query = f"""
                    SELECT * FROM {dataset} 
                    WHERE {field} IN (
                        SELECT {field} FROM {dataset} GROUP BY {field} HAVING COUNT(*) > 1
                    )
                """
                
            elif rule['dimension'] == 'validity':
                # Parse date format like '25-Mar-2015'
                if condition == "> CURRENT_DATE":
                    query = f"SELECT * FROM {dataset} WHERE strptime({field}, '%d-%b-%Y') > CURRENT_DATE"
                else:
                    query = f"SELECT * FROM {dataset} WHERE {field} {condition}"
                    
            elif rule['dimension'] == 'referential_integrity':
                ref_dataset = rule['reference_dataset']
                ref_field = rule['reference_field']
                query = f"""
                    SELECT t1.* FROM {dataset} t1
                    LEFT JOIN {ref_dataset} t2 ON t1.{field} = t2.{ref_field}
                    WHERE t2.{ref_field} IS NULL
                """
            
            # Execute rule
            try:
                violation_df = self.con.execute(query).df()
                total_records = self.con.execute(f"SELECT COUNT(*) FROM {dataset}").fetchone()[0]
                violation_count = len(violation_df)
                
                if violation_count > 0:
                    # In a real system, we'd save the affected_records (IDs). 
                    # For MVP, we save the count and a sample of IDs.
                    id_col = 'PDE_ID' if dataset == 'pde' else ('CLM_ID' if dataset == 'claims' else 'BENE_ID')
                    affected_sample = violation_df[id_col].head(50).tolist() if id_col in violation_df.columns else []
                    
                    results.append({
                        'event_id': f"EVT-{rule_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        'batch_id': 'BATCH_CURRENT',
                        'dataset': dataset,
                        'rule_id': rule_id,
                        'dimension': rule['dimension'],
                        'severity': rule['severity'],
                        'violation_count': violation_count,
                        'violation_rate': violation_count / total_records,
                        'affected_records': str(affected_sample),
                        'evidence': f"Rule {rule['name']} failed {violation_count} times.",
                        'timestamp': datetime.now().isoformat()
                    })
                print(f"Rule {rule_id} ({rule['name']}) -> {violation_count} violations")
            except Exception as e:
                print(f"Error running rule {rule_id}: {e}")

        # If no anomalies in clean baseline, create an empty DataFrame with the schema
        if not results:
            results_df = pd.DataFrame(columns=[
                'event_id', 'batch_id', 'dataset', 'rule_id', 'dimension', 'severity', 
                'violation_count', 'violation_rate', 'affected_records', 'evidence', 'timestamp'
            ])
        else:
            results_df = pd.DataFrame(results)
            
        return results_df

if __name__ == "__main__":
    datasets = {
        'pde': 'data/raw/pde/pde.csv',
        'claims': 'data/raw/claims/inpatient.csv',
        'beneficiary': 'data/raw/beneficiary/beneficiary_2024.csv'
    }
    detector = DQDetector('configs/dq_rules.yaml', datasets)
    results_df = detector.run_rules()
    
    out_path = 'outputs/anomaly/dq_results.parquet'
    results_df.to_parquet(out_path)
    print(f"DQ Engine completed. Found {len(results_df)} violation types on clean baseline.")
    print(f"Results saved to {out_path}")
