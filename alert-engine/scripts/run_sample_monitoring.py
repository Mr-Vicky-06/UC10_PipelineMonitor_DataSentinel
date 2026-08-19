import pandas as pd
import httpx
import json
import datetime
from pathlib import Path

def run_monitoring():
    # 1. Load data
    csv_path = Path(__file__).parent / "sample_claims.csv"
    print(f"Loading sample data from {csv_path}...")
    df = pd.read_csv(csv_path)
    total_rows = len(df)
    
    alerts = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    print("\n--- Running Data Quality Validation ---")
    
    # 3. Calculate DQ Metrics
    
    # Completeness: BENE_ID NULL
    null_bene_count = df['BENE_ID'].isna().sum()
    if null_bene_count > 0:
        pct = (null_bene_count / total_rows) * 100
        alerts.append({
            "source": "DQ",
            "pipeline": "claims",
            "hospital": "Hospital Sample",
            "event_type": "DATA_QUALITY",
            "metric": "null_percentage",
            "value": float(pct),
            "unit": "percentage",
            "summary": f"{pct:.1f}% of BENE_ID values are NULL",
            "details": {
                "rule_id": "DQ-COMP-001",
                "rule_name": "mandatory_beneficiary_id",
                "field": "BENE_ID",
                "affected_rows": int(null_bene_count),
                "total_rows": total_rows,
                "affected_percentage": float(pct)
            },
            "timestamp": now
        })
        
    # Financial validation: Negative payments
    neg_pmt_count = (df['CLM_PMT_AMT'] < 0).sum()
    if neg_pmt_count > 0:
        pct = (neg_pmt_count / total_rows) * 100
        alerts.append({
            "source": "DQ",
            "pipeline": "claims",
            "hospital": "Hospital Sample",
            "event_type": "DATA_QUALITY",
            "metric": "negative_payment",
            "value": float(neg_pmt_count),
            "unit": "count",
            "summary": f"Found {neg_pmt_count} claims with negative payment amounts",
            "details": {
                "rule_id": "DQ-FIN-001",
                "rule_name": "no_negative_payments",
                "field": "CLM_PMT_AMT",
                "affected_rows": int(neg_pmt_count),
                "total_rows": total_rows,
                "affected_percentage": float(pct)
            },
            "timestamp": now
        })
        
    # Duplicate validation
    dup_count = df.duplicated(subset=['CLM_ID', 'CLM_LINE_NUM']).sum()
    if dup_count > 0:
        pct = (dup_count / total_rows) * 100
        alerts.append({
            "source": "DQ",
            "pipeline": "claims",
            "hospital": "Hospital Sample",
            "event_type": "DATA_QUALITY",
            "metric": "duplicate_claim_lines",
            "value": float(dup_count),
            "unit": "count",
            "summary": f"Found {dup_count} duplicate claim lines (CLM_ID + CLM_LINE_NUM)",
            "details": {
                "rule_id": "DQ-UNIQ-001",
                "rule_name": "unique_claim_line",
                "fields": ["CLM_ID", "CLM_LINE_NUM"],
                "affected_rows": int(dup_count),
                "total_rows": total_rows,
                "affected_percentage": float(pct)
            },
            "timestamp": now
        })
        
    # Date validation: THRU < FROM
    df['CLM_FROM_DT'] = pd.to_datetime(df['CLM_FROM_DT'])
    df['CLM_THRU_DT'] = pd.to_datetime(df['CLM_THRU_DT'])
    invalid_date_count = (df['CLM_THRU_DT'] < df['CLM_FROM_DT']).sum()
    if invalid_date_count > 0:
        pct = (invalid_date_count / total_rows) * 100
        alerts.append({
            "source": "DQ",
            "pipeline": "claims",
            "hospital": "Hospital Sample",
            "event_type": "DATA_QUALITY",
            "metric": "invalid_date_range",
            "value": float(invalid_date_count),
            "unit": "count",
            "summary": f"Found {invalid_date_count} claims where THRU_DT is before FROM_DT",
            "details": {
                "rule_id": "DQ-DATE-001",
                "rule_name": "valid_date_range",
                "fields": ["CLM_FROM_DT", "CLM_THRU_DT"],
                "affected_rows": int(invalid_date_count),
                "total_rows": total_rows,
                "affected_percentage": float(pct)
            },
            "timestamp": now
        })
        
    # Provider completeness
    null_prov_count = df['PROVIDER_ID'].isna().sum()
    if null_prov_count > 0:
        pct = (null_prov_count / total_rows) * 100
        alerts.append({
            "source": "DQ",
            "pipeline": "claims",
            "hospital": "Hospital Sample",
            "event_type": "DATA_QUALITY",
            "metric": "null_provider",
            "value": float(null_prov_count),
            "unit": "count",
            "summary": f"{null_prov_count} claims are missing PROVIDER_ID",
            "details": {
                "rule_id": "DQ-COMP-002",
                "rule_name": "mandatory_provider_id",
                "field": "PROVIDER_ID",
                "affected_rows": int(null_prov_count),
                "total_rows": total_rows,
                "affected_percentage": float(pct)
            },
            "timestamp": now
        })
        
    # 4. Send One Alert Event Per Important DQ Problem
    print(f"Generated {len(alerts)} DQ alerts based on sample data.\n")
    print("--- Sending Alerts to the Alert Engine ---")
    
    api_url = "http://localhost:8000/api/v1/alerts/events"
    
    with httpx.Client() as client:
        for alert in alerts:
            print(f"Sending: {alert['summary']}")
            try:
                resp = client.post(api_url, json=alert)
                resp.raise_for_status()
                print(f"  -> Success! Alert ID: {resp.json().get('alert_id')}")
            except Exception as e:
                print(f"  -> Failed: {e}")

if __name__ == "__main__":
    run_monitoring()
