import httpx
import asyncio
import datetime

API_URL = "http://localhost:8000/api/v1/alerts/events"

async def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    new_event = {
        "source": "DQ",
        "pipeline": "claims",
        "hospital": "Hospital NEW", # Brand new hospital to bypass deduplication
        "event_type": "DATA_QUALITY",
        "metric": "null_percentage",
        "value": 99.0,
        "unit": "percentage",
        "summary": "Brand new alert to test Email notifications!",
        "details": {
            "rule_id": "DQ-NEW-999",
            "rule_name": "test_email_rule",
            "field": "TEST_ID"
        },
        "timestamp": now
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(API_URL, json=new_event)
        print(f"Sent NEW alert - Status {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    asyncio.run(main())
