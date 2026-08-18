import httpx
import asyncio
import websockets
import json

API_URL = "http://localhost:8000/api/v1/alerts"
WS_URL = "ws://localhost:8000/ws/alerts"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Test GET /alerts
        print("\n--- Testing GET /api/v1/alerts/ ---")
        res = await client.get(f"{API_URL}/")
        alerts = res.json()
        print(f"Total alerts retrieved: {len(alerts)}")
        
        if not alerts:
            print("No alerts found in DB.")
            return

        alert_id = alerts[0]["alert_id"]
        print(f"First alert ID: {alert_id}")
        
        # 2. Test GET /summary
        print("\n--- Testing GET /api/v1/alerts/summary ---")
        res = await client.get(f"{API_URL}/summary")
        print(json.dumps(res.json(), indent=2))
        
        # 3. Test Acknowledge
        print(f"\n--- Testing ACKNOWLEDGE {alert_id} ---")
        res = await client.post(f"{API_URL}/{alert_id}/acknowledge")
        print(f"Status: {res.status_code}")
        print(f"New state: {res.json().get('status')}")
        
        # 4. Test Resolve
        print(f"\n--- Testing RESOLVE {alert_id} ---")
        res = await client.post(f"{API_URL}/{alert_id}/resolve")
        print(f"Status: {res.status_code}")
        print(f"New state: {res.json().get('status')}")

    # 5. Test WebSocket Connection
    print("\n--- Testing WebSocket ---")
    try:
        async with websockets.connect(WS_URL) as ws:
            print("WebSocket connected successfully!")
            # We don't need to wait for messages, just verifying connection
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
