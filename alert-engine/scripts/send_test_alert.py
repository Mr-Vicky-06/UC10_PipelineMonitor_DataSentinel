import httpx
import asyncio
import datetime
import json

API_URL = "http://localhost:8000/api/v1/alerts/events"

async def send_event(client, event_data):
    try:
        response = await client.post(API_URL, json=event_data)
        response.raise_for_status()
        print(f"Sent {event_data['event_type']} - Status {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Failed to send {event_data['event_type']}: {str(e)}")

async def main():
    now = datetime.datetime.utcnow().isoformat()
    
    events = [
        # 1. Critical DQ Alert
        {
            "source": "DQ",
            "pipeline": "claims",
            "hospital": "Hospital A",
            "event_type": "DATA_QUALITY",
            "metric": "null_percentage",
            "value": 45.0,
            "unit": "percentage",
            "summary": "45% of BENE_ID values are NULL",
            "details": {
                "rule_id": "DQ-COMP-001",
                "rule_name": "mandatory_beneficiary_id",
                "field": "BENE_ID",
                "affected_rows": 1,
                "total_rows": 3,
                "affected_percentage": 33.33
            },
            "timestamp": now
        },
        # 2. High DQ Alert
        {
            "source": "DQ",
            "pipeline": "claims",
            "hospital": "Hospital A",
            "event_type": "DATA_QUALITY",
            "metric": "null_percentage",
            "value": 20.0,
            "unit": "percentage",
            "summary": "20% of CLM_ID values are NULL",
            "details": {
                "rule_id": "DQ-COMP-002",
                "rule_name": "mandatory_claim_id",
                "field": "CLM_ID",
                "affected_rows": 20,
                "total_rows": 100,
                "affected_percentage": 20.0
            },
            "timestamp": now
        },
        # 3. Critical Anomaly
        {
            "source": "ANOMALY",
            "pipeline": "claims",
            "hospital": "Hospital A",
            "event_type": "ANOMALY",
            "metric": "volume_deviation",
            "value": 60.0,
            "unit": "percentage",
            "summary": "Claims volume is 60% below normal",
            "details": {
                "expected": 1000000,
                "actual": 400000,
                "deviation": 60.0
            },
            "timestamp": now
        },
        # 4. High SLA Risk
        {
            "source": "SLA",
            "pipeline": "claims",
            "hospital": "Hospital A",
            "event_type": "SLA",
            "metric": "minutes_remaining",
            "value": 20.0,
            "unit": "minutes",
            "summary": "Claims pipeline may miss SLA",
            "details": {
                "deadline": "07:00",
                "estimated_completion": "07:15",
                "pipeline_status": "RUNNING"
            },
            "timestamp": now
        },
        # 5. Critical Processing Failure
        {
            "source": "PROCESSING",
            "pipeline": "claims",
            "hospital": "Hospital A",
            "event_type": "PROCESSING",
            "metric": "job_status",
            "value": "FAILED",
            "summary": "Claims transformation job failed",
            "details": {
                "job_name": "claims_transformation",
                "stage": "transformation"
            },
            "timestamp": now
        }
    ]
    
    async with httpx.AsyncClient() as client:
        # Send initial events
        for event in events:
            await send_event(client, event)
            await asyncio.sleep(1)
            
        print("\n--- Sending Duplicate DQ Event to test Deduplication ---")
        # Duplicate of #1
        await send_event(client, events[0])

if __name__ == "__main__":
    asyncio.run(main())
