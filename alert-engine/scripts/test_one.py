import httpx
import asyncio
import datetime
import json

API_URL = "http://localhost:8000/api/v1/alerts/events"

async def main():
    now = datetime.datetime.utcnow().isoformat()
    
    event = {
        "source": "DQ",
        "pipeline": "claims",
        "hospital": "Hospital C",
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
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=event)
            response.raise_for_status()
            print(f"Sent {event['event_type']} - Status {response.status_code}")
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Failed to send: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
