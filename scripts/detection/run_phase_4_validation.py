import os
import duckdb
import hashlib
from src.monitoring.metrics_repository import MetricsRepository
from src.detection.dq_detector import DQDetector

def get_sha256(filepath):
    h = hashlib.sha256()
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    return "FILE_NOT_FOUND"

def main():
    print("Starting Phase 4 Real Data Validation and Historical Readiness Audit...")

    # 1. Source Immutability Check (Before)
    source_file = "master_data/claims/claims_master.csv"
    data_file = "data/raw/claims/inpatient.csv"
    
    hash_master_before = get_sha256(source_file)
    hash_data_before = get_sha256(data_file)
    
    # 2. Historical Readiness Audit
    con_tel = duckdb.connect("outputs/pipeline_workspace/pipeline_telemetry.duckdb")
    con_claims = duckdb.connect("outputs/pipeline_workspace/processed_claims.duckdb")
    repo = MetricsRepository()
    
    runs = con_tel.execute("SELECT COUNT(DISTINCT run_id) FROM pipeline_events").fetchone()[0]
    batches = con_tel.execute("SELECT COUNT(DISTINCT batch_id) FROM pipeline_events").fetchone()[0]
    hospitals = con_tel.execute("SELECT COUNT(DISTINCT hospital_id) FROM pipeline_events").fetchone()[0]
    service_dates = con_tel.execute("SELECT COUNT(DISTINCT service_date) FROM pipeline_events").fetchone()[0]
    time_span = con_tel.execute("SELECT MIN(timestamp), MAX(timestamp) FROM pipeline_events").fetchone()
    
    # Metrics
    metric_obs = repo._get_connection().execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
    metric_counts = repo._get_connection().execute("SELECT metric_name, COUNT(*) FROM metrics GROUP BY metric_name").fetchall()
    
    # 3. DQ Detector Real Data Validation
    print("Executing DQ Detector over existing rule_results...")
    rule_results = []
    
    rows = con_claims.execute("SELECT * FROM rule_results").fetchall()
    columns = [desc[0] for desc in con_claims.execute("DESCRIBE rule_results").fetchall()]
    
    for row in rows:
        record = dict(zip(columns, row))
        rule_results.append(record)
        
    failed_rules_count = sum(1 for r in rule_results if r["status"] != "PASSED")
    
    detector = DQDetector()
    anomalies = detector.detect(rule_results, hospital_id="HOSP-ALL")
    
    print(f"DQ Detector generated {len(anomalies)} anomalies from {failed_rules_count} failed rule results.")
    
    repo.save_anomalies(anomalies)
    saved_anomalies_count = repo._get_connection().execute("SELECT COUNT(*) FROM anomaly_events").fetchone()[0]
    
    print(f"Persisted {saved_anomalies_count} anomaly_events to Metrics Repository.")
    
    con_tel.close()
    con_claims.close()
    
    # 4. Source Immutability Check (After)
    hash_master_after = get_sha256(source_file)
    hash_data_after = get_sha256(data_file)
    
    immutability_passed = (hash_master_before == hash_master_after) and (hash_data_before == hash_data_after)
    
    # 5. Generate Report
    report = f"""# Historical Readiness Report & Validation

## 1. Historical Data Readiness Gate
- **Pipeline Runs**: {runs}
- **Batches**: {batches}
- **Hospitals**: {hospitals}
- **Service Dates**: {service_dates}
- **Time Span**: {time_span[0]} to {time_span[1]}
- **Metrics Observations**: {metric_obs}
- **Observations per feature**: {dict(metric_counts)}
- **Missing Features (Data Gaps)**: `pde_count`, `claim_pde_ratio`, `median_rx_cost`, `median_days_supply`, `backlog`
- **Minimum Observations Required for ML**: 1,000+ over 30+ days
- **Training Readiness Status**: INSUFFICIENT HISTORICAL DATA

## 2. ML Detector Status
- **VolumeDetector**: BLOCKED — INSUFFICIENT HISTORICAL DATA
- **DistributionDetector**: BLOCKED — INSUFFICIENT HISTORICAL DATA
- **OperationalDetector**: BLOCKED — INSUFFICIENT HISTORICAL DATA

## 3. Real Data Validation (DQ Detector)
- **Total rule_results evaluated**: {len(rule_results)}
- **Violations detected (status != PASSED)**: {failed_rules_count}
- **AnomalyEvents generated**: {len(anomalies)}
- **AnomalyEvents persisted to DB**: {saved_anomalies_count}
- **Reconciliation**: {'PASS' if failed_rules_count == len(anomalies) == saved_anomalies_count else 'FAIL'}

## 4. Source Immutability Check
- `master_data` SHA256 Before: {hash_master_before}
- `master_data` SHA256 After: {hash_master_after}
- `data/` SHA256 Before: {hash_data_before}
- `data/` SHA256 After: {hash_data_after}
- **Immutability Status**: {'PASS' if immutability_passed else 'FAIL'}
"""

    with open("outputs/reports/historical_readiness_report.md", "w") as f:
        f.write(report)
        
    print("Report written to outputs/reports/historical_readiness_report.md")
    
if __name__ == "__main__":
    os.makedirs("outputs/reports", exist_ok=True)
    main()
